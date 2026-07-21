from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, title="项目摘要")

    id: str = Field(description="项目 ID")
    title: str = Field(description="标题")
    status: str = Field(description="状态")
    archetype: str = Field(description="骨架")
    domain: str = Field(description="领域")
    backend_running: bool = Field(description="后端预览是否在跑")
    frontend_running: bool = Field(description="前端预览是否在跑")
    backend_port: int = Field(description="后端端口")
    frontend_port: int = Field(description="前端端口")
    zip_ready: bool = Field(description="ZIP 是否可下载")
    db_name: str = Field(default="", description="学生库名")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")


class ProjectDetail(ProjectSummary):
    model_config = ConfigDict(from_attributes=True, title="项目详情")

    source_filename: Optional[str] = Field(default=None, description="源材料文件名（多份用分号连接）")
    source_size: int = Field(default=0, description="开题文件大小（字节）")
    recommended_arch: str = Field(description="推荐骨架")
    recommended_domain: str = Field(description="推荐领域")
    confidence: float = Field(description="匹配置信度")
    theme: str = Field(description="主题")
    llm_enabled: bool = Field(description="是否启用 LLM")
    password_hash: str = Field(default="none", description="学生端密码哈希策略")
    match_locked: bool = Field(description="匹配是否锁定")
    match_confirmed: bool = Field(description="匹配是否已确认")
    match_mode: str = Field(description="匹配模式")
    spec: dict[str, Any] = Field(default_factory=dict, description="Spec 配置")
    gates: dict[str, Any] = Field(default_factory=dict, description="门禁结果")
    checklist: list[Any] = Field(default_factory=list, description="开题对照清单")
    workspace_path: Optional[str] = Field(default=None, description="工作区路径")
    zip_path: Optional[str] = Field(default=None, description="ZIP 路径")


class MatchUpdate(BaseModel):
    model_config = ConfigDict(title="匹配更新")

    archetype: Optional[str] = Field(default=None, description="骨架 ID")
    domain: Optional[str] = Field(default=None, description="领域 ID")
    theme: Optional[str] = Field(default=None, description="主题 ID")
    llm_enabled: Optional[bool] = Field(default=None, description="启用 LLM")
    password_hash: Optional[str] = Field(default=None, description="密码哈希策略")
    unlock: Optional[bool] = Field(default=None, description="解锁匹配")
    reset: Optional[bool] = Field(default=None, description="重置为推荐")
    confirm: Optional[bool] = Field(default=None, description="确认匹配")
    ack: Optional[bool] = Field(default=None, description="确认知晓")


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, title="任务")

    id: int = Field(description="任务 ID")
    project_id: str = Field(description="项目 ID")
    status: str = Field(description="状态")
    step: str = Field(description="当前步骤")
    progress: int = Field(description="进度 0–100")
    steps: list[Any] = Field(default_factory=list, description="步骤明细")
    error: Optional[str] = Field(default=None, description="错误信息")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    finished_at: Optional[datetime] = Field(default=None, description="结束时间")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
    project_title: Optional[str] = Field(default=None, description="项目标题")


class ProjectTokenUsage(BaseModel):
    model_config = ConfigDict(title="项目 Token 用量")

    project_id: str = Field(description="项目 ID")
    tokens: int = Field(default=0, description="Token 数")
    calls: int = Field(default=0, description="调用次数")
    last_at: Optional[datetime] = Field(default=None, description="最近调用时间")
    deleted: bool = Field(default=False, description="项目是否已删除")


