from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from scanlog.collector import collect as do_collect
from scanlog.models import PlanItem, ScanBatch, ScanPlan, ScanResult, ScanResultEntry, ScanRun
from scanlog.parser import parse_output
from scanlog.repository import (
    add_watch_path,
    get_latest_plan,
    get_pending_plan_items,
    get_plan_by_id,
    get_plan_items,
    get_session,
    init_db,
    list_watch_paths,
    remove_watch_path,
)
from scanlog.scanner import run_batch_scan, run_scan

app = typer.Typer(invoke_without_command=True)
watch_app = typer.Typer(help="監視対象 path の管理コマンド")
app.add_typer(watch_app, name="watch")


def _calc_result_status(entries: list[dict]) -> str:
    """clamav_error はスキャン結果に影響させない。infected > error > clean の優先順位。"""
    if any(e["entry_status"] == "infected" for e in entries):
        return "infected"
    if any(e["entry_status"] == "error" for e in entries):
        return "error"
    return "clean"


def _print_scan_result(entries: list[dict], result_status: str) -> None:
    typer.echo(f"\nResult: {result_status.upper()}")
    for e in entries:
        if e["entry_status"] == "infected":
            typer.echo(f"  [INFECTED] {e['scanned_path']} ({e['virus_name']})")
        elif e["entry_status"] == "error":
            typer.echo(f"  [ERROR]    {e['scanned_path']}")
    clamav_errors = [e for e in entries if e["entry_status"] == "clamav_error"]
    if clamav_errors:
        typer.echo(f"  {len(clamav_errors)} file(s) skipped (could not be accessed by ClamAV).")
    clean_count = sum(1 for e in entries if e["entry_status"] == "clean")
    if result_status == "clean":
        typer.echo(f"  All {clean_count} file(s) are clean.")


@app.callback()
def main(ctx: typer.Context) -> None:
    init_db()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def scan(path: str = typer.Argument(..., help="スキャン対象のファイルまたはディレクトリ")) -> None:
    target = Path(path).resolve()
    if not target.exists():
        typer.echo(f"Error: {path} が存在しません", err=True)
        raise typer.Exit(1)

    if target.is_dir():
        target_type = "directory"
        scan_mode = "recursive"
    else:
        target_type = "file"
        scan_mode = "single"

    with get_session() as session:
        plan = ScanPlan(
            mode="manual_scan",
            status="approved",
            base_path=str(target),
            created_at=datetime.now(),
        )
        session.add(plan)
        session.flush()

        item = PlanItem(
            plan_id=plan.id,
            target_path=str(target),
            target_type=target_type,
            scan_mode=scan_mode,
            target_reason="manual",
            selected=True,
            excluded_by_user=False,
        )
        session.add(item)
        session.flush()

        run = ScanRun(
            plan_id=plan.id,
            started_at=datetime.now(),
            status="running",
        )
        session.add(run)
        session.flush()

        batch = ScanBatch(
            run_id=run.id,
            batch_type=target_type,
            status="running",
            started_at=datetime.now(),
        )
        session.add(batch)
        session.flush()

        typer.echo(f"Scanning {target} ...")
        try:
            if target_type == "file":
                raw_output, exit_code, command_line = run_batch_scan([str(target)])
            else:
                raw_output, exit_code = run_scan(str(target), scan_mode)
                command_line = f"clamscan -r --no-summary {target}"
            run_status = "completed"
            batch_status = "completed"
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            run.status = "failed"
            run.finished_at = datetime.now()
            batch.status = "failed"
            batch.finished_at = datetime.now()
            raise typer.Exit(1)

        batch.command_line = command_line
        batch.status = batch_status
        batch.finished_at = datetime.now()

        entries = parse_output(raw_output)
        result_status = _calc_result_status(entries)

        result = ScanResult(
            run_id=run.id,
            batch_id=batch.id,
            plan_item_id=item.id,
            target_path=str(target),
            target_type=target_type,
            result_status=result_status,
            raw_output=raw_output,
            exit_code=exit_code,
        )
        session.add(result)
        session.flush()

        for e in entries:
            session.add(ScanResultEntry(
                scan_result_id=result.id,
                scanned_path=e["scanned_path"],
                entry_status=e["entry_status"],
                virus_name=e["virus_name"],
                raw_line=e["raw_line"],
            ))

        item.execution_status = "completed"
        item.batch_id = batch.id
        item.last_run_id = run.id
        run.status = run_status
        run.finished_at = datetime.now()

    _print_scan_result(entries, result_status)


