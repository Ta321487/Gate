"""终稿吸收：论文物理/逻辑库表章 → draft schema.sql（忠于原文、落库）。

真源：docs/thesis-absorb.md §3 P1-库表。
策略：写法多变、合同不变。
- L1 主矿：正文题注后字段行（类型词锚定切列）；材料里有而抽空 = 工厂漏挖。
- L2：pdfplumber 栅格仅补 L1 仍空的表。
- 逻辑段只供 COMMENT/告警；禁止拼音脑补表名、禁止无物理列造列。
"""

from __future__ import annotations

import re
from typing import Any

# 表号：4.1 / 4．1 / 4-1 / 4－1
_TABLE_NO = r"([0-9０-９]+(?:[.．\-—－][0-9０-９]+)?)"
# 表 4.1 用户表 yonghu（中文表+英文名，滤用例表）
_PHYS_CAPTION = re.compile(
    rf"表\s*{_TABLE_NO}\s*"
    r"([\u4e00-\u9fffA-Za-z0-9]{2,24}表)\s*"
    r"([A-Za-z_][A-Za-z0-9_]{0,63})",
)
# 表 4.1 ××表（无英文名形态；SQL 名用 t_表号 占位，禁拼音脑补）
_PHYS_CAPTION_ZH_ONLY = re.compile(
    rf"^表\s*{_TABLE_NO}\s*"
    r"([\u4e00-\u9fffA-Za-z0-9]{2,24}表)\s*$"
)
# 裸题注：4.18 评论表 en（PDF 常吞句首「表」；须下文仍像字段表才收）
_BARE_PHYS_CAPTION = re.compile(
    rf"^{_TABLE_NO}\s*"
    r"([\u4e00-\u9fffA-Za-z0-9]{2,24}表)\s*"
    r"([A-Za-z_][A-Za-z0-9_]{0,63})\s*$"
)
# 裸题注无英文：4.1 菜品信息表
_BARE_PHYS_CAPTION_ZH_ONLY = re.compile(
    rf"^{_TABLE_NO}\s*"
    r"([\u4e00-\u9fffA-Za-z0-9]{2,24}表)\s*$"
)
# 用户表（yonghu） / 表 4.1 用户表（yonghu）
_PHYS_PAREN_EN = re.compile(
    rf"(?:表\s*{_TABLE_NO}\s*)?"
    r"([\u4e00-\u9fff]{2,20}表)\s*[（(]\s*([A-Za-z_][A-Za-z0-9_]{0,63})\s*[)）]"
)
# （3）仓库管理员表cangkuguanliyuan / 仓库管理员表 cangkuguanliyuan（空格可无）
# （2）厂商changshang（偶发无「表」字）
_ENUM_PHYS = re.compile(
    r"[（(]\d+[)）]\s*"
    r"([\u4e00-\u9fff]{2,20}表?)\s*"
    r"([A-Za-z_][A-Za-z0-9_]{0,63})"
)
# 如表4.3所示 / 所\s*示折行 / 如表4.7¶所示
_SHOWN_REF = re.compile(
    rf"如\s*表\s*{_TABLE_NO}\s*所\s*示"
    rf"|如\s*表\s*{_TABLE_NO}(?=\s|$|[。．;；，,]|所)"
)
_NEXT_ENUM_TABLE = re.compile(
    r"^[（(]\d+[)）]\s*[\u4e00-\u9fffA-Za-z0-9]{2,20}表\b"
)
_CONT_TABLE = re.compile(rf"^续表\s*{_TABLE_NO}")
_FIELD_HEADER_LINE = re.compile(
    r"序号\s*(?:字段名称|字段名|属性名|列名|字段|属性)"
    r"|^(?:字段名称|字段名|属性名|列名|字段|属性)\s+(?:说明|类型|数据类型)"
)
# 逻辑：用户（用户 ID、创建时间、…）
_LOGIC_ENTITY = re.compile(
    r"([\u4e00-\u9fff]{2,16})"
    r"[（(]"
    r"([^）)]{4,400})"
    r"[）)]",
)

_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "name": (
        "字段名称",
        "字段名",
        "属性名",
        "列名",
        "字段",
        "属性",
        "name",
        "column",
    ),
    "label": ("说明", "含义", "注释", "描述", "中文名", "comment"),
    "type": ("数据类型", "数据类别", "类型", "type", "datatype"),
    "length": ("长度", "精度", "len", "length", "宽度"),
    "nullable": ("允许空", "可空", "是否为空", "isnull", "null"),
    "auto_inc": ("自增", "自动递增", "auto", "increment"),
    "key": ("主外键", "主键", "外键", "约束", "键", "key"),
    "seq": ("序号", "编号", "no"),
}

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TYPE_NAMES = (
    "varchar2",
    "longtext",
    "mediumtext",
    "tinytext",
    "longblob",
    "timestamp",
    "datetime",
    "varchar",
    "decimal",
    "numeric",
    "number",
    "tinyint",
    "smallint",
    "bigint",
    "integer",
    "double",
    "float",
    "boolean",
    "bool",
    "blob",
    "json",
    "text",
    "char",
    "date",
    "time",
    "int",
)
# 中文类型 → MySQL（形态同义，不按篇专线）
_ZH_TYPE_MAP = {
    "长文本": "longtext",
    "长整型": "bigint",
    "日期时间": "datetime",
    "字符串": "varchar",
    "字符型": "varchar",
    "浮点型": "double",
    "布尔型": "tinyint",
    "时间型": "datetime",
    "日期型": "date",
    "整型": "int",
    "整数": "int",
    "浮点": "double",
    "小数": "decimal",
    "布尔": "tinyint",
    "文本": "text",
}
# 英文类型须词界，避免 addtime 里误吃 time；中文类型整词
_TYPE_ANCHOR = re.compile(
    r"(?:"
    r"(?<![A-Za-z0-9_])("
    + "|".join(sorted(_TYPE_NAMES, key=len, reverse=True))
    + r")(?![A-Za-z0-9_])"
    r"|("
    + "|".join(sorted(_ZH_TYPE_MAP.keys(), key=len, reverse=True))
    + r")"
    r")\s*(?:\(\s*\d+(?:\s*,\s*\d+)?\s*\))?",
    re.I,
)
_SEQ_START = re.compile(r"^\d{1,3}\b")
_HEADER_HINT = re.compile(
    r"(?:字段名称|字段名|属性名|列名|字段|属性).{0,40}(?:数据类型|类型)"
    r"|(?:数据类型|类型).{0,40}(?:字段名称|字段名|属性名|列名|字段|属性)"
)
_NARRATIVE_SKIP = re.compile(
    r"^(?:说明|注|备注|其中|本表|用于|用来)[:：]|^(?:具体内容如表|如表\s*\d)"
)


