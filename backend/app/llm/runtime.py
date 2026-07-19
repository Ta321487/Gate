from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import SettingRow

DEFAULT_DS = {
    "thinking": True,
    "parse_spec": True,
    "island_fill": True,
    "auto_fix": True,
    "qa_report": False,
}


@dataclass
class LlmRuntime:
    """一次 Job / 上传用的 LLM 运行时配置（内存 settings + DB 开关）。"""

    api_key: str
    base_url: str
    model: str
    thinking: bool
    parse_spec: bool
    island_fill: bool
    auto_fix: bool
    qa_report: bool
    fix_rounds_max: int
    project_token_budget: int
    monthly_token_budget: int

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())

    def stage_on(self, stage: str) -> bool:
        return {
            "parse_spec": self.parse_spec,
            "island_fill": self.island_fill,
            "auto_fix": self.auto_fix,
            "qa_report": self.qa_report,
        }.get(stage, False)


async def load_llm_runtime(db: AsyncSession) -> LlmRuntime:
    s = get_settings()
    row = await db.get(SettingRow, "deepseek")
    cfg = dict(row.value or {}) if row else {}
    # 与 system._hydrate 对齐：DB 优先
    if cfg.get("base_url"):
        s.deepseek_base_url = str(cfg["base_url"])
    if cfg.get("model"):
        s.deepseek_model = str(cfg["model"])
    if "project_token_budget" in cfg:
        s.project_token_budget = int(cfg["project_token_budget"])
    if "monthly_token_budget" in cfg:
        s.monthly_token_budget = int(cfg["monthly_token_budget"])
    if "fix_rounds_max" in cfg:
        s.fix_rounds_max = int(cfg["fix_rounds_max"])
    return LlmRuntime(
        api_key=s.deepseek_api_key or "",
        base_url=str(cfg.get("base_url") or s.deepseek_base_url),
        model=str(cfg.get("model") or s.deepseek_model),
        thinking=bool(cfg.get("thinking", True)),
        parse_spec=bool(cfg.get("parse_spec", True)),
        island_fill=bool(cfg.get("island_fill", True)),
        auto_fix=bool(cfg.get("auto_fix", True)),
        qa_report=bool(cfg.get("qa_report", False)),
        fix_rounds_max=int(cfg.get("fix_rounds_max", s.fix_rounds_max)),
        project_token_budget=int(cfg.get("project_token_budget", s.project_token_budget)),
        monthly_token_budget=int(cfg.get("monthly_token_budget", s.monthly_token_budget)),
    )
