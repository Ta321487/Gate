from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import SettingRow

DEFAULT_DS = {
    "thinking": True,
    "match_recommend": True,
    "parse_spec": True,
    "island_fill": True,
    "er_labels": True,
    "auto_fix": True,
    "qa_report": False,
}

LLM_PROVIDERS = ("deepseek", "gemini")


@dataclass
class ProviderEndpoint:
    name: str
    api_key: str
    base_url: str
    model: str
    thinking: bool = False

    @property
    def configured(self) -> bool:
        return bool((self.api_key or "").strip())


@dataclass
class LlmRuntime:
    """一次 Job / 上传用的 LLM 运行时（可同时启用多家，按 preferred 接力）。"""

    deepseek: ProviderEndpoint
    gemini: ProviderEndpoint
    deepseek_enabled: bool
    gemini_enabled: bool
    preferred: str
    match_recommend: bool
    parse_spec: bool
    island_fill: bool
    er_labels: bool
    auto_fix: bool
    qa_report: bool
    fix_rounds_max: int
    project_token_budget: int
    monthly_token_budget: int

    @property
    def configured(self) -> bool:
        return bool(self.endpoint_chain())

    @property
    def provider(self) -> str:
        """兼容旧代码：返回链上第一家。"""
        chain = self.endpoint_chain()
        return chain[0].name if chain else normalize_provider(self.preferred)

    @property
    def thinking(self) -> bool:
        chain = self.endpoint_chain()
        return chain[0].thinking if chain else False

    def stage_on(self, stage: str) -> bool:
        return {
            "match_recommend": self.match_recommend,
            "parse_spec": self.parse_spec,
            "island_fill": self.island_fill,
            "er_labels": self.er_labels,
            "auto_fix": self.auto_fix,
            "qa_report": self.qa_report,
        }.get(stage, False)

    def endpoint_chain(self) -> list[ProviderEndpoint]:
        """已启用且已配 Key 的厂商，preferred 优先，其余作后备。"""
        pref = normalize_provider(self.preferred)
        order = [pref] + [p for p in LLM_PROVIDERS if p != pref]
        out: list[ProviderEndpoint] = []
        for name in order:
            if name == "deepseek" and self.deepseek_enabled and self.deepseek.configured:
                out.append(self.deepseek)
            elif name == "gemini" and self.gemini_enabled and self.gemini.configured:
                out.append(self.gemini)
        return out


def normalize_provider(value: str | None, fallback: str = "deepseek") -> str:
    p = (value or "").strip().lower() or fallback
    return p if p in LLM_PROVIDERS else fallback


def _migrate_llm_flags(cfg: dict, env_provider: str) -> dict:
    """旧版单选 provider → 双开关；缺省保持 DeepSeek 开启。"""
    out = dict(cfg or {})
    if "deepseek_enabled" in out or "gemini_enabled" in out:
        out["deepseek_enabled"] = bool(out.get("deepseek_enabled", True))
        out["gemini_enabled"] = bool(out.get("gemini_enabled", False))
        out["preferred"] = normalize_provider(str(out.get("preferred") or env_provider or "deepseek"))
        return out
    old = normalize_provider(str(out.get("provider") or env_provider or "deepseek"))
    if old == "gemini":
        out["deepseek_enabled"] = False
        out["gemini_enabled"] = True
        out["preferred"] = "gemini"
    else:
        out["deepseek_enabled"] = True
        out["gemini_enabled"] = False
        out["preferred"] = "deepseek"
    return out


async def get_llm_flags(db: AsyncSession) -> dict:
    s = get_settings()
    row = await db.get(SettingRow, "llm")
    cfg = _migrate_llm_flags(dict(row.value or {}) if row else {}, s.llm_provider)
    return {
        "deepseek_enabled": bool(cfg["deepseek_enabled"]),
        "gemini_enabled": bool(cfg["gemini_enabled"]),
        "preferred": normalize_provider(str(cfg["preferred"])),
    }