@app.command()
def collect(base: str = typer.Argument(".", help="収集対象ディレクトリ（デフォルト: カレント）")) -> None:
    """当日更新ファイルを収集してスキャンプランを作成する"""
    base_path = str(Path(base).resolve())
    targets = do_collect(base_path)

    if not targets:
        typer.echo("収集対象が見つかりませんでした。")
        return

    with get_session() as session:
        plan = ScanPlan(
            mode="scheduled_scan",
            status="draft",
            base_path=base_path,
            created_at=datetime.now(),
        )
        session.add(plan)
        session.flush()

        for t in targets:
            session.add(PlanItem(
                plan_id=plan.id,
                target_path=t["target_path"],
                target_type=t["target_type"],
                scan_mode=t["scan_mode"],
                target_reason=t["target_reason"],
                selected=True,
                excluded_by_user=False,
                execution_status="pending",
            ))

        plan_id = plan.id

    typer.echo(f"Plan created: plan_id={plan_id}, {len(targets)} target(s)")
    typer.echo(f"  Run `scanlog preview --plan-id {plan_id}` to review.")


@app.command()
def preview(
    plan_id: Optional[int] = typer.Option(None, "--plan-id", help="プランID"),
    latest: bool = typer.Option(False, "--latest", help="最新プランを表示"),
) -> None:
    """スキャンプランの内容を表示する"""
    with get_session() as session:
        if latest:
            plan = get_latest_plan(session)
        elif plan_id is not None:
            plan = get_plan_by_id(session, plan_id)
        else:
            typer.echo("Error: --plan-id または --latest を指定してください", err=True)
            raise typer.Exit(1)

        if plan is None:
            typer.echo("Error: プランが見つかりません", err=True)
            raise typer.Exit(1)

        items = get_plan_items(session, plan.id)

        typer.echo(f"Plan ID : {plan.id}")
        typer.echo(f"Mode    : {plan.mode}")
        typer.echo(f"Status  : {plan.status}")
        typer.echo(f"Created : {plan.created_at}")
        typer.echo(f"Items   : {len(items)}")
        typer.echo("")
        typer.echo(f"{'#':<4} {'type':<12} {'mode':<10} {'reason':<16} {'exec_status':<14} path")
        typer.echo("-" * 90)
        for i, item in enumerate(items, 1):
            exec_status = item.execution_status or "pending"
            typer.echo(f"{i:<4} {item.target_type:<12} {item.scan_mode:<10} {item.target_reason:<16} {exec_status:<14} {item.target_path}")


@app.command()
def approve(plan_id: int = typer.Option(..., "--plan-id", help="承認するプランID")) -> None:
    """スキャンプランを承認する"""
    with get_session() as session:
        plan = get_plan_by_id(session, plan_id)
        if plan is None:
            typer.echo(f"Error: plan_id={plan_id} が見つかりません", err=True)
            raise typer.Exit(1)

        plan.status = "approved"

    typer.echo(f"Plan {plan_id} approved.")


