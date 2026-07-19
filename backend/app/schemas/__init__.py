from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProjectSummary(BaseModel):
    id: str
    title: str
    status: str
    archetype: str
    domain: str
    backend_running: bool
    frontend_running: bool
    backend_port: int
    frontend_port: int
    zip_ready: bool
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectSummary):
    source_filename: Optional[str] = None
    source_size: int = 0
    recommended_arch: str
    recommended_domain: str
    confidence: float
    theme: str
    llm_enabled: bool
    password_hash: str = "none"
    match_locked: bool
    match_confirmed: bool
    match_mode: str
    db_name: str
    spec: dict[str, Any] = Field(default_factory=dict)
    gates: dict[str, Any] = Field(default_factory=dict)
    checklist: list[Any] = Field(default_factory=list)
    workspace_path: Optional[str] = None
    zip_path: Optional[str] = None


class MatchUpdate(BaseModel):
    archetype: Optional[str] = None
    domain: Optional[str] = None
    theme: Optional[str] = None
    llm_enabled: Optional[bool] = None
    password_hash: Optional[str] = None
    unlock: Optional[bool] = None
    reset: Optional[bool] = None
    confirm: Optional[bool] = None
    ack: Optional[bool] = None


class JobOut(BaseModel):
    id: int
    project_id: str
    status: str
    step: str
    progress: int
    steps: list[Any] = Field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    project_title: Optional[str] = None

    model_config = {"from_attributes": True}


class ProjectTokenUsage(BaseModel):
    project_id: str
    tokens: int = 0
    calls: int = 0
    last_at: Optional[datetime] = None


class DeepSeekSettings(BaseModel):
    base_url: str
    model: str
    thinking: bool = True
    key_configured: bool
    key_masked: str
    parse_spec: bool = True
    island_fill: bool = True
    auto_fix: bool = True
    qa_report: bool = False
    project_token_budget: int = 100_000
    monthly_token_budget: int = 1_000_000
    fix_rounds_max: int = 5
    monthly_tokens_used: int = 0
    project_usages: list[ProjectTokenUsage] = Field(default_factory=list)


class DeepSeekUpdate(BaseModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    thinking: Optional[bool] = None
    parse_spec: Optional[bool] = None
    island_fill: Optional[bool] = None
    auto_fix: Optional[bool] = None
    qa_report: Optional[bool] = None
    project_token_budget: Optional[int] = None
    monthly_token_budget: Optional[int] = None
    fix_rounds_max: Optional[int] = None


class DeepSeekBalanceInfo(BaseModel):
    currency: str = "CNY"
    total_balance: str = "0"
    granted_balance: str = "0"
    topped_up_balance: str = "0"


class DeepSeekBalance(BaseModel):
    ok: bool = True
    message: str = ""
    is_available: Optional[bool] = None
    balance_infos: list[DeepSeekBalanceInfo] = Field(default_factory=list)


class StatsOut(BaseModel):
    total: int
    generating: int
    previewable: int
    monthly_tokens: int
    monthly_budget: int


class SystemInfo(BaseModel):
    jdk: str
    maven: str
    node: str
    mysql: str  # 学生项目库探测
    factory_db: str = ""  # 工厂元数据（多为 SQLite）
    backend_ports: str
    frontend_ports: str
    used_backend: list[int]
    used_frontend: list[int]
    workspace: str
    uploads: str
    skeletons: str


class RuntimeState(BaseModel):
    backend_status: str = "stopped"  # stopped|starting|healthy|error
    frontend_status: str = "stopped"
    backend_port: int
    frontend_port: int
    preview_url: Optional[str] = None
    backend_url: Optional[str] = None
    backend_log_tail: str = ""
    frontend_log_tail: str = ""


class ApiOk(BaseModel):
    ok: bool = True
    message: str = ""
    data: Any = None
