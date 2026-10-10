"""测试级缓存隔离。

项目列表/统计走「内存投影缓存」（checklist 投影 + ZIP 过期投影），
只有后台对账和写路径才会重算。跨测试复用同一进程时这些缓存必须清掉，
否则前一个用例写入的投影（尤其是 patch 出来的哈希）会污染后一个用例。
"""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "slow: 需本机 Maven 的真编/出包探针；默认跳过，加厚动骨架时 -m slow 或 --run-slow",
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="运行标了 slow 的真编/bake 探针（也可用 -m slow）",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    # --run-slow：全量含真编。任意 -m：交给用户筛选（含 -m slow），不再二次 skip。
    if config.getoption("--run-slow"):
        return
    if (getattr(config.option, "markexpr", None) or "").strip():
        return
    skip_slow = pytest.mark.skip(reason="slow：加 -m slow 或 --run-slow 才跑真编探针")
    for item in items:
        if item.get_closest_marker("slow"):
            item.add_marker(skip_slow)


@pytest.fixture(autouse=True)
def _reset_service_caches():
    from app.services import delivery_review as dr
    from app.services import projects as project_svc

    project_svc.reset_checklist_list_cache()
    dr.reset_zip_stale_cache()
    yield
    project_svc.reset_checklist_list_cache()
    dr.reset_zip_stale_cache()
