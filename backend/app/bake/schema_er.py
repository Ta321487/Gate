"""从 schema.sql 解析表结构，推断联系，输出陈氏 E-R 线框图 SVG。

文案除基数（1 / n）外一律中文；实体按环排列并最小化连线交叉。
联系为直线；SVG 带 er-node / er-edges 分组，供前端拖拽编辑。
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
FK_INLINE_RE = re.compile(
    r"FOREIGN\s+KEY\s*\(`?(\w+)`?\)\s*REFERENCES\s*`?(\w+)`?\s*\(`?(\w+)`?\)",
    re.IGNORECASE,
)
COL_RE = re.compile(
    r"^`?(\w+)`?\s+(\w+(?:\([^)]*\))?)",
    re.IGNORECASE,
)

# —— 中文：领域名从表 domain.schema.json 取；这里只兜底骨架表 + 公共列词根 ——

# 各域 schema.sql 都会有、但不进 entities 的表（完整表名优先于拆段组词）
_INFRA_TABLE_ZH: dict[str, str] = {
    "sys_user": "用户",
    "sys_notice": "公告",
    "sys_message": "消息",
    "sys_config": "配置",
    "category": "分类",
    "user_ledger": "账户流水",
    "reservation": "预约",
    "orders": "订单",
    "resource_slot": "时段名额",
}

# 表名拆段组词（biz_order → 业务+订单）；完整表名见 _INFRA_TABLE_ZH
_TABLE_PART_ZH: dict[str, str] = {
    "user": "用户",
    "sys": "系统",
    "ledger": "账本",
    "order": "订单",
    "biz": "业务",
    "shop": "店铺",
    "food": "餐饮",
    "hotel": "客房",
    "reservation": "预约",
    "ticket": "单据",
    "progress": "进度",
    "attach": "附件",
    "log": "日志",
    "lookup": "字典",
    "favorite": "收藏",
    "slot": "时段",
    "resource": "资源",
}

# 原子列名（可由后缀规则推出的不要再写一遍，见 _col_zh）
_COMMON_COL_ZH: dict[str, str] = {
    "id": "编号",
    "username": "用户名",
    "password": "密码",
    "role": "角色",
    "nickname": "昵称",
    "phone": "手机",
    "enabled": "启用",
    "status": "状态",
    "name": "名称",
    "title": "标题",
    "content": "内容",
    "body": "正文",
    "remark": "说明",
    "qty": "数量",
    "stock": "库存",
    "action": "动作",
    "operator": "操作人",
    "code": "编码",
    "location": "地点",
    "capacity": "容量",
    "price": "价格",
    "rating": "评分",
    "booked": "已约",
    "cfg_key": "配置键",
    "cfg_value": "配置值",
    "super_admin": "总管",
    "profile_editable": "可改资料",
    "profile_json": "资料",
    "kind": "类型",
    "delta": "变动额",
    "reason": "事由",
    "points": "积分",
    "member_tier": "会员等级",
    "points_earned": "获积分",
}

# 去掉后缀后的词根（*_at / *_url / *_yuan / *_msg / *_code / *_after …）
_STEM_ZH: dict[str, str] = {
    "created": "创建",
    "updated": "更新",
    "deleted": "删除",
    "apply": "申请",
    "approve": "受理",
    "due": "到期",
    "return": "完结",
    "reminded": "催办",
    "remind": "催办",
    "rated": "评价",
    "rating": "评价",
    "checked_in": "签到",
    "start": "开始",
    "end": "结束",
    "read": "已读",
    "period_start": "开始",
    "period_end": "结束",
    "apply_deadline": "报名截止",
    "avatar": "头像",
    "attach": "附件",
    "profile": "资料",
    "fine": "费用",
    "price": "价格",
    "line": "小计",
    "checkin": "签到",
    "mutex": "互斥",
    "publisher": "发布人",
    "assignee": "处理人",
    "ref": "关联",
    "parent": "上级",
    "balance": "余额",
    "spend_total": "累计消费",
    "discount": "优惠",
    "pay_balance": "余额支付",
    "member": "会员",
    "ship": "物流",
    "pickup": "取餐",
    "flavor": "口味",
    "address": "地址",
}

_LATIN_RE = re.compile(r"[A-Za-z]")
_ER_LABELS_REL = Path("islands") / "er_labels.json"

# (suffix, 默认中文, 有词根时的格式；{stem} 占位)
_COL_SUFFIX_RULES: tuple[tuple[str, str, str], ...] = (
    ("_username", "用户账号", "{stem}账号"),
    ("_name", "名称", "{stem}"),
    ("_at", "时间", "{stem}时间"),
    ("_url", "链接", "{stem}链接"),
    ("_yuan", "金额", "{stem}"),
    ("_msg", "说明", "{stem}说明"),
    ("_code", "编码", "{stem}码"),
    ("_json", "资料", "{stem}"),
    ("_type", "类型", "{stem}类型"),
    ("_after", "变动后", "变动后{stem}"),
    ("_note", "备注", "{stem}备注"),
    ("_method", "方式", "{stem}方式"),
    ("_status", "状态", "{stem}状态"),
    ("_no", "单号", "{stem}单号"),
)


@dataclass
class Column:
    name: str
    type: str
    pk: bool = False
    fk: bool = False
    fk_table: str | None = None
    not_null: bool = False


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)


@dataclass
class Relation:
    name: str
    left: str
    right: str
    card_left: str  # "1" | "n"
    card_right: str
    via: str


def parse_schema_sql(
    sql: str,
    fk_aliases: dict[str, str] | None = None,
) -> list[Table]:
    tables: list[Table] = []
    for m in CREATE_RE.finditer(sql or ""):
        tname = m.group(1)
        body = m.group(2)
        cols: list[Column] = []
        pk_names: set[str] = set()
        fk_map: dict[str, str] = {}

        for raw in body.split("\n"):
            line = raw.strip().rstrip(",")
            if not line or line.startswith("--"):
                continue
            upper = line.upper()
            if upper.startswith("PRIMARY KEY"):
                for c in re.findall(r"`?(\w+)`?", line):
                    if c.upper() != "PRIMARY" and c.upper() != "KEY":
                        pk_names.add(c)
                continue
            fk = FK_INLINE_RE.search(line)
            if fk:
                fk_map[fk.group(1)] = fk.group(2)
                continue
            if upper.startswith("UNIQUE") or upper.startswith("KEY") or upper.startswith("INDEX") or upper.startswith("CONSTRAINT"):
                continue
            cm = COL_RE.match(line)
            if not cm:
                continue
            cname, ctype = cm.group(1), cm.group(2)
            is_pk = "PRIMARY KEY" in upper
            if is_pk:
                pk_names.add(cname)
            cols.append(
                Column(
                    name=cname,
                    type=ctype,
                    pk=is_pk,
                    not_null="NOT NULL" in upper,
                )
            )

        for c in cols:
            if c.name in pk_names:
                c.pk = True
            if c.name in fk_map:
                c.fk = True
                c.fk_table = fk_map[c.name]

        tables.append(Table(name=tname, columns=cols))

    _infer_fk_by_name(tables, fk_aliases)
    return tables


def _infer_fk_by_name(
    tables: list[Table],
    fk_aliases: dict[str, str] | None = None,
) -> None:
    """按列名推断外键；fk_aliases 把 book/item 等别名映射到领域档案表。"""
    names = {t.name for t in tables}
    aliases = {k: v for k, v in (fk_aliases or {}).items() if v}
    archive = aliases.get("archive") or aliases.get("book") or aliases.get("item") or ""
    for t in tables:
        for c in t.columns:
            if c.fk or c.pk:
                continue
            if c.name.endswith("_id") and len(c.name) > 3:
                base = c.name[:-3]
                candidates: list[str] = []
                if base in aliases:
                    candidates.append(aliases[base])
                if c.name in ("book_id", "item_id") and archive:
                    candidates.append(archive)
                if c.name == "slot_id" and "resource_slot" in names:
                    candidates.append("resource_slot")
                # 单据进度 / 上传附件：ticket_id → 父单据表
                if c.name == "ticket_id" and len(t.name) > 8:
                    if t.name.endswith("_progress"):
                        candidates.append(t.name[: -len("_progress")])
                    elif t.name.endswith("_attach"):
                        candidates.append(t.name[: -len("_attach")])
                candidates.extend([base, f"sys_{base}", f"{base}s"])
                seen_cand: set[str] = set()
                for cand in candidates:
                    if not cand or cand in seen_cand:
                        continue
                    seen_cand.add(cand)
                    if cand in names and cand != t.name:
                        c.fk = True
                        c.fk_table = cand
                        break
            elif c.name == "username" and "sys_user" in names and t.name != "sys_user":
                c.fk = True
                c.fk_table = "sys_user"
            elif (
                c.name.endswith("_username")
                and len(c.name) > 9
                and "sys_user" in names
                and t.name != "sys_user"
            ):
                # publisher_username / assignee_username → 用户
                c.fk = True
                c.fk_table = "sys_user"
            elif c.name in ("uploaded_by", "uploader", "operator") and "sys_user" in names and t.name != "sys_user":
                # 上传人 / 流水登记人
                c.fk = True
                c.fk_table = "sys_user"


def _short_name(table: str) -> str:
    return table.replace("sys_", "")


def _rel_label(parent: str, child: str, via: str, by_name: dict[str, Table]) -> str:
    """联系内部名：必须唯一（含 via），避免多条联系都叫 user 被补丁盖成「用户」。"""
    _ = parent
    _ = by_name
    if child.endswith("_progress"):
        return f"{child}:progress"
    if child.endswith("_attach"):
        return f"{child}:attach"
    if via:
        return f"{child}:{via}"
    return child


def infer_relations(tables: list[Table]) -> list[Relation]:
    by_name = {t.name: t for t in tables}
    rels: list[Relation] = []
    seen: set[tuple[str, str, str]] = set()
    for t in tables:
        for c in t.columns:
            if not c.fk or not c.fk_table:
                continue
            parent, child = c.fk_table, t.name
            key = (parent, child, c.name)
            if key in seen:
                continue
            seen.add(key)
            rels.append(
                Relation(
                    name=_rel_label(parent, child, c.name, by_name),
                    left=parent,
                    right=child,
                    card_left="1",
                    card_right="n",
                    via=c.name,
                )
            )
    return rels


def pick_core_attrs(cols: list[Column], limit: int = 5) -> list[Column]:
    if len(cols) <= 8:
        return cols
    picked: list[Column] = []
    used: set[str] = set()

    def add(c: Column) -> None:
        if c.name in used or len(picked) >= limit:
            return
        used.add(c.name)
        picked.append(c)

    for c in cols:
        if c.pk:
            add(c)
    for c in cols:
        if c.fk:
            add(c)

    prefer = (
        "name", "title", "username", "status", "role", "nickname",
        "isbn", "author", "stock", "content", "phone",
    )
    by_name = {c.name: c for c in cols}
    for n in prefer:
        if n in by_name:
            add(by_name[n])

    for c in cols:
        if c.not_null and not c.name.endswith("_at"):
            add(c)

    for c in cols:
        add(c)

    return picked


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _put_col(cols: dict[str, str], key: str, label: str) -> None:
    key = (key or "").strip()
    label = (label or "").strip()
    if not key or not label:
        return
    cols[key] = label
    snake = _camel_to_snake(key)
    if snake != key:
        cols[snake] = label


def _read_json_dict(path: Path | None) -> dict:
    if not path or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def _labels_from_domain_schema(
    path: Path,
) -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, str]], dict[str, str], dict[str, str]]:
    """从 domain.schema.json 抽：表名、公共列、按表列、联系名、FK 别名。

    联系名优先读 JSON 里的角色语义（verbs / roles），不要把连到用户的边都标成「用户」：
    - ticket.verbs.apply → 主单 username
    - ticket.verbs.approve → assignee_username（办理方角色动作）
    """
    tables: dict[str, str] = {}
    cols: dict[str, str] = {}
    by_table: dict[str, dict[str, str]] = {}
    rels: dict[str, str] = {}
    fk_aliases: dict[str, str] = {}
    data = _read_json_dict(path)
    if not data:
        return tables, cols, by_table, rels, fk_aliases

    labels = data.get("labels") if isinstance(data.get("labels"), dict) else {}
    notice = str(labels.get("noticePageTitle") or "").strip()
    if notice:
        tables["sys_notice"] = notice

    menus = data.get("menus") if isinstance(data.get("menus"), dict) else {}
    for role_menus in menus.values():
        if not isinstance(role_menus, list):
            continue
        for item in role_menus:
            if not isinstance(item, dict):
                continue
            if item.get("key") == "category" and item.get("label"):
                lab = str(item["label"]).removesuffix("管理").strip() or str(item["label"])
                tables.setdefault("category", lab)

    for pf in data.get("profileFields") or []:
        if isinstance(pf, dict):
            _put_col(cols, str(pf.get("key") or ""), str(pf.get("label") or ""))

    # roles.*.label 区分门户角色；联系菱形用动词，避免再写实体名「用户」
    roles = data.get("roles") if isinstance(data.get("roles"), dict) else {}
    staff_lab = ""
    for rk in ("subadmin", "admin"):
        raw = roles.get(rk)
        if isinstance(raw, dict):
            staff_lab = _short_role_label(str(raw.get("label") or ""))
            if staff_lab:
                break

    entities = data.get("entities") or {}
    if not isinstance(entities, dict):
        return tables, cols, by_table, rels, fk_aliases

    archive_key = ""
    archive_label = ""
    for slot, ent in entities.items():
        if not isinstance(ent, dict):
            continue
        key = str(ent.get("key") or "").strip()
        label = str(ent.get("label") or "").strip()
        verbs = ent.get("verbs") if isinstance(ent.get("verbs"), dict) else {}
        apply = str(verbs.get("apply") or "").strip()
        approve = str(verbs.get("approve") or "").strip()
        # 表名可能是 key（repair）或 slot 别名（ticket）；联系/中文名两边都挂上
        name_aliases = {x for x in (key, slot if slot in ("ticket", "reservation") else "") if x}
        if key and label:
            base_lab = label.removesuffix("单") if label.endswith("单") else label
            for tname in name_aliases or {key}:
                tables[tname] = label
                tables.setdefault(f"{tname}_log", f"{base_lab}日志")
                tables.setdefault(f"{tname}_attach", f"{base_lab}附件")
                tables.setdefault(f"{tname}_progress", f"{base_lab}进度")
        scoped = by_table.setdefault(key, {}) if key else {}
        for f in ent.get("fields") or []:
            if not isinstance(f, dict):
                continue
            fk = str(f.get("key") or "")
            fl = str(f.get("label") or "")
            if key:
                _put_col(scoped, fk, fl)
            if slot == "archive" and fk in ("category", "categoryId") and fl:
                tables.setdefault("category", fl)
        if apply:
            for tname in name_aliases:
                rels[tname] = apply
        if slot == "ticket" and approve:
            for tname in name_aliases:
                rels[f"{tname}::assignee_username"] = approve
                rels.setdefault("::assignee_username", approve)
        elif slot == "ticket" and staff_lab:
            for tname in name_aliases:
                rels.setdefault(f"{tname}::assignee_username", "办理")
                rels.setdefault("::assignee_username", "办理")
        if slot == "archive" and key:
            archive_key, archive_label = key, label

    # 单据表通用 FK：book_id / item_id → 档案实体编号
    if archive_key and archive_label:
        fk_aliases = {"archive": archive_key, "book": archive_key, "item": archive_key}
        for ticket_key, ent in entities.items():
            if ticket_key == "archive" or not isinstance(ent, dict):
                continue
            tk = str(ent.get("key") or "").strip()
            if not tk:
                continue
            scoped = by_table.setdefault(tk, {})
            for fk in ("book_id", "item_id", f"{archive_key}_id"):
                scoped.setdefault(fk, f"{archive_label}编号")
            # 日志表
            log_t = f"{tk}_log"
            tlab = tables.get(tk, tk)
            base_lab = tlab.removesuffix("单") if tlab.endswith("单") else tlab
            tables.setdefault(log_t, f"{base_lab}日志")
            by_table.setdefault(log_t, {})[f"{tk}_id"] = f"{tlab}编号"

    return tables, cols, by_table, rels, fk_aliases


def _short_role_label(lab: str) -> str:
    s = (lab or "").strip()
    if not s:
        return ""
    return re.split(r"[（(]", s, maxsplit=1)[0].strip() or s


def _domain_roles_bundle(
    path: Path | None,
) -> tuple[dict[str, str], bool, list[dict[str, str]]]:
    """角色中文名 + 任命开关 + worker 岗位列表 [{id,label}]。"""
    data = _read_json_dict(path)
    if not data:
        return {}, False, []
    roles = data.get("roles") if isinstance(data.get("roles"), dict) else {}
    out: dict[str, str] = {}
    for rid, raw in roles.items():
        if rid in ("staff_posts", "allowAppointFromUsers") or not isinstance(raw, dict):
            continue
        lab = _short_role_label(str(raw.get("label") or ""))
        if lab:
            out[str(rid)] = lab
    allow_appoint = bool(roles.get("allowAppointFromUsers"))
    posts = roles.get("staff_posts") if isinstance(roles.get("staff_posts"), list) else None
    if not posts:
        # 旧工作区 domain.schema 可能没落 staff_posts；从同目录 spec.json 取 domain 补作业岗
        domain = str(data.get("domain") or "").strip()
        archetype = data.get("archetype")
        arches = data.get("archetypes") if isinstance(data.get("archetypes"), list) else None
        if not domain and path is not None:
            spec = _read_json_dict(path.parent / "spec.json")
            domain = str(spec.get("domain") or "").strip()
            archetype = spec.get("archetype")
            arches = (
                spec.get("archetypes")
                if isinstance(spec.get("archetypes"), list)
                else None
            )
        if domain:
            try:
                from app.bake.staff_posts import staff_posts_for_domain

                posts = staff_posts_for_domain(domain, archetype, arches)
            except Exception:  # noqa: BLE001
                posts = []
            # 用岗位表校正子管文案（旧 JSON 可能把维修员误写进 subadmin）
            clerks = [p for p in (posts or []) if isinstance(p, dict) and p.get("kind") == "clerk"]
            if clerks and "subadmin" in out:
                clab = _short_role_label(str(clerks[0].get("label") or ""))
                if clab:
                    out["subadmin"] = clab
    workers: list[dict[str, str]] = []
    for p in posts or []:
        if not isinstance(p, dict) or p.get("kind") != "worker":
            continue
        pid = str(p.get("id") or "").strip()
        lab = _short_role_label(str(p.get("label") or ""))
        if pid and lab:
            workers.append({"id": pid, "label": lab})
    return out, allow_appoint, workers


def _via_to_role_id(via: str, roles: dict[str, str]) -> str:
    """外键列 → 门户角色：同一张 sys_user，总图拆成不同逻辑实体。"""
    via = via or ""
    staff = "subadmin" if "subadmin" in roles else ("admin" if "admin" in roles else "user")
    admin = "admin" if "admin" in roles else staff
    portal = "user" if "user" in roles else next(iter(roles), "user")
    if via in ("username", "uploaded_by", "uploader"):
        return portal
    if via == "operator":
        # 流水登记人多为管理侧
        return admin if "admin" in roles else staff
    if via in ("assignee_username", "handler_username"):
        return staff
    if via in ("publisher_username", "approver_username"):
        return admin
    if via.endswith("_username"):
        return staff
    return portal


def _appoint_or_govern(allow_appoint: bool) -> str:
    return "任命" if allow_appoint else "管辖"


def _role_hierarchy_relations(
    present: dict[str, str],
    *,
    allow_appoint: bool,
    worker_names: list[str] | None = None,
) -> list[dict]:
    """管理员↔岗位、管理员↔业务角色、作业岗派工（来自 roles/staff_posts）。"""
    out: list[dict] = []
    admin = present.get("admin")
    sub = present.get("subadmin")
    portal = present.get("user")
    workers = list(worker_names or [])
    govern = _appoint_or_govern(allow_appoint)
    if admin and sub:
        out.append(
            {
                "name": f"{admin}:staff",
                "left": admin,
                "right": sub,
                "card_left": "1",
                "card_right": "n",
                "via": "staff_post",
                "label": govern,
            }
        )
    if admin and portal:
        out.append(
            {
                "name": f"{admin}:portal",
                "left": admin,
                "right": portal,
                "card_left": "1",
                "card_right": "n",
                "via": "role_manage",
                "label": "管理",
            }
        )
    for wname in workers:
        if admin:
            out.append(
                {
                    "name": f"{admin}:{wname}",
                    "left": admin,
                    "right": wname,
                    "card_left": "1",
                    "card_right": "n",
                    "via": "staff_kind_worker",
                    "label": govern,
                }
            )
        if sub:
            out.append(
                {
                    "name": f"{sub}:{wname}",
                    "left": sub,
                    "right": wname,
                    "card_left": "1",
                    "card_right": "n",
                    "via": "dispatch_worker",
                    "label": "派工",
                }
            )
    return out


def expand_user_role_entities(model: dict, domain_path: Path | None = None) -> dict:
    """总图用：按 JSON roles 拆逻辑实体，并补管理员↔岗位/业务角色/作业岗联系。"""
    roles, allow_appoint, workers = _domain_roles_bundle(domain_path)
    if not roles:
        return model
    tables = list(model.get("tables") or [])
    user = next((t for t in tables if isinstance(t, dict) and t.get("name") == "sys_user"), None)
    if not user:
        return model

    relations = [dict(r) for r in (model.get("relations") or []) if isinstance(r, dict)]
    needed: set[str] = set()
    for r in relations:
        for side in ("left", "right"):
            if str(r.get(side) or "") != "sys_user":
                continue
            rid = _via_to_role_id(str(r.get("via") or ""), roles)
            if rid not in roles:
                rid = next(iter(roles))
            needed.add(rid)
            r[side] = f"sys_user:{rid}"

    if not needed:
        return model

    # 有业务边时，把 JSON 里声明的门户/总管/子管都拉齐，才能画角色间联系
    for rid in ("user", "subadmin", "admin"):
        if rid in roles:
            needed.add(rid)

    order = {"user": 0, "subadmin": 1, "admin": 2}
    out_tables = [t for t in tables if not (isinstance(t, dict) and t.get("name") == "sys_user")]
    present: dict[str, str] = {}
    for rid in sorted(needed, key=lambda x: order.get(x, 9)):
        ent_name = f"sys_user:{rid}"
        present[rid] = ent_name
        out_tables.append(
            {
                "name": ent_name,
                "label": roles[rid],
                "role_of": "sys_user",
                "role_id": rid,
                "columns": list(user.get("columns") or []),
                "core_columns": list(user.get("core_columns") or []),
            }
        )
    worker_names: list[str] = []
    for w in workers:
        ent_name = f"sys_user:worker:{w['id']}"
        worker_names.append(ent_name)
        out_tables.append(
            {
                "name": ent_name,
                "label": w["label"],
                "role_of": "sys_user",
                "role_id": f"worker:{w['id']}",
                "staff_kind": "worker",
                "columns": list(user.get("columns") or []),
                "core_columns": list(user.get("core_columns") or []),
            }
        )
    # 物理表留给分图；总图无连线时会被滤掉
    out_tables.append(dict(user))
    relations.extend(
        _role_hierarchy_relations(
            present, allow_appoint=allow_appoint, worker_names=worker_names
        )
    )
    model = {**model, "tables": out_tables, "relations": relations}
    return scrub_relation_labels(model)


def schema_model(
    sql: str,
    extra_table_zh: dict[str, str] | None = None,
    extra_col_zh: dict[str, str] | None = None,
    extra_table_cols: dict[str, dict[str, str]] | None = None,
    extra_rel_zh: dict[str, str] | None = None,
    fk_aliases: dict[str, str] | None = None,
) -> dict:
    tables = parse_schema_sql(sql, fk_aliases=fk_aliases)
    relations = infer_relations(tables)
    tzh = {**_INFRA_TABLE_ZH, **(extra_table_zh or {})}
    czh = {**_COMMON_COL_ZH, **(extra_col_zh or {})}
    tcols = dict(extra_table_cols or {})
    rzh = dict(extra_rel_zh or {})
    model = {
        "tables": [
            {
                "name": t.name,
                "label": _table_zh(t.name, tzh),
                "columns": [
                    {
                        **asdict(c),
                        "label": _col_zh(c.name, t.name, czh, tcols, tzh),
                    }
                    for c in t.columns
                ],
                "core_columns": [
                    {
                        **asdict(c),
                        "label": _col_zh(c.name, t.name, czh, tcols, tzh),
                    }
                    for c in pick_core_attrs(t.columns)
                ],
            }
            for t in tables
        ],
        "relations": [
            {
                **asdict(r),
                "label": _rel_zh(r.name, r.via, r.left, r.right, tzh, rzh),
            }
            for r in relations
        ],
    }
    # 唯一闸门：联系名不得与实体中文名撞车
    return scrub_relation_labels(model, tzh, rzh)


def _part_lab(part: str, tzh: dict[str, str]) -> str | None:
    return tzh.get(part) or _TABLE_PART_ZH.get(part)


def _table_zh(name: str, tzh: dict[str, str]) -> str:
    # tzh 已含 _INFRA_TABLE_ZH（见 schema_model）
    if name in tzh:
        return tzh[name]
    short = name.replace("sys_", "")
    if short != name and short in tzh:
        return tzh[short]
    for suffix, zh_suffix in (("_log", "日志"), ("_attach", "附件"), ("_progress", "进度")):
        if name.endswith(suffix):
            return f"{_table_zh(name[: -len(suffix)], tzh)}{zh_suffix}"
    if "_" in name:
        parts = name.split("_")
        labs = [_part_lab(p, tzh) for p in parts]
        if all(labs):
            return "".join(lab for lab in labs if lab)
    return short


def _stem_zh(stem: str, czh: dict[str, str]) -> str:
    return czh.get(stem) or _STEM_ZH.get(stem) or ""


def _col_zh(
    name: str,
    table: str,
    czh: dict[str, str],
    tcols: dict[str, dict[str, str]],
    tzh: dict[str, str],
) -> str:
    scoped = tcols.get(table) or {}
    if name in scoped:
        return scoped[name]
    if name in czh:
        return czh[name]
    if name.endswith("_id") and len(name) > 3:
        base = name[:-3]
        lab = _part_lab(base, tzh) or _stem_zh(base, czh)
        return f"{lab}编号" if lab else "关联编号"
    for suffix, default, fmt in _COL_SUFFIX_RULES:
        if name.endswith(suffix) and len(name) > len(suffix):
            stem = _stem_zh(name[: -len(suffix)], czh)
            return fmt.format(stem=stem) if stem else default
    if name.startswith("super_"):
        return "总管"
    if name.endswith("_editable"):
        return "可改资料"
    return name


def _rel_zh_from_via(via: str, right: str = "", left: str = "") -> str:
    """按外键列 + 子表定联系文案，绝不引用实体中文名。"""
    via = via or ""
    right = right or ""
    left = left or ""
    # 登记人 / 上传人：优先于「子表默认名」，避免 operator→流水被标成「归属」
    if via == "operator":
        return "登记"
    if via == "uploaded_by" or via == "uploader":
        return "上传"
    # 角色列：publisher_username / assignee_username …
    # assignee = 办理人，不是「指派」动作（指派/派工留给角色间联系）
    if via.endswith("_username") and len(via) > 9:
        stem = via[: -len("_username")]
        role = {
            "publisher": "发布",
            "assignee": "办理",
            "handler": "处理",
            "approver": "审批",
        }.get(stem)
        if role:
            return role
    if right.endswith("_attach") or (via == "ticket_id" and right.endswith("_attach")):
        return "附件"
    if via == "ticket_id" or right.endswith("_progress"):
        return "进度"
    if via == "category_id" or via == "type_id":
        return "属于"
    # 时段：档案→名额是排班；名额→预约单才是预约
    if via == "slot_id":
        return "预约"
    if right == "resource_slot" or (via == "item_id" and "slot" in right):
        return "排班"
    if via == "building_id":
        return "包含"
    if via == "room_id":
        return "涉及"
    if right.endswith("_log") or via.endswith("_log"):
        return "记录"
    if right.endswith("_favorite"):
        # 用户侧收藏；档案侧是被收录
        return "收藏" if via == "username" else "收录"
    # 仅账户主体 username：按子表语义；operator 等不要走进这里
    if via == "username":
        by_child = {
            "sys_notice": "发布",
            "sys_message": "接收",
            "user_ledger": "归属",
        }
        if right in by_child:
            return by_child[right]
        return "归属"
    if via.endswith("_username"):
        return "关联"
    if via in ("book_id", "item_id") or via.endswith("_id"):
        return "关联"
    return "关联"


def _apply_verb_label(verb: str, right_entity_label: str = "") -> str:
    """verbs.apply 作菱形名；与单据实体同名时加「提交」以免实体/联系撞名。"""
    verb = (verb or "").strip()
    if not verb:
        return ""
    right_lab = (right_entity_label or "").strip()
    if verb == right_lab or verb == right_lab.removesuffix("单"):
        if not verb.startswith("提交"):
            return f"提交{verb}"
    return verb


def _archive_ticket_rel_label(verb: str, right_entity_label: str = "") -> str:
    """档案→单据（book_id/item_id）：尽量用 apply 词干，撞名则用「对应」。"""
    verb = (verb or "").strip()
    right_lab = (right_entity_label or "").strip()
    stem = verb
    for prefix in ("提交", "申请"):
        if stem.startswith(prefix) and len(stem) > len(prefix):
            stem = stem[len(prefix) :]
            break
    if stem and stem not in {right_lab, right_lab.removesuffix("单")}:
        return stem
    return "对应"


def _rel_zh(
    name: str,
    via: str,
    left: str,
    right: str,
    tzh: dict[str, str],
    rzh: dict[str, str],
) -> str:
    """候选联系文案；domain.schema.json 的 verbs/角色列优先，撞实体名由 scrub 处理。"""
    _ = name
    _ = left
    via = via or ""
    right = right or ""
    right_lab = str(tzh.get(right) or "").strip()
    # 申请人：verbs.apply；无 apply 时用实体名动作（如挂号）
    if via == "username":
        if right in rzh:
            verb = _apply_verb_label(str(rzh[right] or ""), right_lab)
            if verb:
                return verb
        if right_lab and right not in {
            "sys_message",
            "sys_notice",
            "user_ledger",
            "sys_config",
        }:
            verb = _apply_verb_label(right_lab, right_lab)
            if verb:
                return verb
    # 档案→单据
    if via in ("book_id", "item_id") and right in rzh:
        return _archive_ticket_rel_label(str(rzh[right] or ""), right_lab)
    # 办理方等角色列：verbs.approve → table::assignee_username
    if via:
        for key in (f"{right}::{via}", f"::{via}"):
            verb = str(rzh.get(key) or "").strip()
            if verb:
                return verb
    return _rel_zh_from_via(via, right, left)


def _entity_label_set(model: dict, tzh: dict[str, str] | None = None) -> set[str]:
    """当前图里实体的中文名/表名。勿把词根词典整表塞进黑名单（会误杀「进度」等合法联系词）。"""
    out: set[str] = set()
    names: set[str] = set()
    for t in model.get("tables") or []:
        if not isinstance(t, dict):
            continue
        tname = str(t.get("name") or "").strip()
        if tname:
            names.add(tname)
            out.add(tname)
            short = tname.replace("sys_", "")
            if short:
                out.add(short)
        lab = str(t.get("label") or "").strip()
        if lab:
            out.add(lab)
    for k, v in (tzh or {}).items():
        if k in names:
            s = str(v or "").strip()
            if s:
                out.add(s)
    return out


def scrub_relation_labels(
    model: dict,
    tzh: dict[str, str] | None = None,
    rzh: dict[str, str] | None = None,
) -> dict:
    """唯一闸门：把「实体名当联系名」打回按 via/子表生成的联系词。"""
    tzh = dict(tzh or {})
    rzh = dict(rzh or {})
    # 用模型当前实体标签补全 tzh，便于 apply 撞名时加「提交」
    for t in model.get("tables") or []:
        if isinstance(t, dict) and t.get("name") and t.get("label"):
            tzh.setdefault(str(t["name"]), str(t["label"]))
    banned = _entity_label_set(model, tzh)
    for r in model.get("relations") or []:
        if not isinstance(r, dict):
            continue
        via = str(r.get("via") or "")
        left = str(r.get("left") or "")
        right = str(r.get("right") or "")
        name = str(r.get("name") or "")
        lab = str(r.get("label") or "").strip()
        if lab and lab not in banned:
            continue
        fixed = _rel_zh(name, via, left, right, tzh, rzh)
        if fixed in banned:
            fixed = _rel_zh_from_via(via, right, left)
        if fixed in banned:
            fixed = "关联"
        r["label"] = fixed
    return model


def looks_latin(text: str) -> bool:
    """展示文案仍含拉丁字母（英文漏网）。"""
    return bool(_LATIN_RE.search(text or ""))


def collect_english_gaps(model: dict) -> dict[str, list[dict[str, str]]]:
    """收集 E-R 模型里仍含英文的实体 / 属性 / 联系，供 ER Label Agent 补中文。"""
    tables: list[dict[str, str]] = []
    columns: list[dict[str, str]] = []
    relations: list[dict[str, str]] = []
    for t in model.get("tables") or []:
        if not isinstance(t, dict):
            continue
        tname = str(t.get("name") or "")
        tlab = str(t.get("label") or tname)
        if looks_latin(tlab):
            tables.append({"name": tname, "label": tlab})
        for c in t.get("columns") or []:
            if not isinstance(c, dict):
                continue
            cname = str(c.get("name") or "")
            clab = str(c.get("label") or cname)
            if looks_latin(clab):
                columns.append({"table": tname, "name": cname, "label": clab})
    for r in model.get("relations") or []:
        if not isinstance(r, dict):
            continue
        rname = str(r.get("name") or "")
        rlab = str(r.get("label") or rname)
        if looks_latin(rlab):
            relations.append(
                {
                    "name": rname,
                    "label": rlab,
                    "left": str(r.get("left") or ""),
                    "right": str(r.get("right") or ""),
                    "via": str(r.get("via") or ""),
                }
            )
    return {"tables": tables, "columns": columns, "relations": relations}


def count_er_gaps(gaps: dict[str, list] | None) -> int:
    return sum(len((gaps or {}).get(k) or []) for k in ("tables", "columns", "relations"))


def count_er_patch_fills(patch: dict | None) -> int:
    p = patch or {}
    return (
        len(p.get("tables") or {})
        + sum(len(v) for v in (p.get("columns") or {}).values() if isinstance(v, dict))
        + len(p.get("relations") or {})
    )


def _sanitize_zh_label(raw: str, *, fallback: str, max_len: int = 16) -> str:
    s = (raw or "").strip().replace("\n", "").replace("\r", "")
    s = re.sub(r"\s+", "", s)
    if not s or looks_latin(s):
        return fallback
    return s[:max_len]


def sanitize_er_label_patch(
    data: dict | None,
    gaps: dict[str, list[dict[str, str]]] | None = None,
) -> dict:
    """清洗补丁；若给 gaps 则只保留缺口内的键，且拒绝拉丁字母标签。"""
    data = data or {}
    allowed_tables = {g["name"] for g in (gaps or {}).get("tables") or []} if gaps else None
    allowed_cols = (
        {(g["table"], g["name"]) for g in (gaps or {}).get("columns") or []} if gaps else None
    )
    allowed_rels = {g["name"] for g in (gaps or {}).get("relations") or []} if gaps else None

    tables_out: dict[str, str] = {}
    for k, v in (data.get("tables") or {}).items():
        key = str(k).strip()
        if not key or (allowed_tables is not None and key not in allowed_tables):
            continue
        lab = _sanitize_zh_label(str(v or ""), fallback="", max_len=16)
        if lab:
            tables_out[key] = lab

    columns_out: dict[str, dict[str, str]] = {}
    raw_cols = data.get("columns") or {}
    if isinstance(raw_cols, dict):
        for tk, cols in raw_cols.items():
            if not isinstance(cols, dict):
                continue
            tname = str(tk).strip()
            bucket: dict[str, str] = {}
            for ck, lab in cols.items():
                cname = str(ck).strip()
                if not cname or (
                    allowed_cols is not None and (tname, cname) not in allowed_cols
                ):
                    continue
                text = _sanitize_zh_label(str(lab or ""), fallback="", max_len=16)
                if text:
                    bucket[cname] = text
            if bucket:
                columns_out[tname] = bucket

    relations_out: dict[str, str] = {}
    for k, v in (data.get("relations") or {}).items():
        key = str(k).strip()
        if not key or (allowed_rels is not None and key not in allowed_rels):
            continue
        lab = _sanitize_zh_label(str(v or ""), fallback="", max_len=12)
        if lab:
            relations_out[key] = lab

    return {"tables": tables_out, "columns": columns_out, "relations": relations_out}


def apply_er_label_patch(model: dict, patch: dict | None) -> dict:
    """把 {tables, columns, relations} 中文补丁盖到 schema model 上。"""
    clean = sanitize_er_label_patch(patch)
    if not clean["tables"] and not clean["columns"] and not clean["relations"]:
        return scrub_relation_labels(model)
    tmap = clean["tables"]
    cmap = {
        (tk, ck): lab
        for tk, cols in clean["columns"].items()
        for ck, lab in cols.items()
    }
    rmap = clean["relations"]

    for t in model.get("tables") or []:
        if not isinstance(t, dict):
            continue
        tname = str(t.get("name") or "")
        if tname in tmap:
            t["label"] = tmap[tname]
        for c in t.get("columns") or []:
            if not isinstance(c, dict):
                continue
            key = (tname, str(c.get("name") or ""))
            if key in cmap:
                c["label"] = cmap[key]
    for r in model.get("relations") or []:
        if not isinstance(r, dict):
            continue
        rname = str(r.get("name") or "")
        via = str(r.get("via") or "")
        left = str(r.get("left") or "")
        right = str(r.get("right") or "")
        cand = rmap.get(rname) or rmap.get(f"{left}|{right}|{via}")
        if cand:
            r["label"] = cand
    # 联系撞实体名统一在此打回，不在上面再拦一遍
    return scrub_relation_labels(model)


def er_labels_path(workspace: Path) -> Path:
    return workspace / _ER_LABELS_REL


def load_er_label_patch(workspace: Path) -> dict:
    return _read_json_dict(er_labels_path(workspace))


def save_er_label_patch(workspace: Path, patch: dict) -> Path:
    path = er_labels_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": patch.get("mode") or "llm",
        "tables": patch.get("tables") or {},
        "columns": patch.get("columns") or {},
        "relations": patch.get("relations") or {},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_schema_model(workspace: Path, *, with_er_patch: bool = True) -> dict | None:
    """从工作区 schema.sql 建 E-R 模型；with_er_patch=False 时仅确定性映射。"""
    path = workspace / "sql" / "schema.sql"
    if not path.exists():
        return None
    domain_path = workspace / "domain.schema.json"
    tzh, czh, tcols, rzh, fk_aliases = _labels_from_domain_schema(domain_path)
    model = schema_model(
        path.read_text(encoding="utf-8", errors="ignore"),
        extra_table_zh=tzh,
        extra_col_zh=czh,
        extra_table_cols=tcols,
        extra_rel_zh=rzh,
        fk_aliases=fk_aliases,
    )
    if with_er_patch:
        model = apply_er_label_patch(model, load_er_label_patch(workspace))
    # 同一张用户表按 JSON roles 拆逻辑实体（申领人 / 库管员…），总图不再只写「用户」
    return expand_user_role_entities(model, domain_path)


def load_schema_model(workspace: Path) -> dict | None:
    return build_schema_model(workspace, with_er_patch=True)


# —— SVG 陈氏 E-R ——

ENTITY_HH = 22
ATTR_RH = 14


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _text_w(s: str, px: float = 12.0) -> float:
    """粗估中西文混排宽度。"""
    w = 0.0
    for ch in s:
        w += px if ord(ch) > 127 else px * 0.55
    return w


def _entity_hw(label: str) -> float:
    return max(40.0, _text_w(label, 13) / 2 + 14)


def _attr_rx(label: str) -> float:
    return max(28.0, _text_w(label, 10) / 2 + 12)


def _attr_cloud_radius(attrs: list[dict], entity_hw: float) -> float:
    m = len(attrs)
    if m == 0:
        return 0.0
    max_rx = max((_attr_rx(c.get("label") or c["name"]) for c in attrs), default=28.0)
    clear_box = math.hypot(entity_hw, ENTITY_HH) + max_rx + 30
    if m == 1:
        return clear_box
    need = (2 * max_rx + 20) / (2 * math.sin(math.pi / m))
    return max(clear_box, need)


def _rect_edge(cx: float, cy: float, tx: float, ty: float, hw: float, hh: float) -> tuple[float, float]:
    dx, dy = tx - cx, ty - cy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return cx, cy - hh
    sx = hw / abs(dx) if abs(dx) > 1e-9 else float("inf")
    sy = hh / abs(dy) if abs(dy) > 1e-9 else float("inf")
    t = min(sx, sy)
    return cx + dx * t, cy + dy * t


def _ellipse_edge(cx: float, cy: float, rx: float, ry: float, fx: float, fy: float) -> tuple[float, float]:
    ox, oy = fx - cx, fy - cy
    if abs(ox) < 1e-9 and abs(oy) < 1e-9:
        return cx, cy - ry
    s = math.hypot(ox / rx, oy / ry) or 1.0
    return cx + ox / s, cy + oy / s


def _diamond_edge(cx: float, cy: float, hw: float, hh: float, tx: float, ty: float) -> tuple[float, float]:
    """菱形 |dx|/hw + |dy|/hh = 1 与中心→目标射线的交点。"""
    ox, oy = tx - cx, ty - cy
    if abs(ox) < 1e-9 and abs(oy) < 1e-9:
        return cx, cy - hh
    denom = abs(ox) / hw + abs(oy) / hh
    if denom < 1e-9:
        return cx, cy - hh
    t = 1.0 / denom
    return cx + ox * t, cy + oy * t


def _circular_crossings(order: list[str], edges: list[tuple[str, str]]) -> int:
    """环上弦交叉数（四端点交错）。"""
    n = len(order)
    pos = {name: i for i, name in enumerate(order)}
    idx_edges: list[tuple[int, int]] = []
    for a, b in edges:
        if a not in pos or b not in pos or a == b:
            continue
        i, j = pos[a], pos[b]
        if i > j:
            i, j = j, i
        idx_edges.append((i, j))
    count = 0
    for i, (a, b) in enumerate(idx_edges):
        for c, d in idx_edges[i + 1 :]:
            # 共享顶点不算交叉
            if len({a, b, c, d}) < 4:
                continue
            # 交错：a < c < b < d 或 c < a < d < b
            if (a < c < b < d) or (c < a < d < b):
                count += 1
    return count


def _order_minimize_crossings(names: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """小规模：邻接交换最小化环上交叉。"""
    order = list(names)
    n = len(order)
    if n <= 2:
        return order
    best = _circular_crossings(order, edges)
    if best == 0:
        return order
    improved = True
    rounds = 0
    while improved and rounds < 80:
        improved = False
        rounds += 1
        for i in range(n):
            for j in range(i + 1, n):
                order[i], order[j] = order[j], order[i]
                c = _circular_crossings(order, edges)
                if c < best:
                    best = c
                    improved = True
                    if best == 0:
                        return order
                else:
                    order[i], order[j] = order[j], order[i]
    return order


def _pair_offset(lp: tuple[float, float], rp: tuple[float, float], index: int, total: int) -> tuple[float, float]:
    """同对多联系时，菱形沿弦垂线错开。"""
    if total <= 1:
        return 0.0, 0.0
    dx, dy = rp[0] - lp[0], rp[1] - lp[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    mid = (total - 1) / 2
    dist = (index - mid) * 36.0
    return nx * dist, ny * dist


def render_er_svg(
    model: dict,
    title: str = "E-R",
    *,
    mode: str = "total",
    entity: str | None = None,
) -> str:
    """陈氏 E-R 线框图。

    mode=total：总图（实体 + 联系 + 基数，不含属性，贴合论文总 E-R）。
    mode=part：分图（单个实体 + 全部属性，不含联系）。
    图内不放标题/图例（图注写 Word）。
    """
    _ = title
    mode = (mode or "total").strip().lower()
    if mode not in ("total", "part"):
        mode = "total"

    tables = list(model.get("tables") or [])
    relations = list(model.get("relations") or [])
    if not tables:
        return _svg_wrap(480, 200, '<text x="24" y="100" font-size="14">无表结构</text>')

    show_attrs = mode == "part"
    if mode == "part":
        ent_name = (entity or "").strip() or str(tables[0].get("name") or "")
        tables = [t for t in tables if t.get("name") == ent_name]
        if not tables:
            return _svg_wrap(480, 200, '<text x="24" y="100" font-size="14">未找到该实体</text>')
        relations = []
    else:
        # 总图：去掉无联系的悬空实体（如纯配置表），让图成连通业务网
        linked: set[str] = set()
        for r in relations:
            if isinstance(r, dict):
                linked.add(str(r.get("left") or ""))
                linked.add(str(r.get("right") or ""))
        linked.discard("")
        if linked:
            tables = [t for t in tables if t.get("name") in linked]
            kept = {t.get("name") for t in tables}
            relations = [
                r
                for r in relations
                if isinstance(r, dict)
                and r.get("left") in kept
                and r.get("right") in kept
            ]

    names = [t["name"] for t in tables]
    edges = [(r["left"], r["right"]) for r in relations]
    order = _order_minimize_crossings(names, edges)
    by_name = {t["name"]: t for t in tables}
    ordered_tables = [by_name[n] for n in order if n in by_name]

    entity_hw: dict[str, float] = {
        t["name"]: _entity_hw(t.get("label") or t["name"]) for t in tables
    }

    def _attrs_for(t: dict) -> list:
        if not show_attrs:
            return []
        # 分图用全列；总图不画属性
        return list(t.get("columns") or [])

    clouds = {
        t["name"]: (
            _attr_cloud_radius(_attrs_for(t), entity_hw[t["name"]])
            if show_attrs
            else max(48.0, entity_hw[t["name"]] + 24)
        )
        for t in tables
    }
    max_cloud = max(clouds.values()) if clouds else 80
    n = len(ordered_tables)
    if n <= 1:
        ring_r = 0.0
    else:
        pair_need = 2 * max_cloud + (64 if not show_attrs else 120)
        ring_r = pair_need / (2 * math.sin(math.pi / n))
        # 总图实体少时不必撑到很大，避免预览一大块空底
        ring_r = max(ring_r, 120.0 if not show_attrs else 200.0)

    pad = 56.0 if not show_attrs else 72.0
    content_r = ring_r + max_cloud
    w = int(2 * content_r + 2 * pad)
    h = int(2 * content_r + 2 * pad)
    w, h = max(w, 360), max(h, 280)
    cx, cy = w / 2.0, h / 2.0

    entity_pos: dict[str, tuple[float, float]] = {}
    for i, t in enumerate(ordered_tables):
        if n == 1:
            entity_pos[t["name"]] = (cx, cy)
        else:
            ang = -math.pi / 2 + 2 * math.pi * i / n
            entity_pos[t["name"]] = (cx + ring_r * math.cos(ang), cy + ring_r * math.sin(ang))

    # 同对联系计数，便于垂线错开
    pair_keys: list[tuple[str, str]] = []
    for r in relations:
        a, b = r["left"], r["right"]
        pair_keys.append((a, b) if a <= b else (b, a))
    pair_totals: dict[tuple[str, str], int] = {}
    for pk in pair_keys:
        pair_totals[pk] = pair_totals.get(pk, 0) + 1
    pair_seen: dict[tuple[str, str], int] = {}

    edge_parts: list[str] = []
    node_parts: list[str] = []
    card_parts: list[str] = []

    # 联系：直线实体边 → 菱形边 → 实体边（仅总图）
    for ri, r in enumerate(relations):
        lp = entity_pos.get(r["left"])
        rp = entity_pos.get(r["right"])
        if not lp or not rp:
            continue
        left_id = f"entity:{r['left']}"
        right_id = f"entity:{r['right']}"
        rel_id = f"rel:{ri}"
        pk = pair_keys[ri]
        pi = pair_seen.get(pk, 0)
        pair_seen[pk] = pi + 1
        ox, oy = _pair_offset(lp, rp, pi, pair_totals[pk])
        mx = (lp[0] + rp[0]) / 2 + ox
        my = (lp[1] + rp[1]) / 2 + oy

        hw1 = entity_hw.get(r["left"], 40)
        hw2 = entity_hw.get(r["right"], 40)
        rel_label = r.get("label") or r["name"]
        dw = max(36.0, _text_w(rel_label, 12) / 2 + 16)
        dh = 22.0

        e1 = _rect_edge(lp[0], lp[1], mx, my, hw1, ENTITY_HH)
        d1 = _diamond_edge(mx, my, dw, dh, lp[0], lp[1])
        d2 = _diamond_edge(mx, my, dw, dh, rp[0], rp[1])
        e2 = _rect_edge(rp[0], rp[1], mx, my, hw2, ENTITY_HH)

        edge_parts.append(
            f'<line class="er-edge" data-from="{_esc(left_id)}" data-to="{_esc(rel_id)}" '
            f'x1="{e1[0]:.1f}" y1="{e1[1]:.1f}" x2="{d1[0]:.1f}" y2="{d1[1]:.1f}" '
            f'stroke="#000" stroke-width="1" fill="none"/>'
        )
        edge_parts.append(
            f'<line class="er-edge" data-from="{_esc(rel_id)}" data-to="{_esc(right_id)}" '
            f'x1="{d2[0]:.1f}" y1="{d2[1]:.1f}" x2="{e2[0]:.1f}" y2="{e2[1]:.1f}" '
            f'stroke="#000" stroke-width="1" fill="none"/>'
        )

        diamond = (
            f"{mx:.1f},{my - dh:.1f} {mx + dw:.1f},{my:.1f} "
            f"{mx:.1f},{my + dh:.1f} {mx - dw:.1f},{my:.1f}"
        )
        node_parts.append(
            f'<g class="er-node" data-kind="rel" data-id="{_esc(rel_id)}" data-shape="diamond" '
            f'data-cx="{mx:.1f}" data-cy="{my:.1f}" data-hw="{dw:.1f}" data-hh="{dh:.1f}">'
            f'<polygon points="{diamond}" fill="#fff" stroke="#000" stroke-width="1.2"/>'
            f'<text x="{mx:.1f}" y="{my + 4:.1f}" text-anchor="middle" '
            f'font-family="Microsoft YaHei, SimSun, serif" font-size="12">{_esc(rel_label)}</text>'
            f"</g>"
        )

        # 基数：沿直线段 35% 处，垂向微偏
        def _card_pos(
            a: tuple[float, float], b: tuple[float, float], t: float = 0.35
        ) -> tuple[float, float]:
            px = a[0] * (1 - t) + b[0] * t
            py = a[1] * (1 - t) + b[1] * t
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1.0
            return px - dy / L * 12, py + dx / L * 12

        c1 = _card_pos(e1, d1)
        c2 = _card_pos(e2, d2)
        card_parts.append(
            f'<text class="er-card" data-from="{_esc(left_id)}" data-to="{_esc(rel_id)}" '
            f'x="{c1[0]:.1f}" y="{c1[1]:.1f}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12">{_esc(r["card_left"])}</text>'
        )
        card_parts.append(
            f'<text class="er-card" data-from="{_esc(right_id)}" data-to="{_esc(rel_id)}" '
            f'x="{c2[0]:.1f}" y="{c2[1]:.1f}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12">{_esc(r["card_right"])}</text>'
        )

    # 实体 +（分图）属性
    for t in ordered_tables:
        name = t["name"]
        label = t.get("label") or name
        x, y = entity_pos[name]
        hw = entity_hw[name]
        ent_id = f"entity:{name}"
        node_parts.append(
            f'<g class="er-node" data-kind="entity" data-id="{_esc(ent_id)}" data-shape="rect" '
            f'data-cx="{x:.1f}" data-cy="{y:.1f}" data-hw="{hw:.1f}" data-hh="{ENTITY_HH:.1f}">'
            f'<rect x="{x - hw:.1f}" y="{y - ENTITY_HH:.1f}" '
            f'width="{hw * 2:.1f}" height="{ENTITY_HH * 2:.1f}" '
            f'fill="#fff" stroke="#000" stroke-width="1.5"/>'
            f'<text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" '
            f'font-family="Microsoft YaHei, SimSun, serif" font-size="13" font-weight="600">'
            f"{_esc(label)}</text>"
            f"</g>"
        )

        attrs = _attrs_for(t)
        m = len(attrs)
        if m == 0:
            continue
        ar = clouds[name]
        base = math.atan2(y - cy, x - cx) if n > 1 else -math.pi / 2
        for ai, col in enumerate(attrs):
            ang = base + 2 * math.pi * ai / m
            ax = x + ar * math.cos(ang)
            ay = y + ar * math.sin(ang)
            alabel = col.get("label") or col["name"]
            rx = _attr_rx(alabel)
            attr_id = f"attr:{name}.{col['name']}"
            p0 = _rect_edge(x, y, ax, ay, hw, ENTITY_HH)
            p1 = _ellipse_edge(ax, ay, rx, ATTR_RH, x, y)
            edge_parts.append(
                f'<line class="er-edge" data-from="{_esc(ent_id)}" data-to="{_esc(attr_id)}" '
                f'x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" '
                f'stroke="#000" stroke-width="0.8" fill="none"/>'
            )
            tw = min(rx * 1.7, _text_w(alabel, 10))
            deco = ""
            if col.get("pk"):
                deco = (
                    f'<line x1="{ax - tw / 2:.1f}" y1="{ay + 8:.1f}" '
                    f'x2="{ax + tw / 2:.1f}" y2="{ay + 8:.1f}" stroke="#000" stroke-width="1"/>'
                )
            elif col.get("fk"):
                wave = []
                x0 = ax - tw / 2
                steps = max(4, int(tw / 6))
                for si in range(steps + 1):
                    wx = x0 + tw * si / steps
                    wy = ay + 8 + (2 if si % 2 else -2)
                    wave.append(f"{wx:.1f},{wy:.1f}")
                deco = (
                    f'<polyline points="{" ".join(wave)}" fill="none" stroke="#000" stroke-width="1"/>'
                )
            node_parts.append(
                f'<g class="er-node" data-kind="attr" data-id="{_esc(attr_id)}" '
                f'data-parent="{_esc(ent_id)}" data-shape="ellipse" '
                f'data-cx="{ax:.1f}" data-cy="{ay:.1f}" data-rx="{rx:.1f}" data-ry="{ATTR_RH:.1f}">'
                f'<ellipse cx="{ax:.1f}" cy="{ay:.1f}" rx="{rx:.1f}" ry="{ATTR_RH:.1f}" '
                f'fill="#fff" stroke="#000" stroke-width="1"/>'
                f'<text x="{ax:.1f}" y="{ay + 4:.1f}" text-anchor="middle" '
                f'font-family="Microsoft YaHei, sans-serif" font-size="10">{_esc(alabel)}</text>'
                f"{deco}</g>"
            )

    parts = (
        ['<g class="er-edges">']
        + edge_parts
        + card_parts
        + ["</g>"]
        + ['<g class="er-nodes">']
        + node_parts
        + ["</g>"]
    )
    return _svg_wrap(w, h, "\n".join(parts))



def _svg_wrap(w: int, h: int, inner: str) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">\n'
        f'<rect class="er-paper" width="100%" height="100%" fill="#fff"/>\n'
        f"{inner}\n</svg>\n"
    )
