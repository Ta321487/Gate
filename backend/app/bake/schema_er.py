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

# 各域 schema.sql 都会有、但不进 entities 的表
_INFRA_TABLE_ZH: dict[str, str] = {
    "sys_user": "用户",
    "sys_notice": "公告",
    "sys_message": "消息",
    "sys_config": "配置",
    "category": "分类",
}

# 不依赖领域的公共列（领域字段优先用 domain.schema 的 fields/profileFields）
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
}

# 去掉后缀后的词根（*_at / *_url / *_yuan / *_msg / *_code）
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
}


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


def parse_schema_sql(sql: str) -> list[Table]:
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

    _infer_fk_by_name(tables)
    return tables


def _infer_fk_by_name(tables: list[Table]) -> None:
    names = {t.name for t in tables}
    for t in tables:
        for c in t.columns:
            if c.fk or c.pk:
                continue
            if c.name.endswith("_id") and len(c.name) > 3:
                base = c.name[:-3]
                candidates = [base, f"sys_{base}", f"{base}s"]
                for cand in candidates:
                    if cand in names and cand != t.name:
                        c.fk = True
                        c.fk_table = cand
                        break
            elif c.name == "username" and "sys_user" in names and t.name != "sys_user":
                c.fk = True
                c.fk_table = "sys_user"


def _short_name(table: str) -> str:
    return table.replace("sys_", "")


def _rel_label(parent: str, child: str, by_name: dict[str, Table]) -> str:
    child_t = by_name.get(child)
    parent_t = by_name.get(parent)
    child_fk_n = sum(1 for c in (child_t.columns if child_t else []) if c.fk)
    if child_fk_n >= 2:
        return _short_name(child)
    if parent_t and len(parent_t.columns) <= 3:
        return _short_name(parent)
    return _short_name(child)


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
                    name=_rel_label(parent, child, by_name),
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


def _labels_from_domain_schema(
    path: Path,
) -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, str]], dict[str, str]]:
    """从 domain.schema.json 抽：表名、公共列、按表列、联系名（仅 verbs.apply）。"""
    tables: dict[str, str] = {}
    cols: dict[str, str] = {}
    by_table: dict[str, dict[str, str]] = {}
    rels: dict[str, str] = {}
    if not path.is_file():
        return tables, cols, by_table, rels
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return tables, cols, by_table, rels

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

    entities = data.get("entities") or {}
    if not isinstance(entities, dict):
        return tables, cols, by_table, rels

    archive_key = ""
    archive_label = ""
    for slot, ent in entities.items():
        if not isinstance(ent, dict):
            continue
        key = str(ent.get("key") or "").strip()
        label = str(ent.get("label") or "").strip()
        if key and label:
            tables[key] = label
            base_lab = label.removesuffix("单") if label.endswith("单") else label
            tables.setdefault(f"{key}_log", f"{base_lab}日志")
            tables.setdefault(f"{key}_attach", f"{base_lab}附件")
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
        verbs = ent.get("verbs") if isinstance(ent.get("verbs"), dict) else {}
        apply = str(verbs.get("apply") or "").strip()
        if key and apply:
            rels[key] = apply
        if slot == "archive" and key:
            archive_key, archive_label = key, label

    # 单据表通用 FK：book_id / item_id → 档案实体编号
    if archive_key and archive_label:
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

    return tables, cols, by_table, rels


