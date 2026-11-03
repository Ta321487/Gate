"""LLM 温度分级：档位区间 + 主链路任务映射 + 填岛 unit 低位锁。"""

from __future__ import annotations

from app.llm.temperature import (
    TEMP_ABSOLUTE,
    TEMP_BOUNDED_COPY,
    TEMP_CREATIVE,
    TEMP_LIVELY_CHAT,
    TEMP_LIVELY_SAMPLE,
    TEMP_STRUCTURED,
    TempBand,
    band_of,
    temperature_for,
    temperature_for_unit,
)
from app.llm.unit_flow.models import UnitKind


def test_bands_cover_product_tiers():
    assert band_of(TEMP_ABSOLUTE) is TempBand.deterministic
    assert band_of(TEMP_STRUCTURED) is TempBand.deterministic
    assert band_of(TEMP_BOUNDED_COPY) is TempBand.deterministic
    assert band_of(TEMP_LIVELY_SAMPLE) is TempBand.lively
    assert band_of(TEMP_LIVELY_CHAT) is TempBand.lively
    assert band_of(TEMP_CREATIVE) is TempBand.creative
    assert 0.0 <= TEMP_ABSOLUTE <= 0.1
    assert 0.0 <= TEMP_STRUCTURED <= 0.1
    assert 0.5 <= TEMP_LIVELY_SAMPLE <= 0.7
    assert 0.5 <= TEMP_LIVELY_CHAT <= 0.7
    assert 0.8 <= TEMP_CREATIVE <= 1.0


def test_main_chain_tasks_are_deterministic():
    for task in (
        "upload_cluster",
        "match_recommend",
        "qa_report",
        "job_fix",
        "bake_fail_classify",
        "bake_fail_hint",
    ):
        assert band_of(temperature_for(task)) is TempBand.deterministic


def test_lively_and_creative_tasks():
    assert band_of(temperature_for("sample_proposal")) is TempBand.lively
    assert band_of(temperature_for("student_chat")) is TempBand.lively
    assert temperature_for("student_chat") == TEMP_LIVELY_CHAT
    assert band_of(temperature_for("brainstorm")) is TempBand.creative


def test_island_fill_locked_low():
    """island_fill 主链路：文案 unit 走 BOUNDED_COPY，角色绝对低位；均不上 lively。"""
    assert temperature_for_unit(UnitKind.island_roles) == TEMP_ABSOLUTE
    for kind in (
        UnitKind.island_labels,
        UnitKind.island_seeds,
        UnitKind.island_entities,
        UnitKind.ppt_page,
    ):
        t = temperature_for_unit(kind)
        assert t == TEMP_BOUNDED_COPY
        assert band_of(t) is TempBand.deterministic
    for kind in (
        UnitKind.er_labels,
        UnitKind.module_labels,
        UnitKind.testcase_labels,
    ):
        assert temperature_for_unit(kind) == TEMP_STRUCTURED


def test_build_unit_messages_uses_policy():
    from app.llm.unit_flow.models import DeliveryPlan, FrozenSpec, TaskUnit
    from app.llm.unit_flow.prompts import build_unit_messages

    plan = DeliveryPlan(
        frozen=FrozenSpec(domain="DOM-BOOK", title="图书"),
        proposal_excerpt="借阅",
        units=[],
    )
    unit = TaskUnit(
        id="island.labels",
        kind=UnitKind.island_labels,
        payload={"keys": ["authLead"], "current": {}},
    )
    _msgs, temp = build_unit_messages(plan, unit)
    assert temp == TEMP_BOUNDED_COPY

    roles = TaskUnit(
        id="island.roles",
        kind=UnitKind.island_roles,
        payload={"current_roles": {}},
    )
    _msgs2, temp2 = build_unit_messages(plan, roles)
    assert temp2 == TEMP_ABSOLUTE


def test_student_chat_constant_aligned_in_skeleton():
    from pathlib import Path

    java = (
        Path(__file__).resolve().parents[2]
        / "skeletons"
        / "baseline"
        / "backend"
        / "src"
        / "main"
        / "java"
        / "com"
        / "thesis"
        / "service"
        / "DeepSeekClient.java"
    ).read_text(encoding="utf-8")
    assert "CHAT_TEMPERATURE = 0.7" in java
    assert "temperature(CHAT_TEMPERATURE)" in java