@app.command()
def execute(plan_id: int = typer.Option(..., "--plan-id", help="実行するプランID")) -> None:
    """承認済みプランのスキャンを実行する"""
    with get_session() as session:
        plan = get_plan_by_id(session, plan_id)
        if plan is None:
            typer.echo(f"Error: plan_id={plan_id} が見つかりません", err=True)
            raise typer.Exit(1)

        if plan.status not in ("approved", "executing"):
            typer.echo(f"Error: plan_id={plan_id} は approved 状態ではありません（現在: {plan.status}）", err=True)
            raise typer.Exit(1)

        pending_items = get_pending_plan_items(session, plan_id)
        if not pending_items:
            typer.echo("すべて完了済みです。")
            return

        raw_items = [
            {
                "id": item.id,
                "target_path": item.target_path,
                "target_type": item.target_type,
                "scan_mode": item.scan_mode,
            }
            for item in pending_items
        ]
        plan.status = "executing"

    # ScanRun を作成
    with get_session() as session:
        run = ScanRun(
            plan_id=plan_id,
            started_at=datetime.now(),
            status="running",
        )
        session.add(run)
        session.flush()
        run_id = run.id

    typer.echo(f"Executing plan {plan_id} ({len(raw_items)} target(s)) ...")

    file_items = [i for i in raw_items if i["target_type"] == "file"]
    dir_items = [i for i in raw_items if i["target_type"] != "file"]

    run_failed = False
    all_results: list[tuple[dict, str, int, list[dict], str]] = []

    # --- file バッチ（全 file target を1バッチ）---
    if file_items:
        file_paths = [i["target_path"] for i in file_items]
        with get_session() as session:
            batch = ScanBatch(
                run_id=run_id,
                batch_type="file",
                status="running",
                started_at=datetime.now(),
            )
            session.add(batch)
            session.flush()
            batch_id = batch.id

        typer.echo(f"  [file batch] {len(file_paths)} file(s) ...")
        try:
            raw_output, exit_code, command_line = run_batch_scan(file_paths)
            batch_status = "completed"
        except Exception as e:
            typer.echo(f"  Error: {e}", err=True)
            batch_status = "failed"
            raw_output, exit_code, command_line = "", 1, ""
            run_failed = True

        entries_all = parse_output(raw_output)

        # 各 file_item に対応するエントリを割り当て
        entries_by_path: dict[str, list[dict]] = {}
        for e in entries_all:
            entries_by_path.setdefault(e["scanned_path"], []).append(e)

        with get_session() as session:
            batch = session.get(ScanBatch, batch_id)
            batch.command_line = command_line
            batch.status = batch_status
            batch.finished_at = datetime.now()

            for item in file_items:
                item_entries = entries_by_path.get(item["target_path"], [])
                result_status = _calc_result_status(item_entries) if item_entries else ("failed" if batch_status == "failed" else "clean")
                exec_status = "failed" if batch_status == "failed" else "completed"

                result = ScanResult(
                    run_id=run_id,
                    batch_id=batch_id,
                    plan_item_id=item["id"],
                    target_path=item["target_path"],
                    target_type=item["target_type"],
                    result_status=result_status,
                    raw_output=raw_output,
                    exit_code=exit_code,
                )
                session.add(result)
                session.flush()

                for e in item_entries:
                    session.add(ScanResultEntry(
                        scan_result_id=result.id,
                        scanned_path=e["scanned_path"],
                        entry_status=e["entry_status"],
                        virus_name=e["virus_name"],
                        raw_line=e["raw_line"],
                    ))

                plan_item = session.get(PlanItem, item["id"])
                plan_item.execution_status = exec_status
                plan_item.batch_id = batch_id
                plan_item.last_run_id = run_id

                all_results.append((item, raw_output, exit_code, item_entries, result_status))

    # --- directory バッチ（1件ずつ）---
    for item in dir_items:
        with get_session() as session:
            batch = ScanBatch(
                run_id=run_id,
                batch_type="directory",
                status="running",
                started_at=datetime.now(),
            )
            session.add(batch)
            session.flush()
            batch_id = batch.id

        typer.echo(f"  [directory] {item['target_path']} ...")
        try:
            raw_output, exit_code = run_scan(item["target_path"], item["scan_mode"])
            command_line = f"clamscan -r --no-summary {item['target_path']}"
            batch_status = "completed"
            exec_status = "completed"
        except Exception as e:
            typer.echo(f"  Error: {e}", err=True)
            raw_output, exit_code, command_line = "", 1, ""
            batch_status = "failed"
            exec_status = "failed"
            run_failed = True

        entries = parse_output(raw_output)
        result_status = _calc_result_status(entries) if entries else ("failed" if exec_status == "failed" else "clean")

        # only-clamav_error → skipped
        if exec_status == "completed" and entries and all(e["entry_status"] == "clamav_error" for e in entries):
            exec_status = "skipped"

        with get_session() as session:
            batch = session.get(ScanBatch, batch_id)
            batch.command_line = command_line
            batch.status = batch_status
            batch.finished_at = datetime.now()

            result = ScanResult(
                run_id=run_id,
                batch_id=batch_id,
                plan_item_id=item["id"],
                target_path=item["target_path"],
                target_type=item["target_type"],
                result_status=result_status,
                raw_output=raw_output,
                exit_code=exit_code,
            )
            session.add(result)
            session.flush()

            for e in entries:
                session.add(ScanResultEntry(
                    scan_result_id=result.id,
                    scanned_path=e["scanned_path"],
                    entry_status=e["entry_status"],
                    virus_name=e["virus_name"],
                    raw_line=e["raw_line"],
                ))

            plan_item = session.get(PlanItem, item["id"])
            plan_item.execution_status = exec_status
            plan_item.batch_id = batch_id
            plan_item.last_run_id = run_id

        all_results.append((item, raw_output, exit_code, entries, result_status))

    # 最終ステータス更新
    with get_session() as session:
        run = session.get(ScanRun, run_id)
        run.finished_at = datetime.now()
        run.status = "failed" if run_failed else "completed"

        plan = get_plan_by_id(session, plan_id)
        plan.status = "failed" if run_failed else "completed"

    final_status = "failed" if run_failed else "completed"
    typer.echo(f"\nDone. plan_id={plan_id} status={final_status}")
    for item, _, _, entries, result_status in all_results:
        typer.echo(f"  [{result_status.upper()}] {item['target_path']}")
        for e in entries:
            if e["entry_status"] == "infected":
                typer.echo(f"    [INFECTED] {e['scanned_path']} ({e['virus_name']})")
        clamav_errors = [e for e in entries if e["entry_status"] == "clamav_error"]
        if clamav_errors:
            typer.echo(f"    {len(clamav_errors)} file(s) skipped (could not be accessed by ClamAV).")


