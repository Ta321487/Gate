"""archive_seed_guard bake 硬闸。"""

import pytest

from app.bake.archive_seed_guard import assert_archive_demo_seed


def test_flow_domain_requires_archive_insert():
    sql = "INSERT IGNORE INTO leave_type (id, title) VALUES (1, '事假');"
    assert_archive_demo_seed(
        sql,
        item_table="leave_type",
        flow_api={"apply": {}, "approve": {}},
    )


def test_flow_domain_missing_seed_raises():
    with pytest.raises(ValueError, match="leave_type"):
        assert_archive_demo_seed(
            "INSERT IGNORE INTO category (id, name) VALUES (1, 'a');",
            item_table="leave_type",
            flow_api={"apply": {}},
        )


def test_no_flow_api_skips():
    assert_archive_demo_seed("", item_table=None, flow_api=None)


def test_standalone_ticket_skips_archive_seed():
    assert_archive_demo_seed(
        "",
        item_table=None,
        flow_api={"apply": {}, "approve": {}},
        ticket_mode="standalone",
    )
