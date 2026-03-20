from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from scanlog.collector import collect as do_collect
from scanlog.models import PlanItem, ScanPlan, ScanResult, ScanResultEntry, ScanRun
from scanlog.parser import parse_output
from scanlog.repository import get_latest_plan, get_plan_by_id, get_plan_items, get_session, init_db
from scanlog.scanner import run_scan

app = typer.Typer(invoke_without_command=True)


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

        typer.echo(f"Scanning {target} ...")
        try:
            raw_output, exit_code = run_scan(str(target), scan_mode)
            run_status = "completed"
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            run.status = "failed"
            run.finished_at = datetime.now()
            raise typer.Exit(1)

        entries = parse_output(raw_output)
        result_status = _calc_result_status(entries)

        result = ScanResult(
            run_id=run.id,
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
        typer.echo(f"{'#':<4} {'type':<12} {'mode':<10} {'reason':<16} path")
        typer.echo("-" * 80)
        for i, item in enumerate(items, 1):
            typer.echo(f"{i:<4} {item.target_type:<12} {item.scan_mode:<10} {item.target_reason:<16} {item.target_path}")


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

        if plan.status != "approved":
            typer.echo(f"Error: plan_id={plan_id} は approved 状態ではありません（現在: {plan.status}）", err=True)
            raise typer.Exit(1)

        raw_items = [
            {
                "id": item.id,
                "target_path": item.target_path,
                "target_type": item.target_type,
                "scan_mode": item.scan_mode,
            }
            for item in get_plan_items(session, plan_id)
        ]
        plan.status = "executing"

    typer.echo(f"Executing plan {plan_id} ({len(raw_items)} target(s)) ...")

    all_results = []
    failed = False

    for item in raw_items:
        typer.echo(f"  Scanning {item['target_path']} ...")
        try:
            raw_output, exit_code = run_scan(item["target_path"], item["scan_mode"])
        except Exception as e:
            typer.echo(f"  Error: {e}", err=True)
            failed = True
            continue

        entries = parse_output(raw_output)
        result_status = _calc_result_status(entries)
        all_results.append((item, raw_output, exit_code, entries, result_status))

    with get_session() as session:
        run = ScanRun(
            plan_id=plan_id,
            started_at=datetime.now(),
            finished_at=datetime.now(),
            status="completed" if not failed else "failed",
        )
        session.add(run)
        session.flush()

        for item, raw_output, exit_code, entries, result_status in all_results:
            result = ScanResult(
                run_id=run.id,
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

        plan = get_plan_by_id(session, plan_id)
        plan.status = "completed" if not failed else "failed"

    typer.echo(f"\nDone. plan_id={plan_id} status={'completed' if not failed else 'failed'}")
    for item, _, _, entries, result_status in all_results:
        typer.echo(f"  [{result_status.upper()}] {item['target_path']}")
        for e in entries:
            if e["entry_status"] == "infected":
                typer.echo(f"    [INFECTED] {e['scanned_path']} ({e['virus_name']})")
        clamav_errors = [e for e in entries if e["entry_status"] == "clamav_error"]
        if clamav_errors:
            typer.echo(f"    {len(clamav_errors)} file(s) skipped (could not be accessed by ClamAV).")


if __name__ == "__main__":
    app()