@watch_app.command("add")
def watch_add(path: str = typer.Argument(..., help="監視対象のディレクトリまたはファイルパス")) -> None:
    """監視対象 path を登録する"""
    resolved = str(Path(path).resolve())
    with get_session() as session:
        wp = add_watch_path(session, resolved)
        session.flush()
        wp_id = wp.id
    typer.echo(f"Added: [{wp_id}] {resolved}")


@watch_app.command("list")
def watch_list() -> None:
    """登録済みの監視対象 path を一覧表示する"""
    with get_session() as session:
        paths = list_watch_paths(session)
        if not paths:
            typer.echo("登録された監視対象はありません")
            return
        typer.echo(f"{'ID':<4} {'enabled':<8} {'created_at':<22} path")
        typer.echo("-" * 80)
        for wp in paths:
            enabled_str = "yes" if wp.enabled else "no"
            created = str(wp.created_at)[:19] if wp.created_at else "-"
            typer.echo(f"{wp.id:<4} {enabled_str:<8} {created:<22} {wp.path}")


@watch_app.command("remove")
def watch_remove(path: str = typer.Argument(..., help="削除する監視対象パス")) -> None:
    """監視対象 path を登録から削除する"""
    resolved = str(Path(path).resolve())
    with get_session() as session:
        removed = remove_watch_path(session, resolved)
    if not removed:
        typer.echo(f"Error: {resolved} は登録されていません", err=True)
        raise typer.Exit(1)
    typer.echo(f"Removed: {resolved}")


if __name__ == "__main__":
    app()