class DeepSeekSettings(BaseModel):
    model_config = ConfigDict(title="DeepSeek 配置")

    base_url: str = Field(description="API 基址")
    model: str = Field(description="模型名")
    thinking: bool = Field(default=True, description="思考模式")
    key_configured: bool = Field(description="是否已配置 Key")
    key_masked: str = Field(description="Key 掩码")
    parse_spec: bool = Field(default=True, description="解析 Spec")
    match_recommend: bool = Field(default=True, description="匹配推荐 Agent")
    island_fill: bool = Field(default=True, description="业务岛填充")
    auto_fix: bool = Field(default=True, description="自动修复")
    qa_report: bool = Field(default=False, description="质量报告")
    project_token_budget: int = Field(default=100_000, description="单项目 Token 预算")
    monthly_token_budget: int = Field(default=1_000_000, description="月度 Token 预算")
    fix_rounds_max: int = Field(default=5, description="最大修复轮数")
    monthly_tokens_used: int = Field(default=0, description="本月已用 Token")
    project_usages: list[ProjectTokenUsage] = Field(default_factory=list, description="分项目用量")
    deepseek_enabled: bool = Field(default=True, description="是否启用 DeepSeek")
    gemini_enabled: bool = Field(default=False, description="是否启用 Gemini")
    preferred: str = Field(default="deepseek", description="双开时优先厂商")


class DeepSeekUpdate(BaseModel):
    model_config = ConfigDict(title="DeepSeek 配置更新")

    base_url: Optional[str] = Field(default=None, description="API 基址")
    model: Optional[str] = Field(default=None, description="模型名")
    thinking: Optional[bool] = Field(default=None, description="思考模式")
    match_recommend: Optional[bool] = Field(default=None, description="匹配推荐 Agent")
    parse_spec: Optional[bool] = Field(default=None, description="解析 Spec")
    island_fill: Optional[bool] = Field(default=None, description="业务岛填充")
    auto_fix: Optional[bool] = Field(default=None, description="自动修复")
    qa_report: Optional[bool] = Field(default=None, description="质量报告")
    project_token_budget: Optional[int] = Field(default=None, description="单项目 Token 预算")
    monthly_token_budget: Optional[int] = Field(default=None, description="月度 Token 预算")
    fix_rounds_max: Optional[int] = Field(default=None, description="最大修复轮数")
    deepseek_enabled: Optional[bool] = Field(default=None, description="启用 DeepSeek")
    gemini_enabled: Optional[bool] = Field(default=None, description="启用 Gemini")
    preferred: Optional[str] = Field(default=None, description="双开时优先厂商")


class GeminiSettings(BaseModel):
    model_config = ConfigDict(title="Gemini 配置")

    base_url: str = Field(description="API 基址（OpenAI 兼容）")
    model: str = Field(description="模型名")
    key_configured: bool = Field(description="是否已配置 Key")
    key_masked: str = Field(description="Key 掩码")
    match_recommend: bool = Field(default=True, description="匹配推荐 Agent")
    parse_spec: bool = Field(default=True, description="解析 Spec")
    island_fill: bool = Field(default=True, description="业务岛填充")
    auto_fix: bool = Field(default=True, description="自动修复")
    qa_report: bool = Field(default=False, description="质量报告")
    project_token_budget: int = Field(default=100_000, description="单项目 Token 预算")
    monthly_token_budget: int = Field(default=1_000_000, description="月度 Token 预算")
    fix_rounds_max: int = Field(default=5, description="最大修复轮数")
    monthly_tokens_used: int = Field(default=0, description="本月已用 Token")
    deepseek_enabled: bool = Field(default=True, description="是否启用 DeepSeek")
    gemini_enabled: bool = Field(default=False, description="是否启用 Gemini")
    preferred: str = Field(default="deepseek", description="双开时优先厂商")


class GeminiUpdate(BaseModel):
    model_config = ConfigDict(title="Gemini 配置更新")

    base_url: Optional[str] = Field(default=None, description="API 基址")
    model: Optional[str] = Field(default=None, description="模型名")
    match_recommend: Optional[bool] = Field(default=None, description="匹配推荐 Agent")
    parse_spec: Optional[bool] = Field(default=None, description="解析 Spec")
    island_fill: Optional[bool] = Field(default=None, description="业务岛填充")
    auto_fix: Optional[bool] = Field(default=None, description="自动修复")
    qa_report: Optional[bool] = Field(default=None, description="质量报告")
    project_token_budget: Optional[int] = Field(default=None, description="单项目 Token 预算")
    monthly_token_budget: Optional[int] = Field(default=None, description="月度 Token 预算")
    fix_rounds_max: Optional[int] = Field(default=None, description="最大修复轮数")
    deepseek_enabled: Optional[bool] = Field(default=None, description="启用 DeepSeek")
    gemini_enabled: Optional[bool] = Field(default=None, description="启用 Gemini")
    preferred: Optional[str] = Field(default=None, description="双开时优先厂商")


