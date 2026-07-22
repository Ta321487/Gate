"""论文软件测试用例表：从交付 schema 推导（与模块图同口径）。

真相来源：domain.schema.json 的 menus / roles / entities / labels。
用例清单由菜单确定性生成；可选 LLM 只润色已有行的文案列（前置/步骤/输入/预期）。
禁止发明菜单外功能。模板 5～9 列由工厂预览选择（默认 6）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.bake.schema_modules import (
    _SKIP_MENU_KEYS,
    _archive_biz_label,
    _biz_id_for_item,
    _menu_label,
    looks_latin,
)

TESTCASE_FIELD_OPTIONS = (5, 6, 7, 8, 9)
DEFAULT_TESTCASE_FIELDS = 6
_TESTCASE_PATCH_REL = Path("islands") / "testcase_labels.json"
_PROSE_KEYS = ("precondition", "steps", "input", "expected")
_PROSE_MAX = {"precondition": 80, "steps": 200, "input": 120, "expected": 120}

_TEMPLATE_HEADERS: dict[int, list[tuple[str, str]]] = {
    5: [
        ("id", "编号"),
        ("item", "测试功能"),
        ("steps", "操作步骤"),
        ("expected", "预期结果"),
        ("actual", "测试结果"),
    ],
    6: [
        ("id", "编号"),
        ("item", "测试项"),
        ("steps", "操作步骤"),
        ("input", "输入数据"),
        ("expected", "预期结果"),
        ("actual", "实际结果"),
    ],
    7: [
        ("id", "编号"),
        ("item", "测试项"),
        ("steps", "操作步骤"),
        ("input", "输入数据"),
        ("expected", "预期结果"),
        ("actual", "实际结果"),
        ("verdict", "结论"),
    ],
    8: [
        ("id", "编号"),
        ("item", "测试项"),
        ("precondition", "前置条件"),
        ("steps", "操作步骤"),
        ("input", "输入数据"),
        ("expected", "预期结果"),
        ("actual", "实际结果"),
        ("verdict", "结论"),
    ],
    9: [
        ("id", "编号"),
        ("module", "测试模块"),
        ("item", "测试项"),
        ("precondition", "前置条件"),
        ("steps", "操作步骤"),
        ("input", "输入数据"),
        ("expected", "预期结果"),
        ("actual", "实际结果"),
        ("verdict", "结论"),
    ],
}

_PREFIX_ALIAS = {
    "profile": "PROFILE",
    "messages": "MSG",
    "archive": "ARCHIVE",
    "category": "CATE",
    "users": "USERS",
    "content": "NOTICE",
    "my_tickets": "TICKET",
    "ticket_pending": "PENDING",
    "ticket_records": "TREC",
    "cart": "CART",
    "my_orders": "MYORD",
    "orders": "ORDERS",
    "addresses": "ADDR",
    "my_reservations": "MYRSV",
    "reservations": "RSV",
    "slots": "SLOT",
    "guestbook": "GUEST",
    "favorites": "FAV",
    "browse_history": "HIST",
    "coupons": "COUPON",
    "order_reviews": "REVIEW",
    "week_calendar": "CAL",
    "deadline": "DDL",
}

# 家族模板：只描述壳能力，文案占位用菜单/角色/实体标签填充（不发明功能）
# 字段：item, steps(list), expected, input?, pre?（默认 {pre}）
Blueprint = list[dict[str, Any]]

_BLUEPRINTS: dict[str, Blueprint] = {
    "profile": [
        {
            "item": "查看与保存个人资料",
            "steps": ["进入「{label}」", "查看资料字段", "修改允许编辑项并保存"],
            "input": "修改昵称或联系方式等表单字段",
            "expected": "保存成功，页面展示更新后的资料",
        }
    ],
    "messages": [
        {
            "item": "查看站内消息",
            "steps": ["进入「{label}」", "查看消息列表"],
            "expected": "能看到消息列表或空状态提示",
        }
    ],
    "archive_user": [
        {
            "item": "浏览{entity}列表",
            "steps": ["进入「{label}」", "查看列表或检索"],
            "expected": "展示{entity}列表，可进入详情",
        },
        {
            "item": "查看{entity}详情",
            "steps": ["进入「{label}」", "打开一条记录详情"],
            "expected": "详情页展示该记录字段信息",
        },
    ],
    "archive_admin": [
        {
            "item": "新增{entity}",
            "steps": ["进入「{label}」", "点击新增", "填写必填项", "保存"],
            "input": "按{entity}表单填写有效数据",
            "expected": "保存成功，列表中出现新记录",
        },
        {
            "item": "编辑{entity}",
            "pre": "{pre}，且已有{entity}记录",
            "steps": ["进入「{label}」", "打开编辑", "修改字段", "保存"],
            "input": "修改标题或说明等字段",
            "expected": "保存成功，列表/详情显示新值",
        },
    ],
    "category": [
        {
            "item": "维护{label}",
            "steps": ["进入「{label}」", "新增或编辑分类", "保存"],
            "input": "分类名称等必填项",
            "expected": "分类保存成功并出现在列表中",
        }
    ],
    "users": [
        {
            "item": "查看用户列表",
            "steps": ["进入「{label}」", "查看用户列表"],
            "expected": "展示用户列表，可进行启用/停用等管理操作",
        },
        {
            "item": "重置用户密码",
            "pre": "{pre}，列表中存在目标用户",
            "steps": ["进入「{label}」", "选择用户", "执行重置密码"],
            "expected": "提示重置成功，可用新密码登录（以系统实现为准）",
        },
    ],
    "content_user": [
        {
            "item": "查看公告列表",
            "steps": ["进入「{label}」", "打开一条公告"],
            "expected": "可阅读公告标题与正文",
        }
    ],
    "content_admin": [
        {
            "item": "发布公告",
            "steps": ["进入「{label}」", "新建公告", "填写标题正文", "发布/保存"],
            "input": "标题与正文必填",
            "expected": "公告保存成功，用户端可查看",
        }
    ],
    "my_tickets": [
        {
            "item": "提交{ticket_stem}申请",
            "steps": ["进入「{label}」", "填写申请表单", "提交"],
            "input": "按表单必填项填写",
            "expected": "提交成功，列表出现新单据",
        },
        {
            "item": "查看{label}",
            "steps": ["进入「{label}」", "查看单据列表与状态"],
            "expected": "能查看本人单据及状态",
        },
    ],
    "ticket_pending": [
        {
            "item": "办理「{label}」通过",
            "pre": "{pre}，存在待办单据",
            "steps": ["进入「{label}」", "打开待办", "执行通过/同意"],
            "expected": "单据状态更新为已通过或下一状态",
        },
        {
            "item": "办理「{label}」驳回",
            "pre": "{pre}，存在待办单据",
            "steps": ["进入「{label}」", "打开待办", "执行驳回"],
            "expected": "单据状态更新为已驳回",
        },
    ],
    "ticket_records": [
        {
            "item": "查询{label}",
            "steps": ["进入「{label}」", "按条件查看记录"],
            "expected": "展示办理记录列表",
        }
    ],
    "cart": [
        {
            "item": "加入购物车并查看",
            "steps": ["在商品页加入购物车", "进入「{label}」", "核对数量"],
            "expected": "购物车展示已选商品与数量",
        }
    ],
    "my_orders": [
        {
            "item": "查看{label}",
            "steps": ["进入「{label}」", "查看订单状态"],
            "expected": "展示本人订单列表与状态",
        }
    ],
    "orders": [
        {
            "item": "处理{label}",
            "pre": "{pre}，存在待处理订单",
            "steps": ["进入「{label}」", "打开订单", "执行确认/发货等办理操作"],
            "expected": "订单状态按办理结果更新",
        }
    ],
    "addresses": [
        {
            "item": "维护收货地址",
            "steps": ["进入「{label}」", "新增或编辑地址", "保存"],
            "input": "收货人、电话、地址等必填项",
            "expected": "地址保存成功并出现在列表中",
        }
    ],
    "reserve_user": [
        {
            "item": "完成「{label}」主流程",
            "steps": ["进入「{label}」", "选择可预约项/时段", "提交预约"],
            "input": "按页面必填项选择",
            "expected": "预约成功，可在我的预约中查看",
        }
    ],
    "reservations": [
        {
            "item": "管理端查看{label}",
            "steps": ["进入「{label}」", "查看预约记录", "必要时办结或处理"],
            "expected": "展示预约记录，办理操作生效",
        }
    ],
    "guestbook_user": [
        {
            "item": "提交留言",
            "steps": ["进入「{label}」", "填写留言", "提交"],
            "input": "留言正文",
            "expected": "提交成功，可在列表中看到留言",
        }
    ],
    "guestbook_admin": [
        {
            "item": "回复或管理留言",
            "pre": "{pre}，存在留言",
            "steps": ["进入「{label}」", "打开留言", "回复或删除"],
            "expected": "留言状态更新，用户端可见回复（如有）",
        }
    ],
    "favorites": [
        {
            "item": "收藏与取消收藏",
            "steps": ["在详情页点击收藏", "进入「{label}」查看", "取消收藏"],
            "expected": "收藏列表增删与操作一致",
        }
    ],
    "browse_history": [
        {
            "item": "查看浏览足迹",
            "pre": "{pre}，且已浏览过业务对象",
            "steps": ["进入「{label}」", "查看足迹列表"],
            "expected": "展示最近浏览记录",
        }
    ],
    "coupons": [
        {
            "item": "使用「{label}」",
            "steps": ["进入「{label}」", "领取或查看优惠券"],
            "expected": "券列表展示正确，可按实现用于下单",
        }
    ],
    "order_reviews": [
        {
            "item": "完成「{label}」",
            "pre": "{pre}，存在可评价完成单",
            "steps": ["进入「{label}」或订单详情", "提交评分与评价"],
            "input": "星级与文字评价",
            "expected": "评价提交成功",
        }
    ],
    "week_calendar": [
        {
            "item": "查看「{label}」",
            "steps": ["进入「{label}」", "切换日期查看安排"],
            "expected": "周历展示本人相关安排",
        }
    ],
    "deadline": [
        {
            "item": "查看「{label}」",
            "steps": ["进入「{label}」", "查看逾期或催办列表"],
            "expected": "展示逾期/催办相关记录",
        }
    ],
    "lookup": [
        {
            "item": "维护「{label}」",
            "steps": ["进入「{label}」", "新增或编辑字典项", "保存"],
            "input": "字典项名称等必填项",
            "expected": "字典项保存成功",
        }
    ],
    # 未知已交付菜单：仅冒烟，不发明业务规则
    "open": [
        {
            "item": "打开「{label}」页面",
            "steps": ["进入「{label}」", "查看页面主列表或主表单"],
            "expected": "「{label}」页面正常打开并可操作",
        }
    ],
}


def normalize_testcase_fields(fields: int | str | None) -> int:
    try:
        n = int(fields)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return DEFAULT_TESTCASE_FIELDS
    return n if n in TESTCASE_FIELD_OPTIONS else DEFAULT_TESTCASE_FIELDS


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def testcase_labels_path(workspace: Path) -> Path:
    return workspace / _TESTCASE_PATCH_REL


def load_testcase_label_patch(workspace: Path) -> dict[str, Any]:
    return _read_json(testcase_labels_path(workspace))


def save_testcase_label_patch(workspace: Path, patch: dict[str, Any]) -> None:
    path = testcase_labels_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(patch, ensure_ascii=False, indent=2), encoding="utf-8")


def _role_label(schema: dict[str, Any], side: str) -> str:
    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    role = roles.get(side) if isinstance(roles.get(side), dict) else {}
    lab = str(role.get("label") or "").strip()
    if lab and not looks_latin(lab):
        return lab
    return "用户" if side == "user" else "管理员"


def _app_title(schema: dict[str, Any], fallback: str = "管理系统") -> str:
    labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
    return (
        str(labels.get("appName") or "").strip()
        or str(schema.get("title") or "").strip()
        or fallback
    )


def _entity_label(schema: dict[str, Any]) -> str:
    lab = _archive_biz_label(schema)
    return lab[:-2] if lab.endswith("模块") else lab


def _circ(n: int) -> str:
    if 1 <= n <= 20:
        return chr(0x2460 + n - 1)
    return f"{n}."


def _fmt_steps(parts: list[str]) -> str:
    return " ".join(f"{_circ(i)}{p}" for i, p in enumerate(parts, 1))


def _fmt(tpl: str, ctx: dict[str, str]) -> str:
    out = tpl or ""
    for k, v in ctx.items():
        out = out.replace("{" + k + "}", v)
    return out


def _module_name(key: str, label: str, schema: dict[str, Any]) -> str:
    biz = _biz_id_for_item(key, label)
    mapping = {
        "user": "用户模块",
        "admin": "管理员模块",
        "favorite": "收藏模块",
        "cart": "购物车模块",
        "order": "订单模块",
        "content": "公告模块",
        "guestbook": "留言模块",
    }
    if biz in mapping:
        return mapping[biz]
    if biz == "archive":
        return _archive_biz_label(schema)
    if biz in ("ticket", "slot"):
        stem = label.replace("我的", "").replace("管理", "").replace("审核", "").replace("记录", "").strip()
        fallback = "业务办理模块" if biz == "ticket" else "预约模块"
        return f"{stem}模块" if stem else fallback
    return label if label.endswith("模块") else f"{label}模块"


def _prefix_for(key: str, label: str) -> str:
    if "收藏" in (label or ""):
        return "FAV"
    if key in _PREFIX_ALIAS:
        return _PREFIX_ALIAS[key]
    if key.startswith("lookup_"):
        return "LOOKUP"
    raw = re.sub(r"[^A-Za-z0-9]+", "", key.upper()) or "FN"
    return raw[:10]


def _kind(key: str, side: str) -> str:
    if key == "archive":
        return f"archive_{side}"
    if key == "content":
        return f"content_{side}"
    if key == "guestbook":
        return f"guestbook_{side}"
    if key in ("my_reservations", "slots"):
        return "reserve_user"
    if key.startswith("lookup_"):
        return "lookup"
    if key in _BLUEPRINTS:
        return key
    return "open"


def _auth_cases(schema: dict[str, Any]) -> list[dict[str, Any]]:
    user = _role_label(schema, "user")
    admin = _role_label(schema, "admin")
    mod = "登录模块"
    return [
        {
            "id": "TC-LOGIN-001",
            "module": mod,
            "item": "正确用户名密码登录",
            "precondition": f"系统运行正常，已存在{admin}或{user}账号",
            "steps": _fmt_steps(["打开登录页", "输入用户名", "输入密码", "点击登录"]),
            "input": "username=admin, password=admin123",
            "expected": "登录成功，进入系统首页或工作台",
            "actual": "与预期一致",
            "verdict": "通过",
            "key": "auth",
            "side": "user",
        },
        {
            "id": "TC-LOGIN-002",
            "module": mod,
            "item": "错误密码登录",
            "precondition": "系统运行正常，已存在账号",
            "steps": _fmt_steps(["打开登录页", "输入用户名", "输入错误密码", "点击登录"]),
            "input": "username=admin, password=000000",
            "expected": "提示用户名或密码错误，停留在登录页",
            "actual": "与预期一致",
            "verdict": "通过",
            "key": "auth",
            "side": "user",
        },
        {
            "id": "TC-LOGIN-003",
            "module": mod,
            "item": "用户名为空登录",
            "precondition": "系统运行正常",
            "steps": _fmt_steps(["打开登录页", "不输入用户名", "输入密码", "点击登录"]),
            "input": "username=空, password=admin123",
            "expected": "提示请输入用户名或校验失败，无法登录",
            "actual": "与预期一致",
            "verdict": "通过",
            "key": "auth",
            "side": "user",
        },
        {
            "id": "TC-REG-001",
            "module": mod,
            "item": f"{user}注册",
            "precondition": "系统运行正常，注册入口可用",
            "steps": _fmt_steps(["打开注册页", "填写必填信息", "提交注册"]),
            "input": "按注册表单填写有效信息",
            "expected": "注册成功，可使用新账号登录",
            "actual": "与预期一致",
            "verdict": "通过",
            "key": "auth",
            "side": "user",
        },
    ]


def _expand_blueprint(
    kind: str,
    *,
    key: str,
    label: str,
    side: str,
    schema: dict[str, Any],
    seq_start: int,
) -> list[dict[str, Any]]:
    bp = _BLUEPRINTS.get(kind) or _BLUEPRINTS["open"]
    module = _module_name(key, label, schema)
    prefix = _prefix_for(key, label)
    user = _role_label(schema, "user")
    admin = _role_label(schema, "admin")
    actor = user if side == "user" else admin
    pre = f"已使用{actor}账号登录"
    ticket_stem = label.replace("我的", "").strip() or label
    ctx = {
        "label": label,
        "entity": _entity_label(schema),
        "user": user,
        "admin": admin,
        "actor": actor,
        "pre": pre,
        "ticket_stem": ticket_stem,
    }
    out: list[dict[str, Any]] = []
    for i, row in enumerate(bp):
        steps_raw = row.get("steps") or []
        steps = [_fmt(str(s), ctx) for s in steps_raw]
        out.append(
            {
                "id": f"TC-{prefix}-{seq_start + i:03d}",
                "module": module,
                "item": _fmt(str(row.get("item") or ""), ctx),
                "precondition": _fmt(str(row.get("pre") or "{pre}"), ctx),
                "steps": _fmt_steps(steps),
                "input": _fmt(str(row.get("input") or "—"), ctx),
                "expected": _fmt(str(row.get("expected") or ""), ctx),
                "actual": "与预期一致",
                "verdict": "通过",
                "key": key,
                "side": side,
            }
        )
    return out


def build_testcase_rows(schema: dict[str, Any]) -> list[dict[str, Any]]:
    menus = schema.get("menus") if isinstance(schema.get("menus"), dict) else {}
    caps = {str(c) for c in (schema.get("capabilities") or [])}
    has_user = bool(menus.get("user")) or "org_users" in caps

    rows: list[dict[str, Any]] = []
    if has_user:
        rows.extend(_auth_cases(schema))

    seen: set[tuple[str, str]] = set()
    for side in ("user", "admin"):
        for raw in menus.get(side) or []:
            if not isinstance(raw, dict):
                continue
            key = str(raw.get("key") or "").strip()
            if not key or key in _SKIP_MENU_KEYS:
                continue
            label = _menu_label(raw)
            pair = (side, key)
            if pair in seen:
                continue
            seen.add(pair)
            prefix = _prefix_for(key, label)
            start = 1 + sum(1 for r in rows if str(r.get("id") or "").startswith(f"TC-{prefix}-"))
            rows.extend(
                _expand_blueprint(
                    _kind(key, side),
                    key=key,
                    label=label,
                    side=side,
                    schema=schema,
                    seq_start=start,
                )
            )
    return rows


def sanitize_testcase_label_patch(
    data: dict | None,
    allowed_ids: set[str] | None = None,
) -> dict[str, Any]:
    """只保留已有用例 id 的文案列；禁止增删用例、禁止改编号/模块/测试项。"""
    data = data or {}
    raw = data.get("cases")
    if not isinstance(raw, dict):
        raw = {}
    cases_out: dict[str, dict[str, str]] = {}
    for cid, body in raw.items():
        cid_s = str(cid or "").strip()
        if not cid_s or (allowed_ids is not None and cid_s not in allowed_ids):
            continue
        if not isinstance(body, dict):
            continue
        prose: dict[str, str] = {}
        for k in _PROSE_KEYS:
            if k not in body:
                continue
            val = str(body.get(k) or "").strip().replace("\n", " ")
            val = re.sub(r"\s+", " ", val)
            if not val or looks_latin(val) and k != "input":
                # input 允许 username=admin 这类
                if k != "input":
                    continue
            if k == "input" and not val:
                continue
            prose[k] = val[: _PROSE_MAX[k]]
        if prose:
            cases_out[cid_s] = prose
    return {"cases": cases_out}


def apply_testcase_label_patch(
    rows: list[dict[str, Any]],
    patch: dict | None,
) -> list[dict[str, Any]]:
    clean = sanitize_testcase_label_patch(
        patch, {str(r.get("id") or "") for r in rows if r.get("id")}
    )
    nmap = clean.get("cases") or {}
    if not nmap:
        return rows
    out: list[dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        cid = str(row.get("id") or "")
        prose = nmap.get(cid)
        if isinstance(prose, dict):
            for k in _PROSE_KEYS:
                if k in prose and prose[k]:
                    row[k] = prose[k]
        out.append(row)
    return out


def project_rows(rows: list[dict[str, Any]], fields: int) -> list[dict[str, str]]:
    fields_n = normalize_testcase_fields(fields)
    headers = _TEMPLATE_HEADERS[fields_n]
    out: list[dict[str, str]] = []
    for r in rows:
        line: dict[str, str] = {}
        for key, _title in headers:
            if fields_n == 5 and key == "actual":
                line[key] = str(r.get("verdict") or "通过")
            else:
                line[key] = str(r.get(key) or "")
        out.append(line)
    return out


def render_testcase_markdown(
    *,
    title: str,
    fields: int,
    rows: list[dict[str, str]],
) -> str:
    fields_n = normalize_testcase_fields(fields)
    headers = _TEMPLATE_HEADERS[fields_n]
    titles = [h[1] for h in headers]
    keys = [h[0] for h in headers]
    lines = [
        f"## {title} — 软件测试用例（{fields_n}字段）",
        "",
        "| " + " | ".join(titles) + " |",
        "| " + " | ".join(["---"] * len(titles)) + " |",
    ]
    for r in rows:
        cells = [str(r.get(k) or "").replace("|", "\\|").replace("\n", "<br>") for k in keys]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def testcase_model(
    schema: dict[str, Any] | None,
    *,
    fields: int = DEFAULT_TESTCASE_FIELDS,
    title_fallback: str = "管理系统",
    label_patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    schema = schema if isinstance(schema, dict) else {}
    fields_n = normalize_testcase_fields(fields)
    title = _app_title(schema, title_fallback)
    raw_rows = build_testcase_rows(schema)
    if label_patch:
        raw_rows = apply_testcase_label_patch(raw_rows, label_patch)
    projected = project_rows(raw_rows, fields_n)
    headers = [{"key": k, "title": t} for k, t in _TEMPLATE_HEADERS[fields_n]]
    return {
        "title": title,
        "fields": fields_n,
        "columns": headers,
        "rows": projected,
        "count": len(projected),
        "markdown": render_testcase_markdown(title=title, fields=fields_n, rows=projected),
        "templates": [
            {"fields": n, "columns": [t for _, t in _TEMPLATE_HEADERS[n]]}
            for n in TESTCASE_FIELD_OPTIONS
        ],
        # 供 Agent 使用的骨架（含 id，未投影）
        "skeleton": [
            {
                "id": r.get("id"),
                "module": r.get("module"),
                "item": r.get("item"),
                "key": r.get("key"),
                "side": r.get("side"),
                "precondition": r.get("precondition"),
                "steps": r.get("steps"),
                "input": r.get("input"),
                "expected": r.get("expected"),
            }
            for r in raw_rows
        ],
    }


def load_testcase_model(
    workspace: Path,
    *,
    fields: int = DEFAULT_TESTCASE_FIELDS,
    with_label_patch: bool = True,
) -> dict[str, Any] | None:
    schema = _read_json(workspace / "domain.schema.json")
    if not schema:
        return None
    spec = _read_json(workspace / "spec.json")
    title_fb = str(spec.get("title") or "管理系统")
    patch = load_testcase_label_patch(workspace) if with_label_patch else None
    return testcase_model(
        schema,
        fields=fields,
        title_fallback=title_fb,
        label_patch=patch,
    )


def build_testcase_skeleton(workspace: Path) -> dict[str, Any] | None:
    """无补丁骨架，供 Agent 约束目标 id。"""
    return load_testcase_model(workspace, fields=6, with_label_patch=False)