def _norm_line(raw: str) -> str:
    return re.sub(r"[ \t]+", " ", (raw or "").strip())


def _norm_table_no(no: str) -> str:
    t = (no or "").strip()
    t = t.translate(str.maketrans("０１２３４５６７８９．", "0123456789."))
    t = re.sub(r"[\-—－]", ".", t)
    return t


def _zh_table_stem(zh: str) -> str:
    t = re.sub(r"\s+", "", zh or "")
    return t[:-1] if t.endswith("表") and len(t) > 2 else t


def _en_near_dup(a: str, b: str) -> bool:
    """英文表名近形：good/goods、截断/复数（PDF 题注常吞尾字母）。"""
    al = (a or "").strip().lower()
    bl = (b or "").strip().lower()
    if not al or not bl:
        return False
    if al == bl:
        return True
    if al + "s" == bl or bl + "s" == al:
        return True
    short, long = (al, bl) if len(al) <= len(bl) else (bl, al)
    # 短名≥3 且为长名前缀（good⊂goods）；禁止 o/or 这类过短误并
    return len(short) >= 3 and long.startswith(short)


def _prefer_en_name(a: str, b: str) -> str:
    """同表冲突时留更完整英文名（goods > good）。"""
    a = (a or "").strip()
    b = (b or "").strip()
    if not a:
        return b
    if not b:
        return a
    if len(b) > len(a):
        return b
    return a


def _looks_like_field_header(s: str) -> bool:
    t = re.sub(r"\s+", "", s or "")
    if not t:
        return False
    if _FIELD_HEADER_LINE.search(s or ""):
        return True
    if t.startswith("序号") and any(
        k in t for k in ("字段", "列名", "属性")
    ):
        return True
    return bool(_HEADER_HINT.search(s or ""))


def _cell_stream_header_at(lines: list[str], j: int) -> bool:
    """一格一行：本行是「序号」，随后短窗内出现字段+类型。"""
    s = _norm_line(lines[j] if j < len(lines) else "")
    if s not in ("序号", "编号") and s.lower() not in ("no", "seq"):
        return False
    window = [
        _norm_line(lines[k])
        for k in range(j, min(j + 12, len(lines)))
    ]
    flat = "".join(window)
    has_name = any(k in flat for k in ("字段", "属性名", "列名", "属性"))
    has_type = "数据类型" in flat or "类型" in flat
    return has_name and has_type


def _anchor_before_field_header(lines: list[str], from_li: int) -> int:
    """字段表上一行：所示/题注行；block 从 line_index+1 吃。"""
    end = min(from_li + 16, len(lines))
    for j in range(from_li, end):
        s = _norm_line(lines[j])
        nxt = _norm_line(lines[j + 1]) if j + 1 < len(lines) else ""
        if _looks_like_field_header(nxt) or _cell_stream_header_at(lines, j + 1):
            return j
        if _looks_like_field_header(s) or _cell_stream_header_at(lines, j):
            return max(0, j - 1)
    return from_li


def _field_table_ahead(lines: list[str], from_li: int, *, window: int = 24) -> bool:
    """下文是否仍像物理字段表（表头或类型锚定行）。引导词不对时的收录闸。"""
    end = min(max(0, from_li) + window, len(lines))
    for j in range(max(0, from_li), end):
        s = _norm_line(lines[j])
        if not s:
            continue
        if _looks_like_field_header(s) or _cell_stream_header_at(lines, j):
            return True
        if parse_anchored_field_line(s):
            return True
    return False


def _next_caption_line_index(
    captions: list[dict[str, Any]], start_li: int
) -> int | None:
    """按正文行号找下一题注（禁止按表号排序取 next → 空切）。"""
    later = [
        int(c.get("line_index") or -1)
        for c in captions
        if int(c.get("line_index") or -1) > start_li
    ]
    return min(later) if later else None


def _placeholder_en_from_no(no: str) -> str:
    """无英文题注时用表号占位（t_4_1）；禁止拼音脑补业务名。"""
    no_n = _norm_table_no(no)
    if not no_n:
        return ""
    safe = re.sub(r"[^0-9A-Za-z]+", "_", no_n).strip("_")
    return f"t_{safe}" if safe else ""


