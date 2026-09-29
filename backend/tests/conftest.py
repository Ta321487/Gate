"""测试级缓存隔离。

项目列表/统计走「内存投影缓存」（checklist 投影 + ZIP 过期投影），
只有后台对账和写路径才会重算。跨测试复用同一进程时这些缓存必须清掉，
否则前一个用例写入的投影（尤其是 patch 出来的哈希）会污染后一个用例。
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_service_caches():
    from app.services import delivery_review as dr
    from app.services import projects as project_svc

    project_svc.reset_checklist_list_cache()
    dr.reset_zip_stale_cache()
    yield
    project_svc.reset_checklist_list_cache()
    dr.reset_zip_stale_cache()
