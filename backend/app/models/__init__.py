from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProjectStatus(str, enum.Enum):
    needs_confirm = "needs_confirm"
    ready = "ready"
    generating = "generating"
    generated = "generated"
    failed = "failed"
    running = "running"
    archived = "archived"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ProjectStatus.needs_confirm.value)

    source_filename: Mapped[Optional[str]] = mapped_column(String(255))
    source_path: Mapped[Optional[str]] = mapped_column(String(512))
    source_size: Mapped[int] = mapped_column(Integer, default=0)

    # 推荐（锁定默认）
    recommended_arch: Mapped[str] = mapped_column(String(64), default="ARCH-CRUD")
    recommended_domain: Mapped[str] = mapped_column(String(64), default="DOM-GENERIC")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    # 当前选择
    archetype: Mapped[str] = mapped_column(String(64), default="ARCH-CRUD")
    domain: Mapped[str] = mapped_column(String(64), default="DOM-GENERIC")
    theme: Mapped[str] = mapped_column(String(64), default="gen-ink")
    llm_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # none | bcrypt | md5 | sha256 — 学生端密码存储策略，默认明文
    password_hash: Mapped[str] = mapped_column(String(32), default="none")
    match_locked: Mapped[bool] = mapped_column(Boolean, default=True)
    match_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    match_mode: Mapped[str] = mapped_column(String(32), default="recommended")

    db_name: Mapped[str] = mapped_column(String(128), default="")
    backend_port: Mapped[int] = mapped_column(Integer, default=0)
    frontend_port: Mapped[int] = mapped_column(Integer, default=0)

    spec: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    gates: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    checklist: Mapped[list[Any]] = mapped_column(JSON, default=list)

    workspace_path: Mapped[Optional[str]] = mapped_column(String(512))
    zip_path: Mapped[Optional[str]] = mapped_column(String(512))
    zip_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    # 人工履约：none → ready（可交付）→ delivered（已交付）；与机器质检 zip_ready 分离
    delivery_mark: Mapped[str] = mapped_column(String(16), default="none")

    backend_running: Mapped[bool] = mapped_column(Boolean, default=False)
    frontend_running: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.queued.value)
    step: Mapped[str] = mapped_column(String(64), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[list[Any]] = mapped_column(JSON, default=list)
    error: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    stage: Mapped[str] = mapped_column(String(64))
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    detail: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SettingRow(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