def parse_physical_captions(text: str) -> list[dict[str, Any]]:
    """物理题注 → [{no, zh, en, order, line_index}]。

    优先「中文表+英文名」；仅中文题注用 t_表号 占位（禁拼音脑补）。
    写法：同行题注 / 括号英文名 / 枚举+如表所示。
    禁止空「表 4.n所示」当题注。
    """
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    lines = (text or "").splitlines()

    def _merge_into(
        c: dict[str, Any], *, no: str, zh: str, en: str, anchor_from: int
    ) -> None:
        """把新证据并进已有题注（同表号 / 近形英文），不另开一张空表。"""
        new_li = _anchor_before_field_header(lines, anchor_from)
        if new_li >= int(c.get("line_index") or 0):
            c["line_index"] = new_li
        if no and not c.get("no"):
            c["no"] = _norm_table_no(no)
        preferred = _prefer_en_name(str(c.get("en") or ""), en)
        old_en = str(c.get("en") or "")
        # 真英文盖过 t_表号 占位
        if old_en.lower().startswith("t_") and en and not en.lower().startswith("t_"):
            preferred = en
        if preferred.lower() != old_en.lower():
            seen.discard(old_en.lower())
            seen.add(preferred.lower())
            c["en"] = preferred
        if zh and len(zh) > len(str(c.get("zh") or "")):
            c["zh"] = zh

    def _push(no: str, zh: str, en: str, anchor_from: int) -> None:
        en = (en or "").strip()
        zh = (zh or "").strip()
        if not zh:
            return
        if not en:
            en = _placeholder_en_from_no(no)
        if not en or en.lower() in seen:
            return
        if not _IDENT.match(en):
            return
        seen.add(en.lower())
        out.append(
            {
                "no": _norm_table_no(no),
                "zh": zh,
                "en": en,
                "order": len(out),
                "line_index": _anchor_before_field_header(lines, anchor_from),
            }
        )

    def _upgrade_or_push(no: str, zh: str, en: str, anchor_from: int) -> None:
        en = (en or "").strip()
        zh = (zh or "").strip()
        if not zh:
            return
        if not en:
            en = _placeholder_en_from_no(no)
        if not en or not _IDENT.match(en):
            return
        en_l = en.lower()
        no_n = _norm_table_no(no) if no else ""
        zh_stem = _zh_table_stem(zh)
        if en_l in seen:
            for c in out:
                if c["en"].lower() != en_l:
                    continue
                # 更明确的「表4.n …」行：上调锚点与表号
                _merge_into(c, no=no, zh=zh, en=en, anchor_from=anchor_from)
                break
            return
        # 同表号或同中文 + 近形英文（枚举 goods / 正式题注 good）→ 并一张，禁假漏挖
        for c in out:
            c_no = str(c.get("no") or "")
            same_no = bool(no_n) and bool(c_no) and no_n == c_no
            same_zh = bool(zh_stem) and _zh_table_stem(str(c.get("zh") or "")) == zh_stem
            if not (same_no or same_zh):
                continue
            if not (_en_near_dup(str(c.get("en") or ""), en) or same_no and same_zh):
                continue
            _merge_into(c, no=no, zh=zh, en=en, anchor_from=anchor_from)
            return
        _push(no, zh, en, anchor_from)

    for li, raw in enumerate(lines):
        line = _norm_line(raw)
        if not line:
            continue
        # 形态1：表 4.1 用户表 yonghu
        m = _PHYS_CAPTION.search(line)
        if m and not (
            "所示" in line
            and not re.search(
                rf"{re.escape(m.group(2))}\s*{re.escape(m.group(3))}", line
            )
        ):
            _upgrade_or_push(m.group(1), m.group(2), m.group(3), li)
            continue
        # 形态1z：表 4.1 菜品信息表（无英文）；拒测试/用例表
        zm = _PHYS_CAPTION_ZH_ONLY.match(line)
        if (
            zm
            and "所示" not in line
            and "用例" not in line
            and "测试" not in zm.group(2)
        ):
            _upgrade_or_push(zm.group(1), zm.group(2), "", li)
            continue
        # 形态1c：裸 4.18 评论表 en——引导词缺「表」；下文仍像字段表才收
        bm = _BARE_PHYS_CAPTION.match(line)
        if bm:
            if _field_table_ahead(lines, li + 1):
                _upgrade_or_push(bm.group(1), bm.group(2), bm.group(3), li)
            continue
        bzm = _BARE_PHYS_CAPTION_ZH_ONLY.match(line)
        if bzm and "用例" not in line and "测试" not in bzm.group(2):
            if _field_table_ahead(lines, li + 1):
                _upgrade_or_push(bzm.group(1), bzm.group(2), "", li)
            continue
        # 形态1b：用户表（yonghu）
        pm = _PHYS_PAREN_EN.search(line)
        if pm and "用例" not in line:
            _upgrade_or_push(pm.group(1) or "", pm.group(2), pm.group(3), li)
            continue
        # 形态2：枚举 + 如表 x.y所示（可跨行；表名与英文可粘连）
        em = _ENUM_PHYS.search(line)
        if not em:
            continue
        # 误吞流程步骤：须附近有「如表…所示」或「信息存储在该表」
        blob = " ".join(
            _norm_line(lines[j]) for j in range(li, min(li + 5, len(lines)))
        )
        sm = _SHOWN_REF.search(blob)
        if not sm and "该表" not in blob and "存储" not in line:
            continue
        no = ""
        if sm:
            no = next((g for g in sm.groups() if g), "") or ""
        zh = em.group(1)
        if zh and not zh.endswith("表"):
            zh = zh + "表"
        # 引导词折烂仍可收：已采到表号，或下文仍像字段表
        if no or _field_table_ahead(lines, li + 1):
            _upgrade_or_push(no, zh, em.group(2), li)

    def _sort_key(c: dict[str, Any]) -> tuple:
        no = str(c.get("no") or "")
        parts = re.findall(r"\d+", no)
        nums = tuple(int(x) for x in parts[:3]) if parts else (999,)
        return (*nums, int(c.get("line_index") or 0))

    out.sort(key=_sort_key)
    for i, c in enumerate(out):
        c["order"] = i
    return out


