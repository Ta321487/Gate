"""订单壳增强：评价（扫词）；超时关单；限时购 flash_price（E-05，扫词开）。"""

from __future__ import annotations

from app.bake.sql.ddl_edit import (
    CREATE_TABLE_RE as _CREATE_TABLE_RE,
    inject_missing_columns as _inject_missing_columns,
    prune_columns as _prune_columns,
)

import re
from typing import Any

from app.bake.proposal_lexicon import keyword_mentioned, pattern_mentioned

ORDER_REVIEW_CAP = "order_review"
FLASH_PRICE_CAP = "flash_price"

# 交易行毕设默认就要能评（开题常漏写「评价」专名）；影院选座题不默认
_REVIEW_DEFAULT_DOMAINS = frozenset({
    "DOM-SHOP",
    "DOM-FOOD",
    "DOM-HOTEL",
    "DOM-CARRENT",
})

# 开题常写「评价退单 / 用户评价」等，勿只认「订单评价」四字；禁裸「评价」（易撞指标体系）
_REVIEW_SIGNALS = re.compile(
    r"订单评价|商品评价|评价功能|评价管理|评价模块|售后评价|完成评价|星级评价|评论功能"
    r"|评价退单|用户评价|买家评价|客户评价|服务评价|餐品评价|外卖评价"
    r"|订单评分|星级评分|对订单进行评价|评价与售后|商品评论|订单评论|评分评价"
    r"|下单与评价|下单评价|支付与评价"
)
_TIMEOUT_SIGNALS = re.compile(
    r"超时取消|支付超时|自动取消订单|未支付取消|订单超时|超时关单"
)
_FLASH_TERMS = (
    "限时购",
    "限时特价",
    "限时折扣",
    "活动价",
    "秒杀",
    "促销信息",
    "节日优惠",
    "早鸟票",
    "特价",
    "场次特价",
    "第二份半价",
    "今日特价",
    "折扣价",
)


def scan_order_review(text: str) -> bool:
    return pattern_mentioned(text or "", _REVIEW_SIGNALS, ignore_contrast=True)


def scan_order_timeout(text: str) -> bool:
    return pattern_mentioned(text or "", _TIMEOUT_SIGNALS, ignore_contrast=True)


def scan_flash_price(text: str) -> bool:
    raw = text or ""
    return any(keyword_mentioned(raw, kw, ignore_contrast=True) for kw in _FLASH_TERMS)


def merge_order_extras_capabilities(
    caps: list[str],
    proposal_text: str = "",
    *,
    domain: str | None = None,
    title: str = "",
) -> list[str]:
    out = list(caps or [])
    if "order_lines" not in out:
        return [c for c in out if c not in (ORDER_REVIEW_CAP, FLASH_PRICE_CAP)]
    # 行业默认 > 开题扫词；多店扫词作补充（title 空时仍靠域默认）
    want_review = (domain or "") in _REVIEW_DEFAULT_DOMAINS or scan_order_review(
        proposal_text
    )
    if not want_review and (domain or "") == "DOM-SHOP":
        from app.bake.scene_scan import scan_shop_marketplace

        want_review = scan_shop_marketplace(title, proposal_text)
    if want_review and ORDER_REVIEW_CAP not in out:
        out.append(ORDER_REVIEW_CAP)
    if scan_flash_price(proposal_text) and FLASH_PRICE_CAP not in out:
        out.append(FLASH_PRICE_CAP)
    return out


def order_timeout_minutes(
    proposal_text: str = "",
    caps: list[str] | None = None,
    *,
    domain: str | None = None,
    title: str = "",
    schema: dict[str, Any] | None = None,
) -> int:
    """支付/待付款超时关单分钟数；0=关。

    - 开题写超时关单 → 30
    - 多店在线支付 / demoPay → 默认 15（待付款倒计时）
    """
    caps = list(caps or [])
    if "order_lines" not in caps:
        return 0
    if scan_order_timeout(proposal_text):
        return 30
    sch = schema if isinstance(schema, dict) else {}
    if sch.get("demoPay") or sch.get("shopMarketplace"):
        return 15
    if (domain or "") == "DOM-SHOP":
        from app.bake.scene_scan import scan_shop_marketplace

        if scan_shop_marketplace(title, proposal_text):
            return 15
    return 0


