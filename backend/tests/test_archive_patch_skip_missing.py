"""档案 PATCH：本域未配置的列不得因整表提交而抛「系统未配置该字段」。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STORES = [
    ROOT
    / "skeletons/baseline/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
    ROOT
    / "skeletons/overlays/persistence-mybatis/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
    ROOT
    / "skeletons/overlays/persistence-jpa/backend/src/main/java/com/thesis/capability/ArchiveStore.java",
]


def _patch_opt_bodies() -> list[str]:
    out = []
    for p in STORES:
        text = p.read_text(encoding="utf-8")
        assert "private static void patchOptStr" in text, p
        # 缺列应 return，不再 throw 系统未配置该字段
        idx = text.find("private static void patchOptStr")
        end = text.find("public static boolean deleteItem(long id)", idx)
        chunk = text[idx:end]
        assert 'throw new IllegalStateException("系统未配置该字段")' not in chunk, p
        assert chunk.count("if (!hasItemColumn(col)) return;") >= 3, p
        out.append(chunk)
    return out


def test_three_stores_skip_missing_columns():
    bodies = _patch_opt_bodies()
    assert len(bodies) == 3


def test_soft_delete_stamps_shelf_off():
    for p in STORES:
        text = p.read_text(encoding="utf-8")
        assert "shelf_off=NOW()" in text, p.name
        assert "shelf_on=NOW()" in text, p.name


def test_keyword_search_includes_region_and_harvest():
    """有产地/采摘列时，关键词检索须纳入（开题按产地/采摘搜）。"""
    for p in STORES:
        text = p.read_text(encoding="utf-8")
        assert "private static void appendKeywordSearch" in text, p.name
        idx = text.find("private static void appendKeywordSearch")
        end = text.find("private static boolean hasItemColumn", idx)
        chunk = text[idx:end]
        assert 'hasItemColumn("region")' in chunk, p.name
        assert 'hasItemColumn("harvest_on")' in chunk, p.name
        assert "CAST(harvest_on AS CHAR)" in chunk, p.name
        assert text.count("appendKeywordSearch(where, args, keyword)") >= 2, p.name


def test_trade_thicken_shelf_labels_are_scheduled():
    from app.bake.features.trade_thicken import apply_trade_thicken_to_spec

    spec = {
        "domain": "DOM-SHOP",
        "capabilities": ["archive", "order_lines"],
        "schema": {"entities": {"archive": {"fields": []}}, "labels": {}},
    }
    out = apply_trade_thicken_to_spec(spec, "农产品销售网站")
    labels = (out.get("schema") or {}).get("labels") or {}
    assert labels.get("shelfOnLabel") == "定时上架"
    assert labels.get("shelfOffLabel") == "定时下架"
    assert "预约" in (labels.get("shelfScheduleHint") or "")
