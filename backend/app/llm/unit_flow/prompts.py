"""填岛/标签各 Unit 的 LLM 提示词（唯一来源，旧 Agent 已移除）。"""

from __future__ import annotations

import json
from typing import Any

from app.llm.agents_common import _LABEL_KEYS
from app.llm.unit_flow.context_budget import prepare_unit_user_payload
from app.llm.unit_flow.models import DeliveryPlan, TaskUnit, UnitKind


def build_unit_messages(
    plan: DeliveryPlan,
    unit: TaskUnit,
    *,
    repair_messages: list[dict[str, str]] | None = None,
) -> tuple[list[dict[str, str]], float]:
    """返回 (messages, temperature)。"""
    frozen = plan.frozen
    excerpt = plan.proposal_excerpt
    repair_messages = repair_messages or []

    if unit.kind == UnitKind.island_labels:
        sys = (
            "你是毕设港 Island Label Agent。只输出 JSON："
            '{"labels":{"键":"中文文案"}}\n'
            f"labels 可含: {','.join(_LABEL_KEYS)}。\n"
            "只改 payload.keys 列出的键；禁止改 menus/capabilities/路由/表结构。\n"
            "文案必须贴合领域，禁止其它领域错词（如宿舍系统勿写馆内/借阅）。"
            "authLead 禁止写入材料头/开题报告字样。"
        )
        user = prepare_unit_user_payload(
            {
                "domain": frozen.domain,
                "title": frozen.title,
                "keys": unit.payload.get("keys"),
                "current": unit.payload.get("current"),
                "proposal_excerpt": excerpt,
            },
            budget_chars=unit.budget_chars,
        )
        temp = 0.35
    elif unit.kind == UnitKind.island_seeds:
        sys = (
            "你是毕设港 Island Seed Agent。只输出 JSON："
            '{"seeds":{"noticeTitle":"...","noticeBody":"..."}}\n'
            "只改 payload.keys；公告正文须贴合领域已实现功能，禁止编造。"
        )
        user = prepare_unit_user_payload(
            {
                "domain": frozen.domain,
                "title": frozen.title,
                "keys": unit.payload.get("keys"),
                "current": unit.payload.get("current"),
                "proposal_excerpt": excerpt,
            },
            budget_chars=unit.budget_chars,
        )
        temp = 0.35
    elif unit.kind == UnitKind.island_entities:
        sys = (
            "你是毕设港 Island Entity Agent。只输出 JSON："
            '{"entities":{"ticket":{"label","labelPlural","verbs","states"}}}\n'
            "只改 payload.keys 里的实体；label 须为短动作名词（借阅/预约/挂号），禁止带「记录」。"
        )
        user = prepare_unit_user_payload(
            {
                "domain": frozen.domain,
                "title": frozen.title,
                "keys": unit.payload.get("keys"),
                "current": unit.payload.get("current"),
                "proposal_excerpt": excerpt,
            },
            budget_chars=unit.budget_chars,
        )
        temp = 0.35
    elif unit.kind == UnitKind.island_roles:
        sys = (
            "你是毕设港 Island Roles Agent。只输出 JSON："
            '{"roles":{"user":{"label"},"admin":{"label"},"subadmin":{"label"},'
            '"staff_posts":[{"id","label"}]}}\n'
            "开题/材料里写了什么岗位称呼就原样填，禁止改写、近义替换或润色；"
            "禁止增删角色 id、禁止改 kind/packs；材料未写角色则不要输出 roles。"
        )
        user = prepare_unit_user_payload(
            {
                "domain": frozen.domain,
                "title": frozen.title,
                "current_roles": unit.payload.get("current_roles"),
                "proposal_excerpt": excerpt,
            },
            budget_chars=unit.budget_chars,
        )
        temp = 0.35
    elif unit.kind == UnitKind.er_labels:
        sys = (
            "你是毕设港 ER Label Agent。只输出 JSON：\n"
            '{"tables":{"表名":"中文实体名"},'
            '"columns":{"表名":{"列名":"中文属性名"}},'
            '"relations":{"联系名":"中文联系名"}}\n'
            "规则：只翻译 gaps 里列出的项；纯中文短名（实体≤8字、属性≤8字、联系≤6字）；"
            "联系名必须是动词或动宾（发布/指派/属于/接收…），禁止用实体名；"
            "禁止拼音/英文/代码；不要发明 gaps 以外的键。"
        )
        user = {
            "domain": frozen.domain,
            "title": frozen.title,
            "gaps": unit.payload.get("gaps"),
        }
        temp = 0.2
    elif unit.kind == UnitKind.module_labels:
        sys = (
            "你是毕设港 Module Label Agent。只输出 JSON："
            '{"nodes":{"节点id":"中文模块名"}}\n'
            "规则：只翻译/微调 target 列出的 id；纯中文短名（≤10字）；"
            "必须贴合开题材料用语，禁止发明 target 以外的模块；禁止拼音/英文/代码。"
        )
        user = prepare_unit_user_payload(
            {
                "domain": frozen.domain,
                "title": frozen.title,
                "scope": unit.payload.get("scope"),
                "target": unit.payload.get("target"),
                "proposal_excerpt": excerpt,
            },
            budget_chars=unit.budget_chars,
        )
        temp = 0.2
    elif unit.kind == UnitKind.testcase_labels:
        sys = (
            "你是毕设港 Testcase Label Agent。只输出 JSON：\n"
            '{"cases":{"TC-XXX-001":{"precondition":"...","steps":"...","input":"...","expected":"..."}}}\n'
            "硬约束：\n"
            "1) 只能改 target 里已有的 id；禁止新增/删除用例；禁止改 id/module/item；\n"
            "2) 文案必须描述该菜单已实现操作，贴合开题用语但禁止发明未实现功能；\n"
            "3) steps 用①②③…；中文为主；input 可含 username=admin 这类演示数据；\n"
            "4) 不要写 actual/verdict；不要输出 target 以外的键。"
        )
        user = prepare_unit_user_payload(
            {
                "domain": frozen.domain,
                "title": frozen.title,
                "target": unit.payload.get("target"),
                "proposal_excerpt": excerpt,
            },
            budget_chars=unit.budget_chars,
        )
        temp = 0.2
    elif unit.kind == UnitKind.ppt_page:
        role = str(unit.payload.get("role") or "bullets")
        sys = (
            "你是毕设港答辩 PPT 整形 Agent。只输出 JSON：\n"
            '{"page_id":"...","title":"...","bullets":[{"id":"...","text":"...","source_refs":["..."]}],'
            '"table":{"headers":["..."],"rows":[["..."]]}}\n'
            "硬约束：\n"
            "1) 只整形开题∪实包已有内容为答辩要点；禁止编造模块、中间件、技术名、未实现能力；\n"
            "2) 技术名必须落在 allowlist.tech；菜单/能力表述须贴合 allowlist.menus；\n"
            "3) bullets 只能使用 payload.bullet_ids 中的 id，条数与 id 对齐；每条 text≤72字；\n"
            "4) table 仅当 role=table 时输出，行列贴合 payload.table_shape；否则省略 table；\n"
            "5) source_refs 只能取自 payload.allowed_refs；page_id 必须等于 payload.page_id。"
        )
        user = prepare_unit_user_payload(
            {
                "domain": frozen.domain,
                "title": frozen.title,
                "persistence": frozen.persistence,
                "spring_security": frozen.spring_security,
                "page_id": unit.payload.get("page_id"),
                "role": role,
                "page_title": unit.payload.get("page_title"),
                "bullet_ids": unit.payload.get("bullet_ids"),
                "table_shape": unit.payload.get("table_shape"),
                "allowlist": unit.payload.get("allowlist"),
                "allowed_refs": unit.payload.get("allowed_refs"),
                "evidence_snip": unit.payload.get("evidence_snip"),
                "fallback_hint": unit.payload.get("fallback_hint"),
                "proposal_excerpt": excerpt,
            },
            budget_chars=unit.budget_chars,
        )
        temp = 0.25
    else:
        raise ValueError(f"unknown unit kind: {unit.kind}")

    messages: list[dict[str, str]] = [
        {"role": "system", "content": sys},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]
    messages.extend(repair_messages)
    return messages, temp