def attach_flash_price_fields(schema: dict[str, Any]) -> None:
    """档案字段：活动价 + 窗口；管理端走 extraFields，门户展示促销价。"""
    ents = schema.setdefault("entities", {})
    archive = ents.setdefault("archive", {})
    if not isinstance(archive, dict):
        return
    fields = list(archive.get("fields") or [])
    keys = {f.get("key") for f in fields if isinstance(f, dict)}
    extras = [
        {"key": "promoPrice", "label": "活动价(元)", "type": "number", "format": "money"},
        {"key": "promoStart", "label": "活动开始", "type": "datetime"},
        {"key": "promoEnd", "label": "活动结束", "type": "datetime"},
    ]
    for f in extras:
        if f["key"] not in keys:
            fields.append(f)
            keys.add(f["key"])
    archive["fields"] = fields
    archive["flashPriceEnabled"] = True
    labels = schema.setdefault("labels", {})
    labels.setdefault("flashPriceBadge", "活动价")
    labels.setdefault(
        "flashPriceHint",
        "活动窗口内按下单时的活动价计入订单；窗外按原价。库存仍按单仓扣减。",
    )


def attach_order_extras_schema(schema: dict[str, Any], caps: list[str], *, timeout_minutes: int = 0) -> None:
    caps = list(caps or [])
    labels = schema.setdefault("labels", {})
    menus = schema.setdefault("menus", {})
    user = menus.setdefault("user", [])
    admin = menus.setdefault("admin", [])

    if timeout_minutes > 0:
        schema["orderTimeoutMinutes"] = int(timeout_minutes)
        if schema.get("demoPay") or schema.get("shopMarketplace"):
            labels["orderTimeoutHint"] = (
                f"待付款订单超过 {timeout_minutes} 分钟将自动取消，请尽快支付"
            )
        else:
            labels.setdefault(
                "orderTimeoutHint",
                f"待确认订单超过 {timeout_minutes} 分钟将自动取消",
            )

    if FLASH_PRICE_CAP in caps:
        attach_flash_price_fields(schema)

    if ORDER_REVIEW_CAP not in caps:
        return

    from app.bake.schema.menu_utils import ensure_menu

    ensure_menu(user, "order_reviews", {"key": "order_reviews", "label": "我的评价"}, before_key="my_orders")
    ensure_menu(admin, "order_reviews", {"key": "order_reviews", "label": "评价管理"}, before_key="orders")
    labels.setdefault("orderReviewPageTitle", "我的评价")
    labels.setdefault("orderReviewPageLead", "对已完成订单进行星级与文字评价。")
    ents = schema.setdefault("entities", {})
    ents.setdefault(
        "orderReview",
        {"key": "order_review", "label": "评价", "labelPlural": "评价"},
    )