def parse_logical_entities(text: str) -> dict[str, list[str]]:
    """逻辑结构：实体名 → 属性中文列表（仅交叉，不造列）。"""
    out: dict[str, list[str]] = {}
    body = text or ""
    slice_m = re.search(
        r"(?:逻辑结构|逻辑设计|概念结构).{0,80}",
        body,
    )
    scan = body[slice_m.start() :] if slice_m else body
    scan = scan[:12000]
    for m in _LOGIC_ENTITY.finditer(scan):
        name = (m.group(1) or "").strip()
        if name.endswith("表"):
            name = name[:-1]
        if name in ("如下所示", "如图所示", "数据库", "本系统") or len(name) < 2:
            continue
        attrs = [
            re.sub(r"\s+", "", a).strip()
            for a in re.split(r"[、，,;；]", m.group(2) or "")
            if re.sub(r"\s+", "", a).strip()
        ]
        attrs = [a for a in attrs if 1 < len(a) <= 24]
        if len(attrs) < 2:
            continue
        if name not in out or len(attrs) > len(out[name]):
            out[name] = attrs
    return out


def _norm_header_cell(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip()).lower()


def _map_header(row: list[str]) -> dict[str, int] | None:
    """表头 → 角色列下标；至少要有列名 + 类型。"""
    cells = [_norm_header_cell(c) for c in row]
    if not any(cells):
        return None
    idx: dict[str, int] = {}
    for i, cell in enumerate(cells):
        if not cell:
            continue
        for role, aliases in _HEADER_ALIASES.items():
            if role in idx:
                continue
            if any(a.lower() in cell or cell == a.lower() for a in aliases):
                # 「空」太短易误伤，只认整格
                if aliases == ("允许空", "可空", "null") and cell in ("空",):
                    continue
                idx[role] = i
                break
    if "name" not in idx or "type" not in idx:
        return None
    return idx


def _yn_true(s: str) -> bool:
    t = re.sub(r"\s+", "", (s or "").strip())
    if not t:
        return False
    tu = t.upper()
    if t in ("×", "x", "X", "否", "N", "n", "false", "0", "-", "—") or tu in (
        "NO",
        "NULL",
    ):
        return False
    if t in ("√", "✓", "是", "Y", "y", "true", "1", "允许", "可") or tu in (
        "YES",
        "NOTNULL",
    ):
        return True
    if "NOTNULL" in tu.replace(" ", "") or "NOT_NULL" in tu:
        return False  # 允许空? → 否
    return "√" in t or "✓" in t


def _parse_key_cell(s: str) -> tuple[bool, bool]:
    t = (s or "").strip()
    tu = t.upper()
    pk = "主键" in t or tu in ("PK", "PRI") or "PRI" in tu.split()
    fk = "外键" in t or tu in ("FK", "MUL") or "MUL" in tu.split()
    return pk, fk


def _normalize_type_token(raw: str) -> tuple[str | None, str]:
    """类型锚 → (mysql_base, inline_length)。认不出 base 则 (None, '')."""
    s = re.sub(r"\s+", "", (raw or "").strip())
    if not s:
        return None, ""
    m = re.match(r"^(.+?)(?:\((\d+(?:,\d+)?)\))?$", s, re.I)
    if not m:
        return None, ""
    base = m.group(1)
    inline_len = m.group(2) or ""
    bl = base.lower()
    # 中文
    for zh, en in sorted(_ZH_TYPE_MAP.items(), key=lambda x: -len(x[0])):
        if base == zh or bl == zh:
            return en, inline_len
    if bl == "varchar2":
        return "varchar", inline_len
    if bl == "number":
        return "decimal", inline_len
    if bl == "integer":
        return "int", inline_len
    if bl in ("bool", "boolean"):
        return "tinyint", inline_len
    if bl in {x.lower() for x in _TYPE_NAMES}:
        return bl, inline_len
    return None, ""


def _compose_type(base: str, length: str) -> str | None:
    b, inline = _normalize_type_token(base)
    if not b:
        return None
    ln = re.sub(r"\s+", "", (length or "").strip())
    # 「默认」是空长度占位，勿盖掉类型括号里的 inline（如 decimal(10,2)）
    if not ln or ln in ("默认", "缺省", "-", "—", "－"):
        ln = inline
    if ln and re.match(r"^\d+(,\d+)?$", ln):
        if b in ("varchar", "char", "decimal", "numeric"):
            return f"{b}({ln})"
    return b


def parse_field_table_rows(rows: list[list[str]]) -> list[dict[str, Any]]:
    """八列/变体字段表（plumber）→ columns；认不出表头返回 []。"""
    if not rows or len(rows) < 2:
        return []
    header_i = 0
    mapping = _map_header(rows[0])
    if mapping is None and len(rows) > 2:
        mapping = _map_header(rows[1])
        header_i = 1
    if mapping is None:
        return []
    cols: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in rows[header_i + 1 :]:
        if not raw:
            continue

        def _cell(role: str) -> str:
            i = mapping.get(role)
            if i is None or i >= len(raw):
                return ""
            return str(raw[i] or "").strip()

        name = re.sub(r"\s+", "", _cell("name"))
        if not name or not _IDENT.match(name):
            continue
        if name.lower() in seen:
            continue
        typ = _compose_type(_cell("type"), _cell("length"))
        if not typ:
            continue
        pk, fk = _parse_key_cell(_cell("key"))
        nullable_raw = _cell("nullable")
        if nullable_raw:
            nullable = _yn_true(nullable_raw)
        else:
            nullable = not pk
        auto_inc = _yn_true(_cell("auto_inc")) if "auto_inc" in mapping else False
        label = re.sub(r"\s+", " ", _cell("label")).strip() or name
        seen.add(name.lower())
        cols.append(
            {
                "name": name,
                "label": label[:64],
                "type": typ,
                "nullable": nullable and not pk,
                "pk": pk,
                "fk": fk,
                "auto_increment": auto_inc,
                "raw": " ".join(str(x) for x in raw if x),
            }
        )
    return cols


