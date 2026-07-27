"""合并各领域 DOMAINS 子目录。"""

from __future__ import annotations

from app.bake.domains_catalog.apply import DOMAINS as APPLY_DOMAINS
from app.bake.domains_catalog.borrow import DOMAINS as BORROW_DOMAINS
from app.bake.domains_catalog.content import DOMAINS as CONTENT_DOMAINS
from app.bake.domains_catalog.fallback import DOMAINS as FALLBACK_DOMAINS
from app.bake.domains_catalog.oa import DOMAINS as OA_DOMAINS
from app.bake.domains_catalog.stuwork import DOMAINS as STUWORK_DOMAINS
from app.bake.domains_catalog.bed import DOMAINS as BED_DOMAINS
from app.bake.domains_catalog.checkin import DOMAINS as CHECKIN_DOMAINS
from app.bake.domains_catalog.mutual import DOMAINS as MUTUAL_DOMAINS
from app.bake.domains_catalog.visitor import DOMAINS as VISITOR_DOMAINS
from app.bake.domains_catalog.tail import DOMAINS as TAIL_DOMAINS
from app.bake.domains_catalog.instrument import DOMAINS as INSTRUMENT_DOMAINS
from app.bake.domains_catalog.exam import DOMAINS as EXAM_DOMAINS
from app.bake.domains_catalog.survey import DOMAINS as SURVEY_DOMAINS
from app.bake.domains_catalog.vote import DOMAINS as VOTE_DOMAINS
from app.bake.domains_catalog.doclib import DOMAINS as DOCLIB_DOMAINS
from app.bake.domains_catalog.carpool import DOMAINS as CARPOOL_DOMAINS
from app.bake.domains_catalog.timebank import DOMAINS as TIMEBANK_DOMAINS
from app.bake.domains_catalog.cinema import DOMAINS as CINEMA_DOMAINS
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
    **OA_DOMAINS,
    **STUWORK_DOMAINS,
    **BED_DOMAINS,
    **CHECKIN_DOMAINS,
    **MUTUAL_DOMAINS,
    **VISITOR_DOMAINS,
    **TAIL_DOMAINS,
    **INSTRUMENT_DOMAINS,
    **EXAM_DOMAINS,
    **SURVEY_DOMAINS,
    **VOTE_DOMAINS,
    **DOCLIB_DOMAINS,
    **CARPOOL_DOMAINS,
    **TIMEBANK_DOMAINS,
    **CINEMA_DOMAINS,
    **FALLBACK_DOMAINS,
}