def apply_order_extras_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    caps = merge_order_extras_capabilities(
        list(spec.get("capabilities") or []),
        proposal_text,
        domain=spec.get("domain"),
        title=str(spec.get("title") or ""),
    )
    schema = dict(spec.get("schema") or {})
    timeout = order_timeout_minutes(
        proposal_text,
        caps,
        domain=str(spec.get("domain") or ""),
        title=str(spec.get("title") or ""),
        schema=schema,
    )
    spec = {**spec, "capabilities": caps}
    schema["capabilities"] = caps
    attach_order_extras_schema(schema, caps, timeout_minutes=timeout)
    # 券 / 评价 / 超时关单 / 限时购 gate
    if ORDER_REVIEW_CAP in caps or timeout > 0 or "coupon" in caps or FLASH_PRICE_CAP in caps:
        from app.bake.gate_contracts import merge_order_extras_gate

        gate = dict(spec.get("gate") or {})
        spec["gate"] = merge_order_extras_gate(gate, caps, timeout_minutes=timeout)
        features = list(spec.get("features") or [])
        names = {f.get("name") for f in features if isinstance(f, dict)}
        if ORDER_REVIEW_CAP in caps and "订单评价" not in names:
            features.append({"name": "订单评价", "status": "module"})
        if timeout > 0 and "订单超时自动取消" not in names:
            features.append({"name": "订单超时自动取消", "status": "module"})
        if FLASH_PRICE_CAP in caps and "限时购" not in names:
            features.append({"name": "限时购", "status": "module"})
        spec["features"] = features
    spec["schema"] = schema
    return spec


# --- SQL ensure (moved from fragments.py) ---

FLASH_PRICE_COLUMNS: list[tuple[str, str]] = [
    ("promo_price", "DECIMAL(10,2) NULL"),
    ("promo_start", "DATETIME NULL"),
    ("promo_end", "DATETIME NULL"),
]

def ensure_flash_price_columns(sql: str, *, enabled: bool, item_table: str | None) -> str:
    """限时购列；开题挂 flash_price 才注入档案表。"""
    if not enabled:
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, FLASH_PRICE_COLUMNS)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)

_PROMO_COUPON_DDL = """
CREATE TABLE IF NOT EXISTS promo_coupon (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(32) NOT NULL,
  label VARCHAR(64) DEFAULT '',
  min_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  off_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  total_quota INT NOT NULL DEFAULT 0,
  claimed INT NOT NULL DEFAULT 0,
  expire_at DATETIME NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_promo_code (code)
);
"""

_USER_COUPON_DDL = """
CREATE TABLE IF NOT EXISTS user_coupon (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  coupon_id BIGINT NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'unused',
  claimed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  used_at DATETIME NULL,
  order_id BIGINT NULL,
  UNIQUE KEY uk_user_coupon (username, coupon_id),
  KEY idx_user_coupon_user (username, status, id)
);
"""

_ORDER_REVIEW_DDL = """
CREATE TABLE IF NOT EXISTS order_review (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  rating INT NOT NULL,
  body VARCHAR(500) DEFAULT '',
  reply VARCHAR(500) DEFAULT '',
  replied_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_order_review (order_id),
  KEY idx_review_user (username, id)
);
"""


def _ensure_create_table_ddl(sql: str, *, table: str, ddl: str) -> str:
    """幂等补 CREATE TABLE；种子若已 INSERT/UPDATE 该表，则插到首条引用之前。"""
    if re.search(
        rf"(?i)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?{re.escape(table)}`?\b",
        sql,
    ):
        return sql
    block = ddl if ddl.endswith("\n") else ddl + "\n"
    m = re.search(
        rf"(?i)(?:INSERT\s+(?:IGNORE\s+)?INTO|UPDATE|ALTER\s+TABLE|DELETE\s+FROM)\s+`?{re.escape(table)}`?\b",
        sql,
    )
    if m:
        return sql[: m.start()] + block + sql[m.start() :]
    return sql.rstrip() + "\n" + block


def ensure_coupon_lifecycle_sql(sql: str, *, enabled: bool) -> str:
    if not enabled:
        return sql
    out = sql
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?promo_coupon`?\b", out):
        out = out.rstrip() + "\n" + _PROMO_COUPON_DDL
    if not re.search(r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?user_coupon`?\b", out):
        out = out.rstrip() + "\n" + _USER_COUPON_DDL
    return out

def ensure_order_review_sql(sql: str, *, enabled: bool) -> str:
    if not enabled:
        return sql
    return _ensure_create_table_ddl(sql, table="order_review", ddl=_ORDER_REVIEW_DDL)
