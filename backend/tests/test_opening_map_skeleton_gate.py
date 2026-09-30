"""开题密功能地图 · 骨架静态门禁（不靠起包）。

已齐硬口径（文档）：管理端能管 + 用户端可产生数据（写库）。
本门禁只钉保险丝：已齐表里的 labels.* 必须被 Vue 真读；§1.3 报修硬点控件存在。
纯 Hint / 只读提示不得标已齐——应由地图待补表约束，本测试防止字面量空挂回流已齐。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAP = REPO / "docs" / "opening-feature-delivery-map.md"
FE_SRC = REPO / "skeletons" / "baseline" / "frontend" / "src"
BE_BASE = (
    REPO
    / "skeletons"
    / "baseline"
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "thesis"
)
OV_MYBATIS = (
    REPO
    / "skeletons"
    / "overlays"
    / "persistence-mybatis"
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "thesis"
    / "capability"
    / "TicketStore.java"
)
OV_JPA = (
    REPO
    / "skeletons"
    / "overlays"
    / "persistence-jpa"
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "thesis"
    / "capability"
    / "TicketStore.java"
)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _fe_blob() -> str:
    parts: list[str] = []
    for p in FE_SRC.rglob("*"):
        if p.suffix in {".vue", ".js"} and p.is_file():
            parts.append(_read(p))
    return "\n".join(parts)


def _be_ticket_blob() -> str:
    files = [
        BE_BASE / "capability" / "TicketStore.java",
        BE_BASE / "controller" / "TicketController.java",
        OV_MYBATIS,
        OV_JPA,
    ]
    return "\n".join(_read(p) for p in files if p.is_file())


def _map_done_sections(md: str) -> list[str]:
    """截取每个「本组本轮已齐」到下一節标题之间的正文。"""
    parts = re.split(r"(?=#### 本组本轮已齐)", md)
    return [p for p in parts if p.startswith("#### 本组本轮已齐")]


def _labels_claimed_done(md: str) -> list[str]:
    keys: list[str] = []
    for sec in _map_done_sections(md):
        for m in re.finditer(r"labels\.([A-Za-z][A-Za-z0-9_]*)", sec):
            keys.append(m.group(1))
    return sorted(set(keys))


class OpeningMapSkeletonGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.map_text = _read(MAP)
        cls.fe = _fe_blob()
        cls.be_ticket = _be_ticket_blob()

    def test_done_labels_must_be_read_in_frontend(self) -> None:
        """已齐表里的 labels.xxx 必须在 baseline Vue/JS 出现字面量。"""
        missing = [
            k for k in _labels_claimed_done(self.map_text) if k not in self.fe
        ]
        self.assertEqual(
            missing,
            [],
            "地图「已齐」含纯 Hint（前端零读取），退回待补或挂控件："
            + ", ".join(missing),
        )

    def test_repair_thicken_ui_markers(self) -> None:
        """§1.3 答辩硬点：色标 / 故障频次图 / 楼栋筛 / 对比图 / 维修员今日看板。"""
        fe_need = [
            ("categoryColorOn", "报修分类色标"),
            ("faultReasonSeries", "故障现象高频统计"),
            ("locationFilterOn", "派单按地点/楼栋筛"),
            ("cmp-lab", "报修/完工图对比"),
            ("今日处理中", "维修员今日看板"),
            ("default-today", "StaffTickets 切今日"),
        ]
        for needle, label in fe_need:
            self.assertIn(needle, self.fe, f"FE 缺 {label}: {needle}")

        be_need = [
            ("faultReasonSeries", "故障原因 series"),
            ("todayAssigned", "今日处理中筛选"),
            ("rankScope", "成绩排名范围写库"),
            ("rank_scope", "成绩排名范围列"),
        ]
        for needle, label in be_need:
            self.assertIn(needle, self.be_ticket, f"BE 缺 {label}: {needle}")

        self.assertIn("rankScope", self.fe, "FE 缺 rankScope 写库")
        self.assertIn("rank_scope", _read(REPO / "backend/app/bake/sql/fragments.py"), "SQL 缺 rank_scope")

        # §1.2 双端硬点：补考报名入口 + 按假种附件（曾 FE 空挂）
        fe_follow = [
            ("allowMakeupApply", "补考报名开关"),
            ("openApply({ makeup", "补考报名入口调用"),
            ("attachByLeaveType", "按假种附件开关"),
            ("sickAttachHint", "病假附件提示"),
            ("makeupApplyHint", "补考报名提示"),
            ("allowConfidential", "保密标记开关"),
            ("allowDisburseBatch", "发放批次开关"),
            ("allowExcellentMark", "优秀周报开关"),
            ("allowExceptionClose", "异常件办结开关"),
            ("resumeFieldSet", "简历字段套"),
            ("allowAssignDept", "分拨科室开关"),
        ]
        for needle, label in fe_follow:
            self.assertIn(needle, self.fe, f"FE 缺 {label}: {needle}")

        for path, name in ((OV_MYBATIS, "mybatis"), (OV_JPA, "jpa")):
            text = _read(path)
            self.assertIn("faultReasonSeries", text, f"{name} 缺 faultReasonSeries")
            self.assertIn("todayAssigned", text, f"{name} 缺 todayAssigned")


if __name__ == "__main__":
    unittest.main()
