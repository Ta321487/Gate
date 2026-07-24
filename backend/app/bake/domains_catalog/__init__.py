"""合并各领域 DOMAINS 子目录。"""

from __future__ import annotations

from app.bake.domains_catalog.apply import DOMAINS as APPLY_DOMAINS
from app.bake.domains_catalog.borrow import DOMAINS as BORROW_DOMAINS
from app.bake.domains_catalog.content import DOMAINS as CONTENT_DOMAINS
from app.bake.domains_catalog.fallback import DOMAINS as FALLBACK_DOMAINS
from app.bake.domains_catalog.reserve import DOMAINS as RESERVE_DOMAINS
from app.bake.domains_catalog.ticket import DOMAINS as TICKET_DOMAINS
from app.bake.domains_catalog.trade import DOMAINS as TRADE_DOMAINS

CATALOG_DOMAINS: dict = {
    **BORROW_DOMAINS,
    **TICKET_DOMAINS,
    **APPLY_DOMAINS,
    **TRADE_DOMAINS,
    **RESERVE_DOMAINS,
    **CONTENT_DOMAINS,
    **FALLBACK_DOMAINS,
}
