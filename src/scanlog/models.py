from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
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


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_plans.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("scan_runs.id"), nullable=True)
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