def schema_model(
    sql: str,
    extra_table_zh: dict[str, str] | None = None,
    extra_col_zh: dict[str, str] | None = None,
    extra_table_cols: dict[str, dict[str, str]] | None = None,
    extra_rel_zh: dict[str, str] | None = None,
) -> dict:
    tables = parse_schema_sql(sql)
    relations = infer_relations(tables)
    tzh = {**_INFRA_TABLE_ZH, **(extra_table_zh or {})}
    czh = {**_COMMON_COL_ZH, **(extra_col_zh or {})}
    tcols = dict(extra_table_cols or {})
    rzh = dict(extra_rel_zh or {})
    return {
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


def _table_zh(name: str, tzh: dict[str, str]) -> str:
    if name in tzh:
        return tzh[name]
    short = name.replace("sys_", "")
    if short in tzh:
        return tzh[short]
    for suffix, zh_suffix in (("_log", "日志"), ("_attach", "附件"), ("_progress", "进度")):
        if name.endswith(suffix):
            base = name[: -len(suffix)]
            return f"{_table_zh(base, tzh)}{zh_suffix}"
    if "_" in name:
        parts = name.split("_")
        if all(p in tzh or p in _INFRA_TABLE_ZH for p in parts):
            return "".join(tzh.get(p) or _INFRA_TABLE_ZH.get(p, p) for p in parts)
    return short


def _stem_zh(stem: str, czh: dict[str, str]) -> str:
    if stem in czh:
        return czh[stem]
    if stem in _STEM_ZH:
        return _STEM_ZH[stem]
    if stem in _COMMON_COL_ZH:
        return _COMMON_COL_ZH[stem]
    return ""


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
        lab = tzh.get(base) or _INFRA_TABLE_ZH.get(base)
        if lab:
            return f"{lab}编号"
        stem = _stem_zh(base, czh)
        return f"{stem}编号" if stem else "关联编号"
    if name.endswith("_username") and len(name) > 9:
        stem = _stem_zh(name[:-9], czh) or "用户"
        return f"{stem}账号"
    if name.endswith("_name") and len(name) > 5:
        return _stem_zh(name[:-5], czh) or "名称"
    if name.endswith("_at"):
        stem = _stem_zh(name[:-3], czh)
        return f"{stem}时间" if stem else "时间"
    if name.endswith("_url"):
        stem = _stem_zh(name[:-4], czh)
        return f"{stem}链接" if stem else "链接"
    if name.endswith("_yuan"):
        return _stem_zh(name[:-5], czh) or "金额"
    if name.endswith("_msg"):
        stem = _stem_zh(name[:-4], czh)
        return f"{stem}说明" if stem else "说明"
    if name.endswith("_code"):
        stem = _stem_zh(name[:-5], czh)
        return f"{stem}码" if stem else "编码"
    if name.endswith("_json"):
        return _stem_zh(name[:-5], czh) or "资料"
    if name.endswith("_type"):
        stem = _stem_zh(name[:-5], czh)
        return f"{stem}类型" if stem else "类型"
    if name.startswith("super_"):
        return "总管"
    if name.endswith("_editable"):
        return "可改资料"
    return name


def _rel_zh(
    name: str,
    via: str,
    left: str,
    right: str,
    tzh: dict[str, str],
    rzh: dict[str, str],
) -> str:
    # 仅 verbs.apply（如 signup→报名）
    for cand in (right, name):
        if cand in rzh:
            return rzh[cand]
    if via == "username":
        return "归属"
    if name.endswith("_log") or right.endswith("_log"):
        return "记录"
    if name.endswith("_attach") or right.endswith("_attach"):
        return "附件"
    if left in _INFRA_TABLE_ZH or left == "category":
        lab = tzh.get(left) or _INFRA_TABLE_ZH.get(left)
        if lab:
            return lab
    for cand in (right, name, left):
        lab = tzh.get(cand)
        if lab:
            return lab.removesuffix("单") if lab.endswith("单") else lab
    if via.endswith("_id"):
        return "关联"
    return _table_zh(name, tzh)


def load_schema_model(workspace: Path) -> dict | None:
    path = workspace / "sql" / "schema.sql"
    if not path.exists():
        return None
    tzh, czh, tcols, rzh = _labels_from_domain_schema(workspace / "domain.schema.json")
    return schema_model(
        path.read_text(encoding="utf-8", errors="ignore"),
        extra_table_zh=tzh,
        extra_col_zh=czh,
        extra_table_cols=tcols,
        extra_rel_zh=rzh,
    )


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


def render_er_svg(model: dict, title: str = "E-R") -> str:
    tables = model.get("tables") or []
    relations = model.get("relations") or []
    if not tables:
        return _svg_wrap(480, 200, '<text x="24" y="100" font-size="14">无表结构</text>')

    # 标题去掉库名英文感：E-R · xxx → 实体联系图
    show_title = title
    if title.startswith("E-R"):
        show_title = "实体联系图" + (title[3:] if len(title) > 3 else "")

    names = [t["name"] for t in tables]
    edges = [(r["left"], r["right"]) for r in relations]
    order = _order_minimize_crossings(names, edges)
    by_name = {t["name"]: t for t in tables}
    ordered_tables = [by_name[n] for n in order if n in by_name]

    entity_hw: dict[str, float] = {
        t["name"]: _entity_hw(t.get("label") or t["name"]) for t in tables
    }
    clouds = {
        t["name"]: _attr_cloud_radius(
            t.get("core_columns") or t.get("columns") or [],
            entity_hw[t["name"]],
        )
        for t in tables
    }
    max_cloud = max(clouds.values()) if clouds else 80
    n = len(ordered_tables)
    if n <= 1:
        ring_r = 0.0
    else:
        pair_need = 2 * max_cloud + 120
        ring_r = pair_need / (2 * math.sin(math.pi / n))
        ring_r = max(ring_r, 280.0)

    margin = max_cloud + 140
    w = int(2 * (ring_r + margin) + 80)
    h = int(2 * (ring_r + margin) + 110)
    w, h = max(w, 960), max(h, 760)
    cx, cy = w / 2, h / 2 + 16

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

    # 联系：直线实体边 → 菱形边 → 实体边
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

    # 实体 + 属性
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

        attrs = t.get("core_columns") or t.get("columns") or []
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

    header = [
        f'<text class="er-title" x="24" y="28" font-family="Microsoft YaHei, SimSun, serif" font-size="16">'
        f"{_esc(show_title)}</text>",
        '<text class="er-legend" x="24" y="48" font-family="Microsoft YaHei, sans-serif" font-size="11" fill="#333">'
        "方框=实体 · 菱形=联系 · 椭圆=属性 · 下划线=主键 · 波浪线=外键 · 1 / n 为基数"
        "</text>",
    ]
    parts = (
        header
        + ['<g class="er-edges">']
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
