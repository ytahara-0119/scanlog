from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ScanPlan(Base):
    __tablename__ = "scan_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mode: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PlanItem(Base):
    __tablename__ = "plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_plans.id"), nullable=True)
    target_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    scan_mode: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    excluded_by_user: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    exclude_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_batches.id"), nullable=True)
    execution_status: Mapped[str | None] = mapped_column(Text, nullable=True, default="pending")
    last_run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_runs.id"), nullable=True)


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_plans.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScanBatch(Base):
    __tablename__ = "scan_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_runs.id"), nullable=True)
    batch_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    command_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_runs.id"), nullable=True)
    batch_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_batches.id"), nullable=True)
    plan_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("plan_items.id"), nullable=True)
    target_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ScanResultEntry(Base):
    __tablename__ = "scan_result_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_result_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_results.id"), nullable=True)
    scanned_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    virus_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_line: Mapped[str | None] = mapped_column(Text, nullable=True)


class WatchPath(Base):
    """監視対象 path の登録テーブル。
    mode: watch_scan の scan_plan と連携して使用する。
    """

    __tablename__ = "watch_paths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FileInventory(Base):
    """監視対象ファイルの最新状態テーブル。
    watch run 実行時に更新され、差分判定の基準データとして使用する。
    sha256 は size または mtime が変化した場合のみ計算・更新する（監視コスト削減）。
    """

    __tablename__ = "file_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watch_path_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("watch_paths.id"), nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mtime: Mapped[float | None] = mapped_column(Float, nullable=True)
    sha256: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 値: clean / infected / error / null（未スキャン）
    last_scan_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ファイルが走査で見つからない場合 True（論理削除）
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
