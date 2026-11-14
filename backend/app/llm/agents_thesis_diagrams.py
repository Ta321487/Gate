"""论文图对账：只审不改。

硬原则（docs/llm-determinism.md）：不确定 → 确定性。
确定性 rubric / 菜单对齐闸先行并穷尽；LLM 只补缺口；可复现新坑须收进闸。
无 Key / 预算不足 / 模型失败 → 确定性 findings 不得消失。禁止写回 model / 导出正文。
真源：docs/thesis-diagram-export.md · M4。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import (
    append_deepseek_log,
    budget_ok,
    chat,
    format_usage_detail,
    record_call,
)
from app.llm.runtime import LlmRuntime
from app.llm.temperature import temperature_for

_SYS = (
    "你是毕设「论文图」对账 Agent。只核对：图/表 model 是否假宣称、是否跟交付包不一致。"
    "禁止改代码、禁止改图、禁止建议排版/美化/几何。"
    "只输出 JSON："
    '{"ok":boolean,"summary":string,'
    '"findings":[{"level":"error|warn|info","msg":string,"where":string}]}\n'
    "where 须形如 er|sequences|activities|usecase_desc|classes|usecases|architecture|modules"
    " 或带下标如 sequences[0]、usecase_desc[1]。\n"
    "【穷尽】必须逐条对照证据包，把本包内全部不一致一次列完；禁止只报前几条、禁止「其余略」。"
    "每条不一致单独一条 finding；deterministic_findings 已列出的不要重复。\n"
    "【真问题优先】error 仅限可对照证据包核实的硬不一致："
    "用例描述/序列的 menu_key 不在执行者可访问菜单；图上实体/类 id 不在证据包。"
    "文案「像不像某业务」、include 语义是否顺眼 → 最多 warn，禁止抬成 error。\n"
    "【禁止误报】has_staff_posts 时：menus.subadmin 为空是常态，办理岗走 admin 菜单裁剪，"
    "禁止报「商家/subadmin 菜单空」；architecture 使用 staff:岗位id（见 staff_post_ids/roleLabels）不算野角色；"
    "购物车与订单各自挂「进行支付」不算重复挂载错误。\n"
    "auth/login/register（source 含 auth）不是交付菜单项，禁止报「不在菜单」。\n"
    "无把握的条目不报；禁止「建议优化排版/交叉/美观」。"
)

_KIND_RE = re.compile(
    r"^(er|sequences|sequence|activities|activity|usecase_desc|classes|"
    r"usecases|architecture|modules)(\[\d+\])?(\.|$)",
    re.I,
)

_NOISE_RE = re.compile(
    r"排版|交叉|重叠|美观|优化体验|建议拖|draw\.io|几何|好看|对齐线"
)


# where 前缀 → (goto 手调/卡片 section, 操作路径)
_FINDING_NAV: list[tuple[str, str, str]] = [
    ("usecase_desc", "usecase_desc", "论文材料 → 需求分析 → 用例描述表 → 手调文字 / 重选主路径"),
    ("usecases", "usecase", "论文材料 → 需求分析 → 用例图"),
    ("sequences", "sequence", "论文材料 → 系统设计 → 系统序列图"),
    ("sequence", "sequence", "论文材料 → 系统设计 → 系统序列图"),
    ("activities", "activity", "论文材料 → 系统设计 → 系统活动图"),
    ("activity", "activity", "论文材料 → 系统设计 → 系统活动图"),
    ("classes", "classes", "论文材料 → 系统设计 → 系统类图"),
    ("architecture", "architecture", "论文材料 → 系统设计 → 系统逻辑架构图"),
    ("modules", "modules", "论文材料 → 系统设计 → 功能模块图 → 手调文字"),
    ("er", "er", "论文材料 → 打开 E-R / 实体属性图（或重 bake 清外键）"),
    ("testcases", "testcases", "论文材料 → 系统测试 → 软件测试用例"),
]


def _nav_for_where(where: str) -> tuple[str, str]:
    w = (where or "").strip().lower()
    for prefix, goto, fix in _FINDING_NAV:
        if w == prefix or w.startswith(prefix + "[") or w.startswith(prefix + "."):
            return goto, fix
    return "", "论文材料 → 对账 findings 对照卡片"


def enrich_finding_nav(f: dict[str, str]) -> dict[str, str]:
    """补 fix / goto，便于前端点跳。已有字段不覆盖。"""
    out = dict(f)
    goto, fix = _nav_for_where(str(out.get("where") or ""))
    if goto and not out.get("goto"):
        out["goto"] = goto
    if fix and not out.get("fix"):
        out["fix"] = fix
    return out


_LLM_HARD_MENU_RE = re.compile(
    r"(菜单|menu[_ ]?key|menuKeys|交付).{0,24}(未含|没有|不一致|不在)|"
    r"(执行者|角色).{0,16}(菜单|侧).{0,12}(不一致|不符)|"
    r"(不在|未列出).{0,12}(类|实体|菜单|角色)",
    re.I,
)


def stamp_finding_trust(
    f: dict[str, str],
    *,
    source: str,
) -> dict[str, str]:
    """标来源与处置口径：规则 error → 须改；其余 → 待核。"""
    out = dict(f)
    src = "rule" if source == "rule" else "llm"
    out["source"] = src
    level = str(out.get("level") or "warn").lower()
    if src == "rule" and level == "error":
        out["trust"] = "must_fix"
        out["badge"] = "须改"
    elif src == "rule":
        out["trust"] = "verify"
        out["badge"] = "规则·留意"
    else:
        out["trust"] = "verify"
        out["badge"] = "LLM·待核"
        # LLM 语义类不得冒充须改：error 降为 warn，除非像菜单硬不一致
        if level == "error" and not _LLM_HARD_MENU_RE.search(str(out.get("msg") or "")):
            out["level"] = "warn"
    return out


def partition_findings(
    findings: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    must: list[dict[str, str]] = []
    verify: list[dict[str, str]] = []
    for f in findings:
        if f.get("trust") == "must_fix":
            must.append(f)
        else:
            verify.append(f)
    return must, verify


def _norm_findings(raw: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw[:48]:
        if isinstance(item, str):
            out.append({"level": "warn", "msg": item[:200], "where": ""})
            continue
        if not isinstance(item, dict):
            continue
        level = str(item.get("level") or "warn").lower()
        if level not in ("error", "warn", "info"):
            level = "warn"
        row: dict[str, str] = {
            "level": level,
            "msg": str(item.get("msg") or item.get("message") or "")[:200],
            "where": str(item.get("where") or "")[:120],
        }
        if item.get("fix"):
            row["fix"] = str(item.get("fix"))[:160]
        if item.get("goto"):
            row["goto"] = str(item.get("goto"))[:64]
        out.append(row)
    return [f for f in out if f["msg"]]


_AUTH_MENU_FALSE_POS = re.compile(
    r"(auth|login|register|登录|注册).{0,24}(不在|未包含|没有).{0,12}(菜单|menus)",
    re.I,
)


_DUP_PAY_NOISE = re.compile(
    r"进行支付.*(重复|两处|不唯一)|重复 include.*支付|支付.*归属不唯一",
    re.I,
)
_SUBADMIN_EMPTY_FALSE_POS = re.compile(
    r"subadmin.{0,12}(菜单为空|未含|空).{0,40}(商家|办理|岗位)|"
    r"(商家|办理).{0,20}subadmin.{0,12}(空|未含)",
    re.I,
)


def _where_family(where: str) -> str:
    w = (where or "").strip().lower()
    m = re.match(
        r"^(er|sequences?|activities?|usecase_desc|classes|usecases|architecture|modules)",
        w,
    )
    return m.group(1) if m else w.split("[", 1)[0].split(".", 1)[0]


def filter_llm_thesis_findings(
    findings: list[dict[str, str]],
    *,
    evidence: dict[str, Any] | None = None,
    deterministic: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """丢掉空话、改结构/几何建议、where 对不上图种的条；滤掉已知误报与规则闸已覆盖项。"""
    ev = evidence if isinstance(evidence, dict) else {}
    staff_ids: set[str] = {
        str(x).strip()
        for x in (ev.get("staff_post_ids") or [])
        if str(x).strip()
    }
    for r in ev.get("architecture_roles") or []:
        if isinstance(r, dict) and str(r.get("id") or "").startswith("staff:"):
            staff_ids.add(str(r.get("id")).removeprefix("staff:"))
    has_clerk_posts = bool(staff_ids) or bool(ev.get("has_staff_posts"))
    # 规则闸已报的 where 族 + 关键词 → LLM 不得再复读（防「须改」旁再堆同题待核）
    det_families: set[str] = set()
    det_blobs: list[str] = []
    for d in deterministic or []:
        if not isinstance(d, dict):
            continue
        det_families.add(_where_family(str(d.get("where") or "")))
        det_blobs.append(str(d.get("msg") or ""))
    kept: list[dict[str, str]] = []
    for f in findings:
        msg = str(f.get("msg") or "")
        where = str(f.get("where") or "").strip()
        if _NOISE_RE.search(msg):
            continue
        if not where or not _KIND_RE.match(where):
            continue
        if f.get("level") == "error" and re.search(r"建议|宜|不妨|可以更好", msg):
            continue
        if _AUTH_MENU_FALSE_POS.search(msg):
            continue
        if _DUP_PAY_NOISE.search(msg):
            continue
        # staff:shop_merchant 是交付岗位，架构图使用不算假宣称
        if "architecture" in where.lower() and "staff:" in msg:
            m = re.search(r"staff:([\w-]+)", msg)
            if m and (m.group(1) in staff_ids or has_clerk_posts):
                continue
        if has_clerk_posts and _SUBADMIN_EMPTY_FALSE_POS.search(msg):
            continue
        fam = _where_family(where)
        if fam in det_families:
            # 同图种且与确定性条文撞关键词 → 丢（规则已覆盖）
            hit = False
            for blob in det_blobs:
                if not blob:
                    continue
                # 共享实质词：菜单 key / 执行者 / 评价 / 订单 / include
                for tok in ("order_reviews", "menu_key", "商家", "评价", "订单", "include", "购物车", "组合", "composition"):
                    if tok in msg and tok in blob:
                        hit = True
                        break
                if hit:
                    break
            if hit:
                continue
        kept.append(f)
    return kept


def _merge_findings(*groups: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for group in groups:
        for f in group:
            key = f"{f.get('level')}|{f.get('where')}|{f.get('msg')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(f)
    return out


def _menu_keys(schema: dict[str, Any]) -> dict[str, list[str]]:
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    out: dict[str, list[str]] = {}
    for side in ("user", "admin", "staff", "subadmin"):
        raw = menus.get(side) or []
        keys: list[str] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and item.get("key"):
                    keys.append(str(item.get("key")))
                elif isinstance(item, str) and item.strip():
                    keys.append(item.strip())
        out[side] = keys[:80]
    return out


def _summarize_er(model: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(model, dict):
        return {}
    conceptual = [
        str(x) for x in (model.get("conceptual_entities") or []) if str(x).strip()
    ][:40]
    tables = []
    for t in (model.get("tables") or [])[:40]:
        if not isinstance(t, dict) or not t.get("name"):
            continue
        tables.append(
            {
                "name": t.get("name"),
                "label": t.get("label"),
                "assoc_link": bool(t.get("assoc_link")),
                "own": [
                    str(c.get("name"))
                    for c in (t.get("own_columns") or [])
                    if isinstance(c, dict) and c.get("name")
                ][:24],
                "fk": [
                    str(c.get("name"))
                    for c in (t.get("columns") or [])
                    if isinstance(c, dict) and c.get("fk") and c.get("name")
                ][:16],
            }
        )
    gate = model.get("rubric_gate") if isinstance(model.get("rubric_gate"), dict) else {}
    return {
        "conceptual_entities": conceptual,
        "tables": tables,
        "rubric_ok": gate.get("ok"),
        "rubric_errors": [
            f.get("msg")
            for f in (gate.get("findings") or [])
            if isinstance(f, dict) and f.get("level") == "error"
        ][:12],
    }


def _summarize_sequences(model: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(model, dict):
        return {}
    diagrams = []
    for d in (model.get("diagrams") or [])[:3]:
        if not isinstance(d, dict):
            continue
        diagrams.append(
            {
                "id": d.get("id"),
                "figure_title": d.get("figure_title"),
                "menu_key": d.get("menu_key"),
                "actor_label": d.get("actor_label"),
                "participants": [
                    {"id": p.get("id"), "label": p.get("label")}
                    for p in (d.get("participants") or [])
                    if isinstance(p, dict)
                ],
                "messages": [
                    {
                        "from": m.get("from"),
                        "to": m.get("to"),
                        "text": str(m.get("text") or "")[:80],
                    }
                    for m in (d.get("messages") or [])[:20]
                    if isinstance(m, dict)
                ],
            }
        )
    gate = model.get("rubric_gate") if isinstance(model.get("rubric_gate"), dict) else {}
    return {
        "selected": model.get("selected"),
        "diagrams": diagrams,
        "rubric_ok": gate.get("ok"),
        "rubric_errors": [
            f.get("msg")
            for f in (gate.get("findings") or [])
            if isinstance(f, dict) and f.get("level") == "error"
        ][:12],
    }


def _summarize_usecase_desc(model: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(model, dict):
        return {}
    cases = []
    for c in (model.get("cases") or [])[:6]:
        if not isinstance(c, dict):
            continue
        cases.append(
            {
                "name": c.get("name"),
                "actor": c.get("actor"),
                "menu_key": c.get("menu_key"),
                "flow": [str(s)[:60] for s in (c.get("flow") or [])[:8]],
            }
        )
    gate = model.get("rubric_gate") if isinstance(model.get("rubric_gate"), dict) else {}
    return {
        "count": model.get("count"),
        "cases": cases,
        "rubric_ok": gate.get("ok"),
        "rubric_errors": [
            f.get("msg")
            for f in (gate.get("findings") or [])
            if isinstance(f, dict) and f.get("level") == "error"
        ][:12],
    }


def _summarize_classes(model: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(model, dict):
        return {}
    classes = [
        {"id": c.get("id"), "name": c.get("name")}
        for c in (model.get("classes") or [])[:40]
        if isinstance(c, dict) and c.get("id")
    ]
    assocs = [
        {
            "from": a.get("from") or a.get("source"),
            "to": a.get("to") or a.get("target"),
            "kind": a.get("kind"),
        }
        for a in (model.get("associations") or [])[:40]
        if isinstance(a, dict)
    ]
    gate = model.get("rubric_gate") if isinstance(model.get("rubric_gate"), dict) else {}
    return {
        "classes": classes,
        "associations": assocs,
        "rubric_ok": gate.get("ok"),
        "rubric_errors": [
            f.get("msg")
            for f in (gate.get("findings") or [])
            if isinstance(f, dict) and f.get("level") == "error"
        ][:12],
    }


def _summarize_usecases(model: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(model, dict):
        return {}
    actor = model.get("actor") if isinstance(model.get("actor"), dict) else {}
    level1 = []
    for u in (model.get("level1") or [])[:20]:
        if not isinstance(u, dict):
            continue
        level1.append(
            {
                "id": u.get("id"),
                "label": u.get("label"),
                "includes": [
                    {"id": k.get("id"), "label": k.get("label"), "hidden": k.get("hidden")}
                    for k in (u.get("includes") or [])[:8]
                    if isinstance(k, dict)
                ],
            }
        )
    gate = model.get("rubric_gate") if isinstance(model.get("rubric_gate"), dict) else {}
    return {
        "actor": {"id": actor.get("id"), "label": actor.get("label")},
        "level1": level1,
        "rubric_ok": gate.get("ok"),
        "rubric_errors": [
            f.get("msg")
            for f in (gate.get("findings") or [])
            if isinstance(f, dict) and f.get("level") == "error"
        ][:12],
    }


def collect_deterministic_findings(workspace: Path) -> list[dict[str, str]]:
    """跑各图 pack + rubric_gate，汇总 error/warn（不调 LLM）。"""
    from app.bake.schema.diagram_pack import (
        pack_activities,
        pack_architecture,
        pack_classes,
        pack_er,
        pack_modules,
        pack_sequences,
        pack_usecases,
    )
    from app.bake.schema.diagram_rubric import attach_rubric_gate
    from app.bake.schema.usecase_descriptions import load_usecase_description_model

    findings: list[dict[str, str]] = []

    def _take(model: dict[str, Any] | None, kind: str, **opts: Any) -> None:
        if not model:
            findings.append(
                {
                    "level": "warn",
                    "msg": f"{kind} 无 model（可能尚未生成工作区）",
                    "where": kind,
                }
            )
            return
        gated = attach_rubric_gate(dict(model), kind=kind, **opts)
        gate = gated.get("rubric_gate") if isinstance(gated.get("rubric_gate"), dict) else {}
        for f in gate.get("findings") or []:
            if isinstance(f, dict) and f.get("msg"):
                row: dict[str, str] = {
                    "level": str(f.get("level") or "warn"),
                    "msg": str(f.get("msg"))[:200],
                    "where": str(f.get("where") or kind)[:120],
                }
                if f.get("fix"):
                    row["fix"] = str(f.get("fix"))[:160]
                if f.get("goto"):
                    row["goto"] = str(f.get("goto"))[:64]
                findings.append(
                    stamp_finding_trust(enrich_finding_nav(row), source="rule")
                )

    schema: dict[str, Any] = {}
    schema_path = workspace / "domain.schema.json"
    if schema_path.is_file():
        try:
            raw = json.loads(schema_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                schema = raw
        except Exception:
            schema = {}
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}

    # 对账必须 force 重建：旧 diagram cache 会把已修好的 include/文案又当成红灯
    _take(pack_er(workspace, mode="total", force=True), "er", mode="total")
    er_part = pack_er(workspace, mode="total", force=True)
    conceptual = []
    if isinstance(er_part, dict):
        conceptual = [
            str(x) for x in (er_part.get("conceptual_entities") or []) if str(x).strip()
        ]
    if conceptual:
        _take(
            pack_er(workspace, mode="part", entity=conceptual[0], force=True),
            "er",
            mode="part",
            entity=conceptual[0],
        )
    seq = pack_sequences(workspace, force=True)
    if isinstance(seq, dict):
        seq = dict(seq)
        seq["delivery_menus"] = menus
        seq["roles"] = roles
    _take(seq, "sequences")
    _take(pack_activities(workspace, force=True), "activities")
    _take(pack_classes(workspace, force=True), "classes")
    _take(pack_usecases(workspace, actor="user", force=True), "usecases")
    _take(pack_architecture(workspace, force=True), "architecture")
    _take(pack_modules(workspace, force=True), "modules")
    ucd = load_usecase_description_model(workspace, count=4)
    if isinstance(ucd, dict):
        ucd = dict(ucd)
        ucd["delivery_menus"] = menus
        ucd["roles"] = roles
    _take(ucd, "usecase_desc")
    return findings


def build_thesis_diagram_evidence(workspace: Path) -> dict[str, Any]:
    """裁好的证据包：menus + 各图摘要（有上限）。"""
    from app.bake.schema.diagram_pack import (
        pack_architecture,
        pack_classes,
        pack_er,
        pack_sequences,
        pack_usecases,
    )
    from app.bake.schema.usecase_descriptions import load_usecase_description_model

    schema: dict[str, Any] = {}
    path = workspace / "domain.schema.json"
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                schema = raw
        except Exception:
            schema = {}

    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    role_labels = {
        k: str((v or {}).get("label") or k) if isinstance(v, dict) else str(k)
        for k, v in roles.items()
        if k != "staff_posts"
    }
    posts = roles.get("staff_posts") if isinstance(roles.get("staff_posts"), list) else []
    staff_post_ids = [
        str(p.get("id")).strip()
        for p in posts
        if isinstance(p, dict) and str(p.get("id") or "").strip()
    ]
    for p in posts:
        if isinstance(p, dict) and p.get("id") and p.get("label"):
            role_labels[f"staff:{p['id']}"] = str(p.get("label"))

    return {
        "title": str(schema.get("title") or ""),
        "domain": str(schema.get("domain") or ""),
        "menuKeys": _menu_keys(schema),
        "roleLabels": role_labels,
        "staff_post_ids": staff_post_ids,
        "has_staff_posts": bool(staff_post_ids),
        "rubric_zh": [
            "实体属性图只画自身属性、不含外键",
            "序列四槽位：角色/页面/控制器/数据库；消息端点须在参与者内",
            "用例描述默认 4 主路径；表题含「用例描述表」；步骤对交付菜单",
            "类图关系端点须在 classes；禁止包外 id",
        ],
        "er": _summarize_er(pack_er(workspace, mode="total", force=True)),
        "sequences": _summarize_sequences(pack_sequences(workspace, force=True)),
        "usecase_desc": _summarize_usecase_desc(
            load_usecase_description_model(workspace, count=4)
        ),
        "classes": _summarize_classes(pack_classes(workspace, force=True)),
        "usecases": _summarize_usecases(
            pack_usecases(workspace, actor="user", force=True)
        ),
        "architecture_roles": [
            {"id": r.get("id"), "label": r.get("label")}
            for r in (
                (pack_architecture(workspace, force=True) or {}).get("roles") or []
            )
            if isinstance(r, dict)
        ][:12],
    }


def write_thesis_diagram_audit(workspace: Path, report: dict[str, Any]) -> Path:
    islands = workspace / "islands"
    islands.mkdir(parents=True, exist_ok=True)
    path = islands / "thesis_diagram_audit.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


async def run_thesis_diagram_audit(
    db: AsyncSession,
    rt: LlmRuntime,
    *,
    project_id: str,
    workspace: Path,
) -> dict[str, Any]:
    """手动对账：确定性 + 可选 LLM；不改 model。"""
    det = collect_deterministic_findings(workspace)
    evidence = build_thesis_diagram_evidence(workspace)

    llm_skip = ""
    if not rt.configured:
        llm_skip = "未配置大模型 Key（或厂商未启用）"
    elif not await budget_ok(db, project_id, rt):
        llm_skip = "本项目或月度 Token 额度已满，跳过 LLM"
    use_llm = not llm_skip
    det = [
        stamp_finding_trust(enrich_finding_nav(f), source=str(f.get("source") or "rule"))
        for f in det
    ]
    if not use_llm:
        must, verify = partition_findings(det)
        errors = [f for f in det if f.get("level") == "error"]
        summary = (
            f"仅规则闸 · {llm_skip} · 须改 {len(must)} · 待核 {len(verify)}"
        )
        if must:
            summary = f"{summary} · 首条：{must[0]['msg']}"
        report = {
            "ok": not errors,
            "summary": summary[:800],
            "findings": det,
            "must_fix": must,
            "verify": verify,
            "must_fix_count": len(must),
            "verify_count": len(verify),
            "mode": "deterministic",
            "llm_used": False,
            "llm_skip_reason": llm_skip,
        }
        write_thesis_diagram_audit(workspace, report)
        await record_call(
            db,
            project_id=project_id,
            stage="thesis_diagram_audit",
            tokens=0,
            ok=True,
            detail=f"论文图对账：仅确定性 · {llm_skip}",
        )
        return report

    payload = {
        "evidence": evidence,
        "deterministic_findings": det[:40],
        "instruction": (
            "在确定性结果之外，穷尽补「假宣称/跟包不一致」："
            "逐条扫 usecase_desc.cases↔menuKeys、sequences、classes；"
            "每条不一致单独一条；禁止省略；不要重复 deterministic 已有条文；"
            "auth/login/register 勿报不在菜单。"
        ),
    }
    messages = [
        {"role": "system", "content": _SYS},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    res = await chat(
        rt,
        messages,
        json_mode=True,
        temperature=temperature_for("thesis_diagram_audit"),
        timeout=120.0,
    )
    append_deepseek_log(
        project_id, f"thesis_diagram_audit ok={res.ok} {format_usage_detail(res)}"
    )

    if not res.ok or not res.data:
        must, verify = partition_findings(det)
        errors = [f for f in det if f.get("level") == "error"]
        report = {
            "ok": not errors,
            "summary": (
                f"大模型对账失败，回退规则闸 · {res.error or 'no json'}"
                f" · 须改 {len(must)} · 待核 {len(verify)}"
            )[:800],
            "findings": det,
            "must_fix": must,
            "verify": verify,
            "must_fix_count": len(must),
            "verify_count": len(verify),
            "mode": "fallback_after_llm_error",
            "llm_used": False,
        }
        write_thesis_diagram_audit(workspace, report)
        await record_call(
            db,
            project_id=project_id,
            stage="thesis_diagram_audit",
            tokens=res.tokens,
            ok=False,
            detail=format_usage_detail(res, "论文图对账失败"),
        )
        return report

    llm_raw = _norm_findings(res.data.get("findings"))
    llm_kept = [
        stamp_finding_trust(enrich_finding_nav(f), source="llm")
        for f in filter_llm_thesis_findings(
            llm_raw, evidence=evidence, deterministic=det
        )
    ]
    findings = _merge_findings(det, llm_kept)
    findings = [
        stamp_finding_trust(
            enrich_finding_nav(f),
            source=str(f.get("source") or "llm"),
        )
        for f in findings
    ]
    must, verify = partition_findings(findings)
    errors = [f for f in must if f.get("level") == "error"]
    # 挡交付只看规则须改；LLM 待核不拉红 ok（避免当次模型冒充老师）
    ok = not must
    summary = str(res.data.get("summary") or "").strip()
    head = f"须改 {len(must)} · 待核 {len(verify)}"
    if summary:
        summary = f"{head} · {summary}"
    else:
        summary = (
            f"{head} · 规则闸有须改项"
            if must
            else f"{head} · 无规则红；LLM 条请人工核对"
            if verify
            else "对账通过：无须改、无待核"
        )
    report = {
        "ok": ok,
        "summary": summary[:800],
        "findings": findings[:80],
        "must_fix": must[:40],
        "verify": verify[:40],
        "must_fix_count": len(must),
        "verify_count": len(verify),
        "mode": "llm",
        "llm_used": True,
        "llm_dropped": max(0, len(llm_raw) - len(llm_kept)),
        "finding_count": len(findings),
        "error_count": len(errors),
    }
    write_thesis_diagram_audit(workspace, report)
    await record_call(
        db,
        project_id=project_id,
        stage="thesis_diagram_audit",
        tokens=res.tokens,
        ok=True,
        detail=format_usage_detail(res, summary[:400]),
    )
    return report


__all__ = [
    "build_thesis_diagram_evidence",
    "collect_deterministic_findings",
    "enrich_finding_nav",
    "filter_llm_thesis_findings",
    "partition_findings",
    "run_thesis_diagram_audit",
    "stamp_finding_trust",
    "write_thesis_diagram_audit",
]