def is_field_definition_table(rows: list[list[str]]) -> bool:
    return _map_header((rows or [None])[0] or []) is not None or (
        len(rows or []) > 1 and _map_header(rows[1]) is not None
    )


def _split_name_label(left: str) -> tuple[str, str] | None:
    """类型锚左侧 → (en_name, label)。支持：序号+en、序号+中文+en、无序号+en。"""
    s = (left or "").strip()
    if not s:
        return None
    # 先认 en 在前（力固常见：1 yonghu_id 用户 ID）——避免「用户 ID」尾词被当成列名
    m = re.match(
        r"^(\d{1,3})\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$",
        s,
    )
    if m:
        lab = re.sub(r"\s+", " ", (m.group(3) or "").strip()) or m.group(2)
        return m.group(2), lab
    # 1 用户编号 user_id（中文说明在前，须含汉字）
    m = re.match(
        r"^(\d{1,3})\s+(.+?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*$",
        s,
    )
    if m and re.search(r"[\u4e00-\u9fff]", m.group(2)):
        return m.group(3), re.sub(r"\s+", " ", m.group(2)).strip()
    # 中文说明 + en（无序号）：评价 ID pingjia_id
    m = re.match(r"^(.+?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", s)
    if m and re.search(r"[\u4e00-\u9fff]", m.group(1)):
        return m.group(2), re.sub(r"\s+", " ", m.group(1)).strip()
    # user_id 用户编号（无序号）
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$", s)
    if m:
        lab = re.sub(r"\s+", " ", (m.group(2) or "").strip()) or m.group(1)
        return m.group(1), lab
    return None


def _parse_flags_tail(tail: str, *, pk_hint: bool) -> tuple[bool, bool, bool, bool]:
    """→ pk, fk, auto_inc, nullable。"""
    pk, fk = _parse_key_cell(tail)
    pk = pk or pk_hint
    auto_inc = False
    nullable = not pk
    # 三列是/否：按「主键·外键·非空」读（末列非空 ≠ 允许空）
    zh_marks = re.findall(r"是|否", tail or "")
    if len(zh_marks) >= 3 and not re.search(r"[√✓×]|主键|外键|允许空", tail or ""):
        pk = zh_marks[0] == "是" or pk
        fk = zh_marks[1] == "是" or fk
        nullable = zh_marks[2] == "否"
        return pk, fk, auto_inc, nullable
    # Y/N 与勾叉
    marks = re.findall(r"[√✓×]|YES|NO|[YyNn](?![A-Za-z])", tail, re.I)
    if marks:
        auto_inc = _yn_true(marks[0])
        if len(marks) >= 2:
            nullable = _yn_true(marks[-1])
    if re.search(r"NOT\s*NULL", tail, re.I):
        nullable = False
    elif re.search(r"(?<![A-Za-z])NULL(?![A-Za-z])", tail, re.I) and "NOT" not in tail.upper():
        nullable = True
    return pk, fk, auto_inc, nullable


def parse_anchored_field_line(line: str) -> dict[str, Any] | None:
    """类型词锚定切列：禁纯空格切八列；兼中文类型/括号长度/无序号行。"""
    s = re.sub(r"[ \t]+", " ", (line or "").strip())
    if not s or _NARRATIVE_SKIP.search(s):
        return None
    tm = _TYPE_ANCHOR.search(s)
    if not tm:
        return None
    left = s[: tm.start()].strip()
    typ_raw = tm.group(0)
    right = s[tm.end() :].strip()
    split = _split_name_label(left)
    if not split:
        return None
    name, label = split
    tokens = right.split()
    length = ""
    if tokens:
        tok0 = tokens[0].rstrip(",")
        if tok0 in ("默认", "缺省", "-", "—", "－") or re.match(
            r"^\d+(,\d+)?$", tok0
        ):
            length = tok0
            tokens = tokens[1:]
        elif tok0.upper() in ("YES", "NO", "Y", "N", "PRI", "MUL", "PK", "FK"):
            pass
    typ = _compose_type(typ_raw, length)
    if not typ:
        return None
    tail = " ".join(tokens)
    pk, fk, auto_inc, nullable = _parse_flags_tail(tail, pk_hint=False)
    return {
        "name": name,
        "label": (label or name)[:64],
        "type": typ,
        "nullable": nullable and not pk,
        "pk": pk,
        "fk": fk,
        "auto_increment": auto_inc,
        "raw": s,
    }


def _is_header_line(s: str) -> bool:
    return _looks_like_field_header(s)