class DeepSeekBalanceInfo(BaseModel):
    model_config = ConfigDict(title="余额明细")

    currency: str = Field(default="CNY", description="币种")
    total_balance: str = Field(default="0", description="总余额")
    granted_balance: str = Field(default="0", description="赠送余额")
    topped_up_balance: str = Field(default="0", description="充值余额")


class DeepSeekBalance(BaseModel):
    model_config = ConfigDict(title="账户余额")

    ok: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="说明")
    is_available: Optional[bool] = Field(default=None, description="账户是否可用")
    balance_infos: list[DeepSeekBalanceInfo] = Field(default_factory=list, description="余额列表")


class UnsplashSettings(BaseModel):
    model_config = ConfigDict(title="Unsplash 配图配置")

    key_configured: bool = Field(description="是否已配置 Access Key")
    key_masked: str = Field(description="Key 掩码")
    hint: str = Field(
        default="环境变量 UNSPLASH_ACCESS_KEY；用于登录氛围图与门户轮播检索",
        description="配置说明",
    )


class StatsOut(BaseModel):
    model_config = ConfigDict(title="项目统计")

    total: int = Field(description="总数")
    generating: int = Field(description="生成中")
    previewable: int = Field(description="可预览")
    monthly_tokens: int = Field(description="本月 Token")
    monthly_budget: int = Field(description="月度预算")


class SystemInfo(BaseModel):
    model_config = ConfigDict(title="运行环境")

    jdk: str = Field(description="JDK 版本")
    maven: str = Field(description="Maven 版本")
    node: str = Field(description="Node 版本")
    mysql: str = Field(description="学生 MySQL 探测")
    factory_db: str = Field(default="", description="工厂元数据库")
    public_host: str = Field(default="127.0.0.1", description="对外主机")
    bind_host: str = Field(default="127.0.0.1", description="监听主机")
    backend_ports: str = Field(description="后端端口池")
    frontend_ports: str = Field(description="前端端口池")
    used_backend: list[int] = Field(description="已占用后端端口")
    used_frontend: list[int] = Field(description="已占用前端端口")
    managed_backend: list[int] = Field(default_factory=list, description="托管中后端端口")
    managed_frontend: list[int] = Field(default_factory=list, description="托管中前端端口")
    idle_backend: list[int] = Field(default_factory=list, description="可释放后端端口")
    idle_frontend: list[int] = Field(default_factory=list, description="可释放前端端口")
    workspace: str = Field(description="工作区目录")
    uploads: str = Field(description="上传目录")
    skeletons: str = Field(description="骨架目录")


class RuntimeState(BaseModel):
    model_config = ConfigDict(title="预览运行状态")

    backend_status: str = Field(default="stopped", description="后端状态")
    frontend_status: str = Field(default="stopped", description="前端状态")
    backend_port: int = Field(description="后端端口")
    frontend_port: int = Field(description="前端端口")
    public_host: str = Field(default="127.0.0.1", description="对外主机")
    project_status: str = Field(default="", description="项目状态")
    preview_url: Optional[str] = Field(default=None, description="前端预览地址")
    backend_url: Optional[str] = Field(default=None, description="后端地址")
    backend_log_tail: str = Field(default="", description="后端日志尾")
    frontend_log_tail: str = Field(default="", description="前端日志尾")


class ApiOk(BaseModel):
    model_config = ConfigDict(title="通用成功响应")

    ok: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="说明")
    data: Any = Field(default=None, description="附加数据")
