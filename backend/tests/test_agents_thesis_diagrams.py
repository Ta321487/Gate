"""论文图 M4 对账：只审不改；噪声过滤；须改/待核分层。"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.agents_thesis_diagrams import (
    filter_llm_thesis_findings,
    run_thesis_diagram_audit,
    stamp_finding_trust,
)


def test_stamp_rule_error_is_must_fix_llm_is_verify():
    rule = stamp_finding_trust(
        {"level": "error", "msg": "菜单不一致", "where": "usecase_desc[0]"},
        source="rule",
    )
    assert rule["trust"] == "must_fix"
    assert rule["badge"] == "须改"
    soft = stamp_finding_trust(
        {
            "level": "error",
            "msg": "图题像评价但消息像订单",
            "where": "sequences[1]",
        },
        source="llm",
    )
    assert soft["trust"] == "verify"
    assert soft["badge"] == "LLM·待核"
    assert soft["level"] == "warn"  # 语义类不得冒充须改
    hard = stamp_finding_trust(
        {
            "level": "error",
            "msg": "执行者与菜单侧不一致：subadmin 未含 order_reviews",
            "where": "sequences[2]",
        },
        source="llm",
    )
    assert hard["trust"] == "verify"
    assert hard["level"] == "error"  # 菜单硬不一致保留错级，但仍待核


def test_filter_drops_geometry_noise_and_bad_where():
    from app.llm.agents_thesis_diagrams import enrich_finding_nav

    raw = [
        {"level": "error", "msg": "用例描述写了未交付的退款流程", "where": "usecase_desc[0]"},
        {"level": "warn", "msg": "建议优化排版减少交叉", "where": "classes"},
        {"level": "error", "msg": "类图好看一点", "where": "classes"},
        {"level": "error", "msg": "缺槽位", "where": ""},
        {"level": "warn", "msg": "菱形动词偏弱", "where": "activities[1]"},
        {
            "level": "error",
            "msg": "买家登录使用的 auth 不在买家交付菜单中",
            "where": "usecase_desc[0]",
        },
        {
            "level": "info",
            "msg": "架构图角色清单使用 id「staff:shop_merchant」标注商家，该角色标识未在交付角色清单中列出",
            "where": "architecture",
        },
        {
            "level": "warn",
            "msg": "进行支付同时被购物车与订单重复 include，归属不唯一",
            "where": "usecases",
        },
        {
            "level": "error",
            "msg": "商家使用 order_reviews 但 subadmin 菜单为空",
            "where": "sequences[2]",
        },
    ]
    ev = {
        "has_staff_posts": True,
        "staff_post_ids": ["shop_merchant"],
        "roleLabels": {"staff:shop_merchant": "商家"},
    }
    kept = filter_llm_thesis_findings(raw, evidence=ev)
    msgs = [f["msg"] for f in kept]
    assert "用例描述写了未交付的退款流程" in msgs
    assert "菱形动词偏弱" in msgs
    assert not any("排版" in m or "好看" in m for m in msgs)
    assert not any(f.get("where") == "" for f in kept)
    assert not any("auth" in m and "不在" in m for m in msgs)
    assert not any("staff:shop_merchant" in m for m in msgs)
    assert not any("归属不唯一" in m for m in msgs)
    assert not any("subadmin 菜单为空" in m for m in msgs)
    nav = enrich_finding_nav(kept[0])
    assert nav.get("goto") == "usecase_desc"
    assert "用例描述表" in (nav.get("fix") or "")


def test_filter_drops_llm_duplicate_of_deterministic():
    """规则闸已报同图种同关键词 → LLM 不得再堆一条待核。"""
    det = [
        {
            "level": "error",
            "msg": "图题为评价流程，但消息多为订单操作文案，与 menu_key=order_reviews 不符",
            "where": "sequences[1]",
        }
    ]
    raw = [
        {
            "level": "warn",
            "msg": "图题买家发表评价，但消息为分页查询订单/提交订单，与评价不符",
            "where": "sequences[1]",
        },
        {
            "level": "warn",
            "msg": "用例图购物车 include 了无关支付",
            "where": "usecases",
        },
    ]
    kept = filter_llm_thesis_findings(raw, deterministic=det)
    msgs = [f["msg"] for f in kept]
    assert not any("分页查询订单" in m for m in msgs)
    assert any("购物车" in m for m in msgs)


def test_run_audit_deterministic_without_llm(tmp_path: Path):
    """无 Key → mode=deterministic；不写回图文件。"""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "domain.schema.json").write_text(
        '{"title":"测","domain":"DOM-X","menus":{"user":[],"admin":[]},"roles":{}}',
        encoding="utf-8",
    )
    rt = MagicMock()
    rt.configured = False
    db = MagicMock()

    with patch(
        "app.llm.agents_thesis_diagrams.collect_deterministic_findings",
        return_value=[
            {
                "level": "error",
                "msg": "实体属性图 own_columns 含外键列 user_id",
                "where": "er.part.orders",
            }
        ],
    ), patch(
        "app.llm.agents_thesis_diagrams.build_thesis_diagram_evidence",
        return_value={"title": "测"},
    ), patch(
        "app.llm.agents_thesis_diagrams.record_call",
        new_callable=AsyncMock,
    ):
        report = asyncio.run(
            run_thesis_diagram_audit(db, rt, project_id="p1", workspace=ws)
        )

    assert report["mode"] == "deterministic"
    assert report["llm_used"] is False
    assert report["ok"] is False
    assert "未配置大模型" in (report.get("llm_skip_reason") or "")
    assert "须改 1" in report["summary"]
    assert report.get("must_fix_count") == 1
    assert report["must_fix"][0]["badge"] == "须改"
    assert any("外键" in f["msg"] for f in report["findings"])
    audit_path = ws / "islands" / "thesis_diagram_audit.json"
    assert audit_path.is_file()


def test_run_audit_llm_findings_filtered(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    rt = MagicMock()
    rt.configured = True
    db = MagicMock()

    fake_res = MagicMock()
    fake_res.ok = True
    fake_res.data = {
        "ok": False,
        "summary": "发现假宣称",
        "findings": [
            {
                "level": "error",
                "msg": "用例描述步骤「一键退款」不在交付菜单",
                "where": "usecase_desc[0]",
            },
            {
                "level": "warn",
                "msg": "建议拖开重叠框",
                "where": "classes",
            },
        ],
    }
    fake_res.tokens = 12
    fake_res.error = None
    fake_res.prompt_tokens = 10
    fake_res.completion_tokens = 2
    fake_res.reasoning_tokens = 0
    fake_res.provider = "deepseek"
    fake_res.model = "test"

    with patch(
        "app.llm.agents_thesis_diagrams.collect_deterministic_findings",
        return_value=[],
    ), patch(
        "app.llm.agents_thesis_diagrams.build_thesis_diagram_evidence",
        return_value={},
    ), patch(
        "app.llm.agents_thesis_diagrams.budget_ok",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.llm.agents_thesis_diagrams.chat",
        new_callable=AsyncMock,
        return_value=fake_res,
    ), patch(
        "app.llm.agents_thesis_diagrams.append_deepseek_log",
    ), patch(
        "app.llm.agents_thesis_diagrams.record_call",
        new_callable=AsyncMock,
    ):
        report = asyncio.run(
            run_thesis_diagram_audit(db, rt, project_id="p1", workspace=ws)
        )

    assert report["mode"] == "llm"
    assert report["llm_used"] is True
    # 仅 LLM、无规则须改 → ok 不因当次模型拉红（不当老师保险丝）
    assert report["ok"] is True
    assert report.get("must_fix_count", 0) == 0
    assert report.get("verify_count", 0) >= 1
    assert any("一键退款" in f["msg"] for f in report["verify"])
    assert not any("重叠" in f["msg"] for f in report["findings"])
    assert report.get("llm_dropped", 0) >= 1
    assert all(f.get("badge") == "LLM·待核" for f in report["verify"])