def _glue_block_lines(raw_lines: list[str]) -> list[str]:
    """表头/数据折行捏合。"""
    lines = [re.sub(r"[ \t]+", " ", (ln or "").strip()) for ln in raw_lines]
    lines = [ln for ln in lines if ln and not _NARRATIVE_SKIP.search(ln)]
    if not lines:
        return []
    glued: list[str] = []
    buf = ""
    header_done = False
    name_keys = ("字段名称", "字段名", "属性名", "列名", "字段", "属性")
    for ln in lines:
        if not header_done:
            buf = f"{buf}{ln}" if not buf else f"{buf}{ln}"
            flat = re.sub(r"\s+", "", buf)
            has_name = any(k in flat for k in name_keys)
            has_type = "数据类型" in flat or "类型" in flat
            has_tail = any(
                k in flat for k in ("允许空", "可空", "主外键", "主键", "是否为空", "约束")
            )
            if has_name and has_type and (has_tail or len(flat) >= 12):
                glued.append(buf)
                buf = ""
                header_done = True
            continue
        # 新数据行：整行已能锚定切列（含无序号「中文 + en + 类型」）
        fresh = parse_anchored_field_line(ln) is not None
        if fresh:
            if buf:
                glued.append(buf)
            buf = ln
        else:
            buf = f"{buf} {ln}".strip() if buf else ln
    if buf:
        glued.append(buf)
    return glued


def _block_lines_for_caption(
    all_lines: list[str],
    start_li: int,
    next_li: int | None,
    *,
    self_en: str = "",
    self_no: str = "",
) -> list[str]:
    end = next_li if next_li is not None else len(all_lines)
    self_en_l = (self_en or "").strip().lower()
    self_no_n = _norm_table_no(self_no) if self_no else ""

    def _is_same_table_caption(flat: str) -> bool:
        m = _PHYS_CAPTION.search(flat) or _BARE_PHYS_CAPTION.match(flat)
        if m:
            if self_en_l and m.group(3).lower() == self_en_l:
                return True
            if self_no_n and _norm_table_no(m.group(1)) == self_no_n:
                return True
        pm = _PHYS_PAREN_EN.search(flat)
        if pm and self_en_l and pm.group(3).lower() == self_en_l:
            return True
        return False

    def _is_other_table_caption(flat: str) -> bool:
        if _PHYS_CAPTION.search(flat) or _PHYS_PAREN_EN.search(flat):
            return not _is_same_table_caption(flat)
        if _BARE_PHYS_CAPTION.match(flat):
            return not _is_same_table_caption(flat)
        return False

    # 下一块前若夹「续表」，并入本块（同表续页）
    if next_li is not None:
        for j in range(next_li, min(next_li + 3, len(all_lines))):
            if _CONT_TABLE.match(_norm_line(all_lines[j])):
                # 延到下一真正题注前
                end = len(all_lines)
                for k in range(j + 1, len(all_lines)):
                    nk = _norm_line(all_lines[k])
                    if (
                        _PHYS_CAPTION.search(nk)
                        or _PHYS_PAREN_EN.search(nk)
                        or _BARE_PHYS_CAPTION.match(nk)
                        or _NEXT_ENUM_TABLE.match(nk)
                    ):
                        if _is_same_table_caption(nk):
                            continue
                        end = k
                        break
                break
    chunk: list[str] = []
    for ln in all_lines[start_li + 1 : end]:
        s = (ln or "").strip()
        if not s:
            if chunk:
                # 空行不立刻截断：续表前常空一行
                continue
            continue
        flat = re.sub(r"[ \t]+", " ", s)
        if _CONT_TABLE.match(flat):
            continue
        if _is_other_table_caption(flat):
            break
        if _is_same_table_caption(flat):
            continue  # 枚举后再写「表4.n / 裸4.n …」——同表，勿截断
        if _NEXT_ENUM_TABLE.match(s):
            break
        if _NARRATIVE_SKIP.search(s) or re.match(r"^具体内容如表|^如表\s*\d", s):
            continue
        chunk.append(s)
        if len(chunk) > 120:
            break
    return chunk


def _is_stream_break_token(tok: str) -> bool:
    s = (tok or "").strip()
    if not s:
        return True
    if _CONT_TABLE.match(s) or _NEXT_ENUM_TABLE.match(s):
        return True
    if _PHYS_CAPTION.search(s) or _PHYS_PAREN_EN.search(s):
        return True
    if "如表" in s or s.startswith("具体内容如表"):
        return True
    if len(s) >= 36 and re.search(r"[\u4e00-\u9fff]{4,}", s) and not _IDENT.match(s):
        # 段首叙述（一格一行里偶发整句）
        return True
    return False


def _merge_split_header_tokens(tokens: list[str]) -> list[str]:
    """一格一行时表头常拆：主外|键 → 主外键。"""
    pairs = (
        ("主外", "键", "主外键"),
        ("自", "增", "自增"),
        ("允许", "空", "允许空"),
        ("数据", "类型", "数据类型"),
        ("字段", "名称", "字段名称"),
        ("字段", "名", "字段名"),
        ("属性", "名", "属性名"),
    )
    out: list[str] = []
    i = 0
    while i < len(tokens):
        merged = False
        for a, b, c in pairs:
            if i + 1 < len(tokens) and tokens[i] == a and tokens[i + 1] == b:
                out.append(c)
                i += 2
                merged = True
                break
        if not merged:
            out.append(tokens[i])
            i += 1
    return out


