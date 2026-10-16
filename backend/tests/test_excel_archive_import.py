"""档案 xlsx：Apache POI，模板 / 导入 / 导出，不是 CSV 冒充。"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_poi_on_three_poms() -> None:
    for rel in (
        "skeletons/baseline/backend/pom.xml",
        "skeletons/overlays/persistence-mybatis/backend/pom.xml",
        "skeletons/overlays/persistence-jpa/backend/pom.xml",
    ):
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "poi-ooxml" in text, rel


def test_archive_page_uses_xlsx() -> None:
    vue = (
        REPO / "skeletons/baseline/frontend/src/views/admin/ArchiveAdmin.vue"
    ).read_text(encoding="utf-8")
    assert "导入 Excel" in vue
    assert "导出 Excel" in vue
    assert "/api/archive/import-xlsx" in vue
    assert "/api/archive/import-template" in vue
    assert "导入 CSV" not in vue
    java = (
        REPO
        / "skeletons/baseline/backend/src/main/java/com/thesis/capability/ExcelBook.java"
    ).read_text(encoding="utf-8")
    assert "XSSFWorkbook" in java
    assert "填写说明" in java
