"""E-R 中文标签、角色展开与 LLM 补丁。

词表见 er_zh；本模块保留拼装与补丁逻辑。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.bake.schema.er_zh import (  # noqa: F401
    _COL_SUFFIX_RULES,
    _COMMON_COL_ZH,
    _INFRA_TABLE_ZH,
    _STEM_ZH,
    _TABLE_PART_ZH,
)

_LATIN_RE = re.compile(r"[A-Za-z]")
_ER_LABELS_REL = Path("islands") / "er_labels.json"


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
            "sys_guestbook": "发表",
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
            "sys_guestbook",
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
