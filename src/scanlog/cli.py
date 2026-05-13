from pathlib import Path

import typer

from scanlog.models import ScanResult, ScanResultEntry, WatchPath
from scanlog.repository import (
    add_watch_path,
    get_recent_scan_results,
    get_session,
    init_db,
    list_watch_paths,
    remove_watch_path,
)
from scanlog.scanner import iter_batch_scan, run_scan
from scanlog.watcher import DEFAULT_EXCLUDE_DIRS, detect_changes, scan_directory, update_inventory

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
    """ファイルまたはディレクトリを即時スキャンする"""
    from datetime import datetime
    from scanlog.parser import parse_output

    target = Path(path).resolve()
    if not target.exists():
        typer.echo(f"Error: {path} が存在しません", err=True)
        raise typer.Exit(1)

    target_type = "directory" if target.is_dir() else "file"
    typer.echo(f"Scanning {target} ...")

    try:
        if target_type == "file":
            all_stdout = []
            max_exit_code = 0
            for chunk_stdout, chunk_exit_code, _ in iter_batch_scan([str(target)]):
                all_stdout.append(chunk_stdout)
                max_exit_code = max(max_exit_code, chunk_exit_code)
            raw_output = "\n".join(all_stdout)
            exit_code = max_exit_code
        else:
            raw_output, exit_code = run_scan(str(target), "recursive")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    entries = parse_output(raw_output)
    result_status = _calc_result_status(entries)

    with get_session() as session:
        result = ScanResult(
            mode="manual",
            scanned_at=datetime.now(),
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

    _print_scan_result(entries, result_status)


@app.command()
def recent(
    limit: int = typer.Option(10, "--limit", help="表示件数（デフォルト: 10）"),
) -> None:
    """直近のスキャン結果を表示する"""
    with get_session() as session:
        results = get_recent_scan_results(session, limit)
        if not results:
            typer.echo("スキャン結果がありません。")
            return

        typer.echo(f"{'#':<4} {'scanned_at':<22} {'mode':<8} {'status':<10} target_path")
        typer.echo("-" * 80)
        for i, r in enumerate(results, 1):
            scanned_at = str(r.scanned_at)[:19] if r.scanned_at else "-"
            typer.echo(f"{i:<4} {scanned_at:<22} {(r.mode or '-'):<8} {(r.result_status or '-'):<10} {r.target_path}")
            if r.result_status == "infected":
                entries = session.query(ScanResultEntry).filter(
                    ScanResultEntry.scan_result_id == r.id,
                    ScanResultEntry.entry_status == "infected",
                ).all()
                for e in entries:
                    typer.echo(f"     -> {e.virus_name} ({e.scanned_path})")


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


@watch_app.command("run")
def watch_run() -> None:
    """差分ありファイルのみをスキャンする（巡回型監視）

    enabled な全 watch_path を対象に差分チェックを行い、
    変化のあったファイルのみ ClamAV でスキャンする。
    node_modules / .venv 等の重い依存ディレクトリはデフォルトで除外する
    （安全だからではなく、監視コスト削減のためのポリシー）。
    """
    from datetime import datetime
    from scanlog.parser import parse_output

    with get_session() as session:
        all_wps = list_watch_paths(session)
        enabled_wps = [wp for wp in all_wps if wp.enabled]
        wp_info = [{"id": wp.id, "path": wp.path} for wp in enabled_wps]

    if not wp_info:
        typer.echo("監視対象が登録されていません。`scanlog watch add <path>` で登録してください。")
        return

    targets_by_wp_id: dict[int, list] = {}
    all_files_by_wp_id: dict[int, list] = {}

    with get_session() as session:
        for info in wp_info:
            wp = session.get(WatchPath, info["id"])
            files = scan_directory(wp.path, DEFAULT_EXCLUDE_DIRS)
            targets = detect_changes(session, wp, files)
            targets_by_wp_id[wp.id] = targets
            all_files_by_wp_id[wp.id] = files

    all_targets = [t for targets in targets_by_wp_id.values() for t in targets]
    scan_results_map: dict[str, str] = {}
    run_failed = False

    if not all_targets:
        typer.echo("変更ファイルなし。スキャンをスキップします。")
    else:
        typer.echo(f"{len(all_targets)} ファイルの差分を検出。スキャンを開始します...")
        file_paths = [str(t) for t in all_targets]
        total = len(file_paths)
        done = 0
        counts: dict[str, int] = {}

        try:
            for chunk_stdout, chunk_exit_code, chunk_paths in iter_batch_scan(file_paths):
                chunk_entries_all = parse_output(chunk_stdout)
                entries_by_path: dict[str, list[dict]] = {}
                for e in chunk_entries_all:
                    entries_by_path.setdefault(e["scanned_path"], []).append(e)

                done += len(chunk_paths)
                pct = done / total * 100
                print(f"\r  [{done}/{total}] {pct:.1f}%...", end="", flush=True)

                with get_session() as session:
                    for path in chunk_paths:
                        item_entries = entries_by_path.get(path, [])
                        result_status = _calc_result_status(item_entries) if item_entries else "clean"
                        scan_results_map[path] = result_status
                        counts[result_status] = counts.get(result_status, 0) + 1

                        result = ScanResult(
                            mode="watch",
                            scanned_at=datetime.now(),
                            target_path=path,
                            target_type="file",
                            result_status=result_status,
                            raw_output=chunk_stdout,
                            exit_code=chunk_exit_code,
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
            print()

        except Exception as e:
            print()
            typer.echo(f"  Error: {e}", err=True)
            run_failed = True

        final_status = "FAILED" if run_failed else "DONE"
        typer.echo(f"\n[{final_status}] スキャン完了: {done} ファイル")
        typer.echo(f"  clean={counts.get('clean', 0)}  infected={counts.get('infected', 0)}  error={counts.get('error', 0)}")

        for path, result_status in scan_results_map.items():
            if result_status == "infected":
                typer.echo(f"  [INFECTED] {path}")

    with get_session() as session:
        for info in wp_info:
            wp = session.get(WatchPath, info["id"])
            if wp is None:
                continue
            update_inventory(
                session, wp,
                targets_by_wp_id[wp.id],
                scan_results_map,
                all_files_by_wp_id[wp.id],
            )

    if run_failed:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
