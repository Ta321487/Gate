"""Island 填岛 sanitize（LLM 执行已迁至 app.llm.unit_flow）。"""

from __future__ import annotations

from typing import Any

from app.llm.agents_common import _LABEL_KEYS, _SEED_KEYS, _ROLE_LABEL_SLOTS


def _sanitize_island_roles(data: dict[str, Any], base_roles: dict) -> dict[str, Any] | None:
    """只允许改已有角色/岗位的中文 label（开题原样）；禁止增删 id、改 kind/packs。"""
    if not isinstance(base_roles, dict) or not base_roles:
        return None
    src = data.get("roles") if isinstance(data.get("roles"), dict) else {}
    if not src:
        return None
    out: dict[str, Any] = {}
    for rid in _ROLE_LABEL_SLOTS:
        base_slot = base_roles.get(rid)
        if not isinstance(base_slot, dict):
            continue
        piece = src.get(rid) if isinstance(src.get(rid), dict) else None
        lab = None
        if piece and piece.get("label"):
            lab = str(piece["label"]).strip()[:24]
        elif isinstance(src.get(rid), str):
            lab = str(src[rid]).strip()[:24]
        if not lab:
            continue
        out[rid] = {
            **base_slot,
            "id": base_slot.get("id") or rid,
            "label": lab,
        }

    base_posts = base_roles.get("staff_posts")
    src_posts = src.get("staff_posts")
    if isinstance(base_posts, list) and base_posts and isinstance(src_posts, list):
        by_id = {
            str(p.get("id")): str(p.get("label") or "").strip()[:24]
            for p in src_posts
            if isinstance(p, dict) and p.get("id") and p.get("label")
        }
        if by_id:
            merged_posts = []
            changed = False
            for p in base_posts:
                if not isinstance(p, dict) or not p.get("id"):
                    continue
                row = dict(p)
                pid = str(p["id"])
                if pid in by_id and by_id[pid] and by_id[pid] != str(p.get("label") or ""):
                    row["label"] = by_id[pid]
                    changed = True
                merged_posts.append(row)
            if changed:
                out["staff_posts"] = merged_posts
                clerks = [p for p in merged_posts if p.get("kind") == "clerk"]
                if clerks and isinstance(base_roles.get("subadmin"), dict):
                    out["subadmin"] = {
                        **(out.get("subadmin") or base_roles["subadmin"]),
                        "id": "subadmin",
                        "label": clerks[0].get("label") or base_roles["subadmin"].get("label"),
                        "staffPostId": clerks[0].get("id"),
                    }
    return out or None


def _sanitize_island_patch(
    data: dict[str, Any],
    base_labels: dict,
    base_seeds: dict,
    base_roles: dict | None = None,
) -> dict[str, Any]:
    labels: dict[str, Any] = {}
    src_l = data.get("labels") if isinstance(data.get("labels"), dict) else data
    for k in _LABEL_KEYS:
        if k in src_l and src_l[k] is not None:
            v = src_l[k]
            if k == "authPoints" and isinstance(v, list):
                labels[k] = [str(x)[:40] for x in v[:6]]
            else:
                text = str(v)[:200]
                if k == "authLead":
                    from app.bake.domain_schema import ui_copy_polluted

                    if ui_copy_polluted(text):
                        continue
                labels[k] = text
    if not labels.get("noticePageTitle") and base_labels.get("noticePageTitle"):
        labels["noticePageTitle"] = base_labels["noticePageTitle"]
    seeds: dict[str, Any] = {}
    src_s = data.get("seeds") if isinstance(data.get("seeds"), dict) else {}
    for k in _SEED_KEYS:
        if k in src_s and src_s[k] is not None:
            seeds[k] = str(src_s[k])[:500]
        elif k in data and isinstance(data.get(k), str):
            seeds[k] = str(data[k])[:500]
    if not seeds.get("noticeTitle") and base_seeds.get("noticeTitle"):
        seeds["noticeTitle"] = base_seeds["noticeTitle"]
    entities_out: dict[str, Any] = {}
    ents = data.get("entities") if isinstance(data.get("entities"), dict) else {}
    for ek, ev in ents.items():
        if not isinstance(ev, dict):
            continue
        piece: dict[str, Any] = {}
        if ev.get("label"):
            lab = str(ev["label"])[:40].strip()
            if ek in ("reservation", "ticket") and lab.endswith("记录") and len(lab) > 2:
                lab = lab.removesuffix("记录").strip() or lab
            piece["label"] = lab
        if ev.get("labelPlural"):
            piece["labelPlural"] = str(ev["labelPlural"])[:40]
        if isinstance(ev.get("verbs"), dict):
            piece["verbs"] = {str(k): str(v)[:40] for k, v in list(ev["verbs"].items())[:12]}
        if isinstance(ev.get("states"), dict):
            piece["states"] = {str(k): str(v)[:40] for k, v in list(ev["states"].items())[:12]}
        if piece:
            entities_out[ek] = piece
    patch: dict[str, Any] = {"mode": "unit_flow", "labels": labels, "seeds": seeds}
    if entities_out:
        patch["entities"] = entities_out
    roles_out = _sanitize_island_roles(data, base_roles or {})
    if roles_out:
        patch["roles"] = roles_out
    if data.get("title"):
        patch["title"] = str(data["title"])[:120]
    return patch
