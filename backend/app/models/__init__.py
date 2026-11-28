from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint, func
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
    recommended_persistence: Mapped[str] = mapped_column(String(16), default="jdbc")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    # 当前选择
    archetype: Mapped[str] = mapped_column(String(64), default="ARCH-CRUD")
    domain: Mapped[str] = mapped_column(String(64), default="DOM-GENERIC")
    # jdbc | mybatis — spa 内持久层组合轴（默认跟工厂现网 JdbcTemplate）
    persistence: Mapped[str] = mapped_column(String(16), default="jdbc")
    # 按需：开题点名 Spring Security 时推荐开；默认关（仅 crypto）
    recommended_spring_security: Mapped[bool] = mapped_column(Boolean, default=False)
    spring_security: Mapped[bool] = mapped_column(Boolean, default=False)
    recommended_ai_assistant: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_assistant: Mapped[bool] = mapped_column(Boolean, default=False)
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
    # 人工履约：none → ready（已审待发）→ delivered（已发出）；与机器质检 zip_ready 分离
    delivery_mark: Mapped[str] = mapped_column(String(16), default="none")
    # 交付复审：轮次、安全区、合卷指纹（运营侧，不进学生 ZIP）
    delivery_review: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    backend_running: Mapped[bool] = mapped_column(Boolean, default=False)
    frontend_running: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ProjectOverrides(Base):
    """出包微调（论文材料展示层）；见 docs/pack-overrides.md。"""

    __tablename__ = "project_overrides"

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class JobKind(str, enum.Enum):
    bake = "bake"
    defense_ppt = "defense_ppt"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    # bake = 一键生成；defense_ppt = 答辩 PPT（不得动 project.status / zip_ready）
    kind: Mapped[str] = mapped_column(String(32), default=JobKind.bake.value)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.queued.value)
    step: Mapped[str] = mapped_column(String(64), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[list[Any]] = mapped_column(JSON, default=list)
    # PPT 页级 Unit 进度（bake 可空）
    units: Mapped[list[Any]] = mapped_column(JSON, default=list)
    error: Mapped[Optional[str]] = mapped_column(Text)
    # bake 失败稳定码；与 bake_fail_classify / docs/bake-fail-analysis.md 同源
    error_code: Mapped[Optional[str]] = mapped_column(String(64))
    # 本任务门禁快照（P0–P3 表 + 清单）；每 Job 一行，历史不覆盖
    gate_report: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
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


class FactoryZhLexicon(Base):
    """工厂级中文词表（列/表/词根）；域·皮可空串表示全局。"""

    __tablename__ = "factory_zh_lexicon"
    __table_args__ = (
        UniqueConstraint(
            "kind",
            "key_name",
            "domain",
            "skin",
            "table_name",
            name="uk_zh_lex",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    key_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    zh: Mapped[str] = mapped_column(String(64), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    skin: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    table_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryStatusCopy(Base):
    """工厂级状态机话术（domain × machine × status → 中文）。

    domain_id='*' 表示跨域壳默认；具名 DOM-* 可覆盖。
    """

    __tablename__ = "factory_status_copy"
    __table_args__ = (
        UniqueConstraint(
            "domain_id",
            "machine_id",
            "status_code",
            name="uk_status_copy",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain_id: Mapped[str] = mapped_column(String(64), nullable=False, default="*", index=True)
    machine_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    label_zh: Mapped[str] = mapped_column(String(64), nullable=False)
    action_zh: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    empty_zh: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    for_roles: Mapped[str] = mapped_column(String(64), nullable=False, default="admin,staff,user")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryDictValue(Base):
    """工厂级字典/枚举值（domain × skin × dict_key × value_code → 中文）。"""

    __tablename__ = "factory_dict_values"
    __table_args__ = (
        UniqueConstraint(
            "domain_id",
            "skin_id",
            "dict_key",
            "value_code",
            name="uk_dict_value",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain_id: Mapped[str] = mapped_column(String(64), nullable=False, default="*", index=True)
    skin_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    dict_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value_code: Mapped[str] = mapped_column(String(64), nullable=False)
    label_zh: Mapped[str] = mapped_column(String(64), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryDemoScript(Base):
    """工厂级演示剧本（domain × skin × script × step → 角色/标题/数据前提）。"""

    __tablename__ = "factory_demo_script"
    __table_args__ = (
        UniqueConstraint(
            "domain_id",
            "skin_id",
            "script_id",
            "step_no",
            name="uk_demo_script_step",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    skin_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    script_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default", index=True)
    step_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    title_zh: Mapped[str] = mapped_column(String(128), nullable=False)
    need_rows: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    seed_fragment_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryAddonSuggest(Base):
    """工厂级开关建议扫词（addon × hint → 证据 / 是否推荐开）。"""

    __tablename__ = "factory_addon_suggest"
    __table_args__ = (
        UniqueConstraint("addon_id", "hint", name="uk_addon_suggest_hint"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    addon_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    addon_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    hint: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_zh: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    summary_zh: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    recommend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deliverable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryCapCard(Base):
    """工厂级能力说明卡（cap → README 段 / 菜单入口 / 关则禁宣称）。"""

    __tablename__ = "factory_cap_card"
    __table_args__ = (
        UniqueConstraint("cap_id", name="uk_cap_card"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cap_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title_zh: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    body_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    auth_line_on: Mapped[str] = mapped_column(Text, nullable=False, default="")
    auth_line_off: Mapped[str] = mapped_column(Text, nullable=False, default="")
    backend_suffix: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    menu_ids: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    claim_needles: Mapped[list[Any]] = mapped_column(JSON, default=list)
    readme_slot: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryErrorCopy(Base):
    """工厂级业务错误码中文（ErrorCode → 学生可见默认句）。"""

    __tablename__ = "factory_error_copy"
    __table_args__ = (
        UniqueConstraint("error_code", name="uk_error_copy"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    error_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    code_num: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message_zh: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryWidgetHint(Base):
    """工厂级字段控件语义提示（标签/键启发式 → widget）。

    类型直映（date→date）仍在代码；本台管可维护的标签/键覆盖。
    """

    __tablename__ = "factory_widget_hint"
    __table_args__ = (
        UniqueConstraint("rule_key", name="uk_widget_hint_rule"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    match_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="label_contains")
    match_pattern: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    when_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    widget: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    note_zh: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryMenuMatrix(Base):
    """工厂级岗位×菜单矩阵（domain × role × menu_id）。"""

    __tablename__ = "factory_menu_matrix"
    __table_args__ = (
        UniqueConstraint("domain_id", "role", "menu_id", name="uk_menu_matrix"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain_id: Mapped[str] = mapped_column(String(64), nullable=False, default="*", index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    menu_id: Mapped[str] = mapped_column(String(64), nullable=False)
    label_zh: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    cap_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    always_on: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryRuleParam(Base):
    """工厂级业务规则参数（domain × rule_id → 数值）。"""

    __tablename__ = "factory_rule_param"
    __table_args__ = (
        UniqueConstraint("domain_id", "rule_id", name="uk_rule_param"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain_id: Mapped[str] = mapped_column(String(64), nullable=False, default="*", index=True)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    label_zh: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    value_num: Mapped[float] = mapped_column(nullable=False, default=0)
    unit_zh: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    schema_key: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryErEdgeCopy(Base):
    """工厂级表关系叙事句（table_a–table_b → 一句中文）。"""

    __tablename__ = "factory_er_edge_copy"
    __table_args__ = (
        UniqueConstraint("table_a", "table_b", name="uk_er_edge_copy"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_a: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    table_b: Mapped[str] = mapped_column(String(64), nullable=False)
    sentence_zh: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryDemoAccount(Base):
    """工厂级测试账号卡（domain × role → 账号三步）。"""

    __tablename__ = "factory_demo_account"
    __table_args__ = (
        UniqueConstraint("domain_id", "role", name="uk_demo_account"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain_id: Mapped[str] = mapped_column(String(64), nullable=False, default="*", index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    password: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    nickname_zh: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    login_hint_zh: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryDiagramTitle(Base):
    """工厂级论文图题模板（diagram_kind × domain → title_tpl）。"""

    __tablename__ = "factory_diagram_title"
    __table_args__ = (
        UniqueConstraint("diagram_kind", "domain_id", name="uk_diagram_title"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    diagram_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    domain_id: Mapped[str] = mapped_column(String(64), nullable=False, default="*", index=True)
    title_tpl: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryDiagramVerb(Base):
    """工厂级实体动作词（domain × entity × verb → 中文动作）。

    论文图内业务动词唯一词源；渲染器不得自带业务词。
    项目 domain.schema.json 的 entities.*.verbs 优先；本表为缺省与跨域默认（domain_id='*'）。
    """

    __tablename__ = "factory_diagram_verb"
    __table_args__ = (
        UniqueConstraint("domain_id", "skin_id", "entity_key", "verb_key", name="uk_diagram_verb"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain_id: Mapped[str] = mapped_column(String(64), nullable=False, default="*", index=True)
    skin_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    entity_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    verb_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_zh: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryUsecaseFlow(Base):
    """工厂级用例描述流程（flow_kind × face → name/summary/flow 模板）。

    face='*' 为默认；performance / cinema 覆盖票务皮。渲染器只读本台，不得再内置事件流整句。
    """

    __tablename__ = "factory_usecase_flow"
    __table_args__ = (
        UniqueConstraint("flow_kind", "face", name="uk_usecase_flow"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flow_kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    face: Mapped[str] = mapped_column(String(32), nullable=False, default="*", index=True)
    name_tpl: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    summary_tpl: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    flow_json: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FactoryThesisAbsorb(Base):
    """终稿吸收厂库记录（独立于 Project；docs/thesis-absorb.md）。"""

    __tablename__ = "factory_thesis_absorb"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # B 层对账键：gf-ta-YYYYMMDD-HHMMSS（编号合同）；列表主脸用 #id
    public_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="thesis")
    focus: Mapped[str] = mapped_column(String(32), nullable=False, default="thesis_impl")
    source_files: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    source_path: Mapped[Optional[str]] = mapped_column(String(512))
    proposal_json: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="stored")
    coverage: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    coverage_note: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    # 机审终裁原值；人改 coverage 后可对照（回灌样本）
    coverage_machine: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    coverage_review_json: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    extract_round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    extractor_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1")
    has_figure_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feature_line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings_json: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    draft_roles: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    draft_entities: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    draft_features: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    # 论文物理/逻辑库表章 → draft schema.sql（忠于原文；空串=未抽出）
    draft_schema_sql: Mapped[str] = mapped_column(Text, nullable=False, default="")
    schema_extract_meta: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    trial_project_id: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
