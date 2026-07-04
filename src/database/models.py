from datetime import datetime
from sqlalchemy import Integer, Text, Boolean, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from src.database.db import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text, unique=True)
    url_hash: Mapped[str | None] = mapped_column(Text, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    salary_range: Mapped[str | None] = mapped_column(Text)
    date_found: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    date_posted: Mapped[str | None] = mapped_column(Text)
    ai_score: Mapped[int | None] = mapped_column(Integer)
    ai_reason: Mapped[str | None] = mapped_column(Text)
    ai_red_flags: Mapped[str | None] = mapped_column(Text)
    ai_missing_skills: Mapped[str | None] = mapped_column(Text)
    apply_priority: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="new")
    company_rejected_me: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    applied_date: Mapped[datetime | None] = mapped_column(DateTime)


class ScanLog(Base):
    __tablename__ = "scan_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    source: Mapped[str | None] = mapped_column(Text)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    jobs_new: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(Float)


class RejectedCompany(Base):
    __tablename__ = "rejected_companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(Text, unique=True)
