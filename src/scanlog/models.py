from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mode: Mapped[str | None] = mapped_column(Text, nullable=True)
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
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
    last_scan_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
