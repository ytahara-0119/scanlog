from datetime import datetime
from pathlib import Path

import typer

from scanlog.models import PlanItem, ScanPlan, ScanResult, ScanResultEntry, ScanRun
from scanlog.parser import parse_output
from scanlog.repository import get_session, init_db
from scanlog.scanner import run_scan

app = typer.Typer(invoke_without_command=True)


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

        if any(e["entry_status"] == "infected" for e in entries):
            result_status = "infected"
        elif any(e["entry_status"] == "error" for e in entries):
            result_status = "error"
        else:
            result_status = "clean"

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

    # 結果表示
    typer.echo(f"\nResult: {result_status.upper()}")
    for e in entries:
        if e["entry_status"] == "infected":
            typer.echo(f"  [INFECTED] {e['scanned_path']} ({e['virus_name']})")
        elif e["entry_status"] == "error":
            typer.echo(f"  [ERROR]    {e['scanned_path']}")
    if result_status == "clean":
        typer.echo(f"  All {len(entries)} file(s) are clean.")


if __name__ == "__main__":
    app()