def _mine_cell_stream(block_lines: list[str]) -> list[dict[str, Any]]:
    """PyMuPDF 常见：字段表一格一行。按表头宽度切成行再走八列解析。"""
    tokens = [(ln or "").strip() for ln in block_lines if (ln or "").strip()]
    tokens = _merge_split_header_tokens(tokens)
    if len(tokens) < 16:
        return []
    short = sum(1 for t in tokens if len(t) <= 28)
    if short < len(tokens) * 0.65:
        return []
    header_row: list[str] | None = None
    header_i = -1
    header_w = 0
    best_roles = 0
    for i, t in enumerate(tokens[:50]):
        if t not in ("序号", "编号") and t.lower() not in ("no", "seq"):
            continue
        for width in range(6, 12):
            window = tokens[i : i + width]
            if len(window) < width:
                break
            if any(_is_stream_break_token(x) for x in window):
                continue
            mapping = _map_header(window)
            if not mapping:
                continue
            roles = len(mapping)
            if roles > best_roles:
                best_roles = roles
                header_row = list(window)
                header_i = i
                header_w = width
        if header_row is not None and best_roles >= 4:
            break
    if not header_row or header_w < 6:
        return []
    data = tokens[header_i + header_w :]
    rows: list[list[str]] = [header_row]
    i = 0
    while i + header_w <= len(data):
        if _is_stream_break_token(data[i]):
            break
        chunk = data[i : i + header_w]
        # 行首须像序号或列名；否则多半已出表
        head = chunk[0]
        if not (_SEQ_START.match(head) or _IDENT.match(head)):
            break
        if any(_is_stream_break_token(x) for x in chunk):
            break
        rows.append(chunk)
        i += header_w
        if len(rows) > 80:
            break
    cols = parse_field_table_rows(rows)
    return cols