async def set_llm_flags(
    db: AsyncSession,
    *,
    deepseek_enabled: bool | None = None,
    gemini_enabled: bool | None = None,
    preferred: str | None = None,
) -> dict:
    s = get_settings()
    row = await db.get(SettingRow, "llm")
    cfg = _migrate_llm_flags(dict(row.value or {}) if row else {}, s.llm_provider)
    if deepseek_enabled is not None:
        cfg["deepseek_enabled"] = bool(deepseek_enabled)
    if gemini_enabled is not None:
        cfg["gemini_enabled"] = bool(gemini_enabled)
    if preferred is not None:
        cfg["preferred"] = normalize_provider(preferred)
    # 清理旧字段，避免下次再被误读
    cfg.pop("provider", None)
    if not row:
        row = SettingRow(key="llm", value=cfg)
        db.add(row)
    else:
        row.value = cfg
    await db.commit()
    return {
        "deepseek_enabled": bool(cfg["deepseek_enabled"]),
        "gemini_enabled": bool(cfg["gemini_enabled"]),
        "preferred": normalize_provider(str(cfg["preferred"])),
    }


# 兼容旧 import
async def get_llm_provider(db: AsyncSession) -> str:
    flags = await get_llm_flags(db)
    if flags["gemini_enabled"] and not flags["deepseek_enabled"]:
        return "gemini"
    if flags["deepseek_enabled"] and not flags["gemini_enabled"]:
        return "deepseek"
    return flags["preferred"]


async def set_llm_provider(db: AsyncSession, provider: str) -> str:
    p = normalize_provider(provider)
    if p == "gemini":
        await set_llm_flags(db, deepseek_enabled=False, gemini_enabled=True, preferred="gemini")
    else:
        await set_llm_flags(db, deepseek_enabled=True, gemini_enabled=False, preferred="deepseek")
    return p


async def load_llm_runtime(db: AsyncSession) -> LlmRuntime:
    s = get_settings()
    row = await db.get(SettingRow, "deepseek")
    cfg = dict(row.value or {}) if row else {}
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

    g_row = await db.get(SettingRow, "gemini")
    g_cfg = dict(g_row.value or {}) if g_row else {}
    if g_cfg.get("base_url"):
        s.gemini_base_url = str(g_cfg["base_url"])
    if g_cfg.get("model"):
        s.gemini_model = str(g_cfg["model"])

    flags = await get_llm_flags(db)
    return LlmRuntime(
        deepseek=ProviderEndpoint(
            name="deepseek",
            api_key=s.deepseek_api_key or "",
            base_url=str(cfg.get("base_url") or s.deepseek_base_url),
            model=str(cfg.get("model") or s.deepseek_model),
            thinking=bool(cfg.get("thinking", True)),
        ),
        gemini=ProviderEndpoint(
            name="gemini",
            api_key=s.gemini_api_key or "",
            base_url=str(g_cfg.get("base_url") or s.gemini_base_url),
            model=str(g_cfg.get("model") or s.gemini_model),
            thinking=False,
        ),
        deepseek_enabled=flags["deepseek_enabled"],
        gemini_enabled=flags["gemini_enabled"],
        preferred=flags["preferred"],
        match_recommend=bool(cfg.get("match_recommend", True)),
        parse_spec=bool(cfg.get("parse_spec", True)),
        island_fill=bool(cfg.get("island_fill", True)),
        er_labels=bool(cfg.get("er_labels", True)),
        auto_fix=bool(cfg.get("auto_fix", True)),
        qa_report=bool(cfg.get("qa_report", False)),
        fix_rounds_max=int(cfg.get("fix_rounds_max", s.fix_rounds_max)),
        project_token_budget=int(cfg.get("project_token_budget", s.project_token_budget)),
        monthly_token_budget=int(cfg.get("monthly_token_budget", s.monthly_token_budget)),
    )