def mine_columns_from_text_block(block_lines: list[str]) -> list[dict[str, Any]]:
    """L1：一块正文 → columns（TSV → 一格一行流 → 类型锚切行）。"""
    raw = [(ln or "").rstrip() for ln in block_lines if (ln or "").strip()]
    if not raw:
        return []
    # 制表符栅格
    if sum(1 for ln in raw if "\t" in ln) >= 2:
        rows = [[c.strip() for c in ln.split("\t")] for ln in raw if "\t" in ln]
        cols = parse_field_table_rows(rows)
        if cols:
            return cols
    # PDF 一格一行（力固/冠清/小羽正文常见）
    cols = _mine_cell_stream(raw)
    if cols:
        return cols
    glued = _glue_block_lines(raw)
    if not glued:
        return []
    data_lines = glued
    if data_lines and _is_header_line(data_lines[0]):
        data_lines = data_lines[1:]
    cols = []
    seen: set[str] = set()
    for ln in data_lines:
        col = parse_anchored_field_line(ln)
        if not col:
            continue
        key = col["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        cols.append(col)
    return cols


def mine_tables_l1(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """L1 主矿：题注就近正文块。"""
    warnings: list[str] = []
    captions = parse_physical_captions(text or "")
    if not captions:
        warnings.append("缺物理表题注（表4.n 中文表[ eng]），未收 schema")
        return [], warnings
    lines = (text or "").splitlines()
    tables: list[dict[str, Any]] = []
    for cap in captions:
        start_li = int(cap["line_index"])
        # 下一题注按正文行号，不按表号排序后的 i+1（力固评论表空切）
        next_li = _next_caption_line_index(captions, start_li)
        block = _block_lines_for_caption(
            lines,
            start_li,
            next_li,
            self_en=str(cap.get("en") or ""),
            self_no=str(cap.get("no") or ""),
        )
        cols = mine_columns_from_text_block(block)
        item: dict[str, Any] = {
            "name": cap["en"],
            "label": cap["zh"],
            "no": cap.get("no") or "",
            "columns": cols,
            "source": "l1_text",
        }
        if not cols:
            item["skipped"] = "l1_no_columns"
            warnings.append(
                f"题注 {cap['zh']} {cap['en']} 正文块未切出字段列（工厂漏挖或折行未捏合）"
            )
        tables.append(item)
    return tables, warnings


def _plumber_field_tables(
    plumber_tables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in plumber_tables or []:
        rows = t.get("rows") if isinstance(t, dict) else None
        if not isinstance(rows, list):
            continue
        mapped = _map_header(rows[0]) if rows else None
        if mapped is None and len(rows) > 1:
            mapped = _map_header(rows[1])
        if mapped is None:
            continue
        cols = parse_field_table_rows(rows)
        if not cols:
            continue
        out.append({"page": t.get("page"), "columns": cols})
    return out


def merge_l2_plumber(
    tables: list[dict[str, Any]],
    plumber_tables: list[dict[str, Any]],
) -> list[str]:
    """L2：仅补 L1 仍空的表（顺序对齐剩余栅格）；不覆盖已有列。"""
    warnings: list[str] = []
    field_tabs = _plumber_field_tables(plumber_tables)
    if not field_tabs:
        return warnings
    empties = [t for t in tables if not (t.get("columns") or [])]
    if not empties:
        return warnings
    n = min(len(empties), len(field_tabs))
    for i in range(n):
        empties[i]["columns"] = field_tabs[i]["columns"]
        empties[i]["source"] = "l2_plumber"
        empties[i].pop("skipped", None)
        warnings.append(
            f"{empties[i].get('label')} {empties[i].get('name')} 由 pdfplumber 补列"
        )
    return warnings


def bind_captions_to_tables(
    captions: list[dict[str, Any]],
    plumber_tables: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """兼容旧调用：无正文时退回 plumber 补空（不推荐作主路径）。"""
    warnings: list[str] = []
    if not captions:
        warnings.append("缺物理表题注（表4.n 中文表[ eng]），未收 schema")
        return [], warnings
    tables = [
        {
            "name": c["en"],
            "label": c["zh"],
            "no": c.get("no") or "",
            "columns": [],
            "skipped": "no_field_table",
        }
        for c in captions
    ]
    warnings.extend(merge_l2_plumber(tables, plumber_tables))
    if not any(t.get("columns") for t in tables):
        warnings.append("有物理题注但未抽出字段表（正文/pdfplumber），未写列")
    return tables, warnings


def _apply_logical_comments(
    tables: list[dict[str, Any]],
    logical: dict[str, list[str]],
) -> list[str]:
    """用逻辑属性名补空 COMMENT；不增列。"""
    warnings: list[str] = []
    for t in tables:
        zh = str(t.get("label") or "")
        stem = zh[:-1] if zh.endswith("表") else zh
        attrs = logical.get(stem) or logical.get(zh) or []
        if not attrs:
            continue
        cols = t.get("columns") or []
        if not cols:
            continue
        for i, c in enumerate(cols):
            if not isinstance(c, dict):
                continue
            if c.get("label") and c["label"] != c.get("name"):
                continue
            if i < len(attrs):
                c["label"] = attrs[i][:64]
    return warnings


def render_schema_sql(tables: list[dict[str, Any]]) -> str:
    """只渲染有列的表；规范化换行，同材同果。"""
    chunks: list[str] = [
        "-- draft schema.sql · 终稿吸收（忠于论文物理表，禁止脑补）",
        "-- 来源：factory_thesis_absorb.draft_schema_sql",
        "",
    ]
    any_table = False
    for t in tables:
        name = str(t.get("name") or "").strip()
        cols = [c for c in (t.get("columns") or []) if isinstance(c, dict) and c.get("name")]
        if not name or not cols:
            continue
        any_table = True
        zh = str(t.get("label") or name)
        no = str(t.get("no") or "")
        head = f"-- {zh} `{name}`"
        if no:
            head += f"（论文表 {no}）"
        chunks.append(head)
        lines: list[str] = []
        pks: list[str] = []
        for c in cols:
            cname = c["name"]
            typ = c["type"]
            parts = [f"  `{cname}` {typ}"]
            if c.get("auto_increment"):
                parts.append("AUTO_INCREMENT")
            if c.get("pk") or not c.get("nullable", True):
                parts.append("NOT NULL")
            else:
                parts.append("NULL")
            lab = str(c.get("label") or "").replace("'", "")
            if lab:
                parts.append(f"COMMENT '{lab}'")
            lines.append(" ".join(parts))
            if c.get("pk"):
                pks.append(cname)
        if pks:
            lines.append(f"  PRIMARY KEY (`{'`,`'.join(pks)}`)")
        body = ",\n".join(lines)
        comment = zh.replace("'", "")
        chunks.append(
            f"CREATE TABLE IF NOT EXISTS `{name}` (\n{body}\n"
            f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{comment}';"
        )
        chunks.append("")
    if not any_table:
        return ""
    return "\n".join(chunks).rstrip() + "\n"


def assert_schema_homology(
    sql: str,
    tables: list[dict[str, Any]],
) -> None:
    """SQL 中每张表/每列 ⊆ 证据；禁止脑补。"""
    if not (sql or "").strip():
        return
    evidence: dict[str, set[str]] = {}
    for t in tables:
        name = str(t.get("name") or "").strip().lower()
        if not name:
            continue
        evidence[name] = {
            str(c.get("name") or "").strip().lower()
            for c in (t.get("columns") or [])
            if isinstance(c, dict) and c.get("name")
        }
    for m in re.finditer(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?",
        sql,
        re.I,
    ):
        tname = m.group(1).lower()
        if tname not in evidence:
            raise AssertionError(f"sql invents table not in evidence: {tname}")
        start = m.end()
        # 非贪婪：勿把后续表体吞进当前表
        body_m = re.search(r"\((.*?)\)\s*ENGINE", sql[start:], re.I | re.S)
        if not body_m:
            continue
        body = body_m.group(1)
        for cm in re.finditer(r"`(\w+)`\s+[A-Za-z]", body):
            col = cm.group(1).lower()
            if col == "primary":
                continue
            if col not in evidence[tname]:
                raise AssertionError(
                    f"sql invents column {tname}.{col} not in evidence"
                )


def extract_draft_schema(
    text: str,
    *,
    plumber_tables: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """L1 正文主矿 + L2 plumber 补空 → draft_schema_sql + meta。"""
    logical = parse_logical_entities(text or "")
    tables, warnings = mine_tables_l1(text or "")
    warnings.extend(merge_l2_plumber(tables, plumber_tables or []))
    if not tables:
        # 无题注时保持空
        pass
    elif not any(t.get("columns") for t in tables):
        if not any("未抽出字段表" in w or "漏挖" in w for w in warnings):
            warnings.append("有物理题注但正文/pdfplumber 均未切出字段列")
    warnings.extend(_apply_logical_comments(tables, logical))
    with_cols = [t for t in tables if t.get("columns")]
    skipped = [
        {"name": t.get("name"), "reason": t.get("skipped") or "no_columns"}
        for t in tables
        if not t.get("columns")
    ]
    sql = render_schema_sql(tables)
    homology_ok = True
    try:
        assert_schema_homology(sql, tables)
    except AssertionError as e:
        homology_ok = False
        warnings.append(f"同源闸：{e}")
        sql = ""
    # 假绿：有题注却 0 CREATE 必须带黄条
    captions_n = len(parse_physical_captions(text or ""))
    if captions_n and not with_cols and not warnings:
        warnings.append("物理题注在、字段列为空（工厂漏挖）")
    meta = {
        "caption_count": captions_n,
        "table_count": len(with_cols),
        "skipped": skipped,
        "warnings": warnings,
        "homology_ok": homology_ok,
        "table_names": [t["name"] for t in with_cols],
        # 中文题注：供 §3.0b 表↔模块对账（含尚无列的题注表）
        "table_labels": [
            str(t.get("label") or "").strip()
            for t in tables
            if str(t.get("label") or "").strip()
        ],
        "mine": "l1_text",
    }
    return {
        "draft_schema_sql": sql,
        "schema_extract_meta": meta,
        "physical_tables": tables,
    }
