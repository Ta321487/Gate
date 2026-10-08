"""交易组加厚（§1.6）：购物车/订单/选座壳上的通识钉齐与域皮。

T-00：脚手架（TRADE_DOMAINS + 注册点）。
T-01：订单备注、默认地址、口味快捷、超时关单钉齐、影院取票码。
T-02：购物车全选/失效清理/自动勾掉、改规格、凑单包邮提示。
T-03：锁库存回补钉齐、确认收货超时、邀评站内信、销售日报、改地址、小票打印。
T-04：售后原因分类占比、原因必填、仅退款/退货分流、退货单号、N 天可售后、进度时间轴。
T-05：换货/仅换货、物流进度手填节点、部分发货、分享口令、收货码核销、延保登记。
T-06a：影院退票截止、占座倒计时释放、连座提示、售罄关售、观影须知勾选。
T-06b：情侣座/无障碍座标记、特效厅标记、退票手续费登记、排片周视图、连场套票说明。
T-07：点餐桌号取餐号、餐具打包包装费、营业时段禁单、骑手回池、配送费与送达、必选品类、拼单、档口分排序。
T-08：发票抬头/状态/PDF 占位；满减满赠互斥文案；原路退回说明；会员日说明。
T-09：缺货到货通知、上下架定时、好评率/晒图追评、足迹、浅规格库存、详情问答、预售说明。
T-10：能力岛加深（仅 cap 已挂）。
T-11：影院卖品加购与库存扣减；SHOP 包装费；扫尾。

硬约束
------
- 只挂 TRADE_DOMAINS = SHOP / FOOD / CINEMA；不写 HOTEL/CARRENT（§1.7）。
- Store 主战场 OrderStore / AddressStore / Cart；不改 TicketStore 共享语义。
- 超时关单复用 order_extras + DemoScheduleJobs，禁止第二套超时状态机。
- 确认收货超时走同一 DemoScheduleJobs，不另起调度框架。
- 骑手接单超时回池走同一 DemoScheduleJobs，禁止第二套调度框架。
- 上下架定时走同一 DemoScheduleJobs，禁止第二套调度框架。
- 售后加深原 refund_* 列与 requestRefund，禁止平行第二套售后状态机。
- 发票仅为抬头+状态+演示 PDF 壳，≠税控电子发票平台。
- 浅规格库存=同名在售兄弟行余量提示，≠完整 SKU 矩阵。
- 完整 SKU 矩阵 / 商户支付 / 叫号大屏等不支持项不进本组。
"""

from __future__ import annotations

from typing import Any

TRADE_DOMAINS = frozenset({"DOM-SHOP", "DOM-FOOD", "DOM-CINEMA"})

_DEFAULT_TASTE_CHIPS = ("少辣", "多冰", "不要香菜", "多糖")
_DEFAULT_REFUND_REASONS = ("质量问题", "少件/错发", "描述不符", "物流损坏", "其他")

# 三域通识：未扫词也给可答辩的超时关单默认分钟数（可被开题扫词更大值覆盖）
_TRADE_TIMEOUT_DEFAULT = 30
_SHOP_FREE_SHIP_DEFAULT = 49.0
# 发货后未确认收货：默认 7 天（分钟）；仅 SHOP 域默认
_CONFIRM_RECEIVE_TIMEOUT_DEFAULT = 7 * 24 * 60
# 收货后可申请售后天数；仅 SHOP 域默认
_AFTER_SALE_DAYS_DEFAULT = 7
# 开场前 N 分钟停止退票；仅 CINEMA
_TICKET_REFUND_CUTOFF_DEFAULT = 30
# 选座占座分钟；仅 CINEMA（与订单超时关单不是同一套）
_SEAT_HOLD_TIMEOUT_DEFAULT = 10
# 点餐：包装费 / 配送费阶梯 / 预计送达 / 骑手接单超时；仅 FOOD
_PACKAGING_FEE_DEFAULT = 1.0
_DELIVERY_FEE_BASE_DEFAULT = 3.0
_DELIVERY_FEE_FREE_DEFAULT = 30.0
_ETA_MINUTES_DEFAULT = 40
_RIDER_CLAIM_TIMEOUT_DEFAULT = 15
_DEFAULT_STALL_OPEN_HOURS = "10:00-21:00"
_DEFAULT_UTENSIL_OPTS = ("需要餐具", "无需餐具")
_DEFAULT_PACK_OPTS = ("堂食餐具", "打包带走")


def _live_schema(spec: dict[str, Any]) -> dict[str, Any]:
    schema = spec.get("schema")
    if not isinstance(schema, dict):
        schema = {}
        spec["schema"] = schema
    return schema


def _ensure_archive_field(archive: dict[str, Any], field: dict[str, Any]) -> None:
    fields = archive.get("fields")
    if not isinstance(fields, list):
        fields = []
        archive["fields"] = fields
    key = str(field.get("key") or "")
    if not key:
        return
    for f in fields:
        if isinstance(f, dict) and f.get("key") == key:
            return
    fields.append(field)


def ensure_trade_archive_columns(
    sql: str,
    *,
    domain: str | None,
    item_table: str | None,
) -> str:
    """SHOP 包邮门槛列；非本组原样返回。"""
    import re

    from app.bake.sql.fragments import _CREATE_TABLE_RE, _inject_missing_columns

    if (domain or "") != "DOM-SHOP":
        return sql
    t = (item_table or "").strip()
    if not t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return sql
    cols = [("free_ship_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 49.00")]

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if table.lower() != t.lower():
            return m.group(0)
        body = _inject_missing_columns(body, cols)
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


def ensure_cinema_thicken_sql(
    sql: str,
    *,
    domain: str | None,
    order_table: str | None,
) -> str:
    """CINEMA：占座/须知/座属性/退票手续费列；T-11 卖品表与 order_line.line_kind；非本组原样返回。"""
    import re

    from app.bake.sql.fragments import _CREATE_TABLE_RE, _inject_missing_columns

    if (domain or "") != "DOM-CINEMA":
        return sql

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        tl = table.lower()
        if tl == "cinema_seat":
            body = _inject_missing_columns(
                body,
                [
                    ("hold_until", "DATETIME NULL"),
                    ("held_by", "VARCHAR(64) NULL"),
                    ("seat_attr", "VARCHAR(16) NOT NULL DEFAULT ''"),
                ],
            )
        ot = (order_table or "biz_order").strip()
        if ot and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", ot) and tl == ot.lower():
            body = _inject_missing_columns(
                body,
                [
                    ("notice_agreed", "TINYINT NOT NULL DEFAULT 0"),
                    ("refund_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
                ],
            )
        if tl == "order_line":
            body = _inject_missing_columns(
                body,
                [("line_kind", "VARCHAR(16) NOT NULL DEFAULT ''")],
            )
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if not re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?cinema_snack`?\b", out
    ):
        out = out.rstrip() + "\n" + _CINEMA_SNACK_DDL + _CINEMA_SNACK_SEED
    return out


_CINEMA_SNACK_DDL = """
CREATE TABLE IF NOT EXISTS cinema_snack (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(80) NOT NULL,
  price_yuan DECIMAL(10,2) NOT NULL DEFAULT 0,
  stock INT NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'on',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_CINEMA_SNACK_SEED = """
INSERT IGNORE INTO cinema_snack (id, title, price_yuan, stock, status) VALUES
(1, '爆米花（中）', 18.00, 80, 'on'),
(2, '可乐（中）', 12.00, 80, 'on'),
(3, '热狗', 16.00, 40, 'on');
"""


def ensure_food_thicken_sql(
    sql: str,
    *,
    domain: str | None,
    order_table: str | None,
    item_table: str | None,
) -> str:
    """FOOD：桌号/餐具打包/包装费配送费/送达/拼单/骑手认领；菜品营业时段与评分；分类必选。"""
    import re

    from app.bake.sql.fragments import _CREATE_TABLE_RE, _inject_missing_columns

    if (domain or "") != "DOM-FOOD":
        return sql

    ot = (order_table or "biz_order").strip()
    it = (item_table or "dish").strip()
    order_ok = bool(ot and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", ot))
    item_ok = bool(it and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", it))

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        tl = table.lower()
        if order_ok and tl == ot.lower():
            body = _inject_missing_columns(
                body,
                [
                    ("table_no", "VARCHAR(32) DEFAULT ''"),
                    ("utensil_opt", "VARCHAR(32) DEFAULT ''"),
                    ("pack_opt", "VARCHAR(32) DEFAULT ''"),
                    ("packaging_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
                    ("delivery_fee_yuan", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
                    ("eta_text", "VARCHAR(64) DEFAULT ''"),
                    ("merge_code", "VARCHAR(16) DEFAULT ''"),
                    ("rider_username", "VARCHAR(64) DEFAULT ''"),
                    ("rider_claimed_at", "DATETIME NULL"),
                ],
            )
        if item_ok and tl == it.lower():
            body = _inject_missing_columns(
                body,
                [
                    ("open_hours", "VARCHAR(32) DEFAULT ''"),
                    ("stall_score", "DECIMAL(3,1) NOT NULL DEFAULT 5.0"),
                ],
            )
        if tl == "category":
            body = _inject_missing_columns(
                body,
                [("required_pick", "TINYINT NOT NULL DEFAULT 0")],
            )
        return f"{head}{body}{tail}"

    return _CREATE_TABLE_RE.sub(repl, sql)


_ORDER_SHIP_NODE_DDL = """
CREATE TABLE IF NOT EXISTS order_ship_node (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  happened_at DATETIME NULL,
  title VARCHAR(64) NOT NULL DEFAULT '',
  detail VARCHAR(255) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_order_ship_node_order (order_id)
);
"""


def ensure_order_ship_node_sql(sql: str, *, domain: str | None) -> str:
    """SHOP 物流进度手填子表；禁止 JSON 列。"""
    import re

    if (domain or "") != "DOM-SHOP":
        return sql
    if re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?order_ship_node`?\b", sql
    ):
        return sql
    return sql.rstrip() + "\n" + _ORDER_SHIP_NODE_DDL


_STOCK_NOTIFY_DDL = """
CREATE TABLE IF NOT EXISTS stock_notify (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  item_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  notified_at DATETIME NULL,
  UNIQUE KEY uk_stock_notify (item_id, username)
);
"""


def ensure_catalog_thicken_sql(
    sql: str,
    *,
    domain: str | None,
    item_table: str | None,
) -> str:
    """T-09 商品侧：上下架定时列、预售说明、到货订阅表、评价晒图追评、留言挂商品。"""
    import re

    from app.bake.sql.fragments import _CREATE_TABLE_RE, _inject_missing_columns

    d = domain or ""
    if d not in ("DOM-SHOP", "DOM-FOOD"):
        return sql

    it = (item_table or "").strip()
    item_ok = bool(it and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", it))

    def repl(m: re.Match[str]) -> str:
        head, table, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        tl = table.lower()
        if item_ok and tl == it.lower():
            cols: list[tuple[str, str]] = [
                ("shelf_on", "DATETIME NULL"),
                ("shelf_off", "DATETIME NULL"),
            ]
            if d == "DOM-SHOP":
                cols.append(("presale_note", "VARCHAR(255) DEFAULT ''"))
            body = _inject_missing_columns(body, cols)
        if tl == "order_review":
            body = _inject_missing_columns(
                body,
                [
                    ("image_url", "VARCHAR(255) DEFAULT ''"),
                    ("follow_body", "VARCHAR(500) DEFAULT ''"),
                    ("follow_at", "DATETIME NULL"),
                ],
            )
        if tl == "sys_guestbook":
            body = _inject_missing_columns(
                body,
                [("item_id", "BIGINT NULL")],
            )
            if "KEY idx_guestbook_item" not in body and "idx_guestbook_item" not in body:
                # 挂 KEY：inject 只补列，索引用行尾插入
                stripped = body.rstrip()
                if stripped.endswith(","):
                    body = stripped + "\n  KEY idx_guestbook_item (item_id),\n"
                else:
                    body = stripped + ",\n  KEY idx_guestbook_item (item_id)\n"
        return f"{head}{body}{tail}"

    out = _CREATE_TABLE_RE.sub(repl, sql)
    if d == "DOM-SHOP" and not re.search(
        r"(?i)CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+`?stock_notify`?\b", out
    ):
        out = out.rstrip() + "\n" + _STOCK_NOTIFY_DDL
    return out


def _add_feature(spec: dict[str, Any], name: str, status: str = "flow") -> None:
    features = list(spec.get("features") or [])
    names = {f.get("name") for f in features if isinstance(f, dict)}
    if name not in names:
        features.append({"name": name, "status": status})
        spec["features"] = features


def _nail_order_timeout(spec: dict[str, Any], schema: dict[str, Any], thicken: dict[str, Any]) -> None:
    """钉齐超时关单：已有分钟数则只补文案；否则三域默认 30 分钟。"""
    caps = list(spec.get("capabilities") or [])
    if "order_lines" not in caps:
        return
    current = int(schema.get("orderTimeoutMinutes") or 0)
    minutes = current if current > 0 else _TRADE_TIMEOUT_DEFAULT
    schema["orderTimeoutMinutes"] = minutes
    labels = schema.setdefault("labels", {})
    if schema.get("demoPay") or schema.get("shopMarketplace"):
        labels["orderTimeoutHint"] = f"待付款订单超过 {minutes} 分钟将自动取消，请尽快支付"
    else:
        labels.setdefault(
            "orderTimeoutHint",
            f"待确认订单超过 {minutes} 分钟将自动取消",
        )
    thicken["orderTimeoutNail"] = True
    _add_feature(spec, "订单超时未付自动取消")
    from app.bake.gate_contracts import merge_order_extras_gate

    gate = dict(spec.get("gate") or {})
    spec["gate"] = merge_order_extras_gate(gate, caps, timeout_minutes=minutes)


def apply_trade_thicken_to_spec(spec: dict[str, Any], proposal_text: str = "") -> dict[str, Any]:
    """按域默认加厚交易组 schema（只增不减；非本组原样返回）。"""
    domain = str(spec.get("domain") or "")
    if domain not in TRADE_DOMAINS:
        return spec
    caps = list(spec.get("capabilities") or [])
    if "order_lines" not in caps:
        return spec

    schema = _live_schema(spec)
    labels = schema.setdefault("labels", {})
    ents = schema.setdefault("entities", {})
    order_ent = ents.get("order") if isinstance(ents.get("order"), dict) else {}
    if not isinstance(order_ent, dict):
        order_ent = {}
    thicken = schema.get("tradeThicken") if isinstance(schema.get("tradeThicken"), dict) else {}

    schema["tradeThicken"] = thicken
    order_ent["tradeThicken"] = True
    thicken["core"] = True

    # —— T-01：钉已有字段 ——
    if domain in ("DOM-SHOP", "DOM-FOOD"):
        labels.setdefault("orderRemarkLabel", "订单备注")
        labels.setdefault("orderRemarkHint", "留言给商家，选填。")
        thicken["orderRemark"] = True
        _add_feature(spec, "订单备注")

        labels.setdefault("defaultAddressLabel", "设为默认")
        labels.setdefault("defaultAddressHint", "下单时优先使用默认地址。")
        thicken["defaultAddress"] = True
        _add_feature(spec, "收货地址默认一键")

    if domain == "DOM-FOOD":
        labels.setdefault("tasteNoteLabel", "口味 / 忌口")
        labels.setdefault("tasteNotePlaceholder", "如：少辣、不要香菜、多糖少冰")
        labels.setdefault("tasteNoteHint", "可点选快捷项，也可自行填写。")
        chips = order_ent.get("tasteNoteChips")
        if not isinstance(chips, list) or not chips:
            order_ent["tasteNoteChips"] = list(_DEFAULT_TASTE_CHIPS)
        thicken["tasteChips"] = True
        _add_feature(spec, "口味备注快捷选项")
        labels.setdefault("pickupCodeLabel", "取餐码")

    if domain == "DOM-CINEMA":
        labels.setdefault("pickupCodeLabel", "取票码")
        labels.setdefault("pickupCodeHint", "下单后生成，到店出示即可取票。")
        thicken["cinemaPickup"] = True
        _add_feature(spec, "取票码展示")

    if domain == "DOM-SHOP":
        labels.setdefault("pickupCodeLabel", "取货码")

    _nail_order_timeout(spec, schema, thicken)

    # —— T-02：购物车 UX ——
    if domain in ("DOM-SHOP", "DOM-FOOD"):
        labels.setdefault("cartSelectAllLabel", "全选")
        labels.setdefault("cartClearInvalidLabel", "清理失效")
        labels.setdefault("cartInvalidHint", "已下架或无货，不参与结算。")
        thicken["cartSelectAll"] = True
        thicken["cartClearInvalid"] = True
        thicken["cartAutoUncheck"] = True
        _add_feature(spec, "购物车全选与失效清理")

    if domain == "DOM-SHOP":
        labels.setdefault("cartChangeSpecLabel", "换规格")
        labels.setdefault("cartNoSpecHint", "当前没有可换规格。")
        thicken["cartChangeSpec"] = True
        _add_feature(spec, "购物车改规格")
        if not float(schema.get("freeShipYuan") or 0):
            schema["freeShipYuan"] = _SHOP_FREE_SHIP_DEFAULT
        labels.setdefault("freeShipYuanLabel", "包邮门槛（元）")
        labels.setdefault(
            "freeShipYuanHint",
            "购物车按勾选金额提示还差多少包邮；0 表示不提示。",
        )
        labels.setdefault("cartFreeShipHint", "再买 ¥{n} 即可包邮")
        labels.setdefault("cartFreeShipOkHint", "已满包邮门槛")
        archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
        if not isinstance(archive, dict):
            archive = {}
        _ensure_archive_field(
            archive,
            {
                "key": "freeShipYuan",
                "label": labels.get("freeShipYuanLabel") or "包邮门槛（元）",
                "type": "number",
                "hint": labels.get("freeShipYuanHint") or "",
            },
        )
        ents["archive"] = archive
        thicken["cartFreeShip"] = True
        _add_feature(spec, "购物车凑单包邮提示")

    # —— T-03：订单主规则 ——
    if domain in ("DOM-SHOP", "DOM-FOOD") and "quota" in caps:
        labels.setdefault(
            "stockLockHint",
            "下单时扣减库存，取消订单后自动回补。",
        )
        thicken["stockLock"] = True
        order_ent["stockLock"] = True
        _add_feature(spec, "下单锁库存与取消回补")

    if domain == "DOM-SHOP":
        current_recv = int(schema.get("confirmReceiveTimeoutMinutes") or 0)
        recv_min = current_recv if current_recv > 0 else _CONFIRM_RECEIVE_TIMEOUT_DEFAULT
        schema["confirmReceiveTimeoutMinutes"] = recv_min
        days = max(1, recv_min // (24 * 60))
        labels.setdefault(
            "confirmReceiveTimeoutHint",
            f"发货后超过 {days} 天未确认收货，系统将自动完成订单。",
        )
        thicken["confirmReceiveTimeout"] = True
        _add_feature(spec, "确认收货超时自动完成")

        labels.setdefault("changeAddressLabel", "修改地址")
        labels.setdefault("changeAddressHint", "发货前可修改收货人、电话与地址。")
        thicken["changeAddress"] = True
        _add_feature(spec, "订单改地址")

    if domain in ("DOM-SHOP", "DOM-FOOD"):
        labels.setdefault("salesDailyLabel", "销售日报")
        labels.setdefault("salesDailyHint", "按日汇总订单数与成交金额。")
        thicken["salesDaily"] = True
        _add_feature(spec, "销售日报简表")

    if "order_review" in caps:
        labels.setdefault("inviteReviewTitle", "邀请评价")
        labels.setdefault(
            "inviteReviewBody",
            "您的订单已完成，欢迎前往「我的订单」写下评价。",
        )
        thicken["inviteReview"] = True
        _add_feature(spec, "订单完成自动邀评")

    labels.setdefault("orderReceiptPrintLabel", "打印小票")
    thicken["orderReceiptPrint"] = True
    _add_feature(spec, "订单小票打印")

    # —— T-04：售后闭环 ——
    if domain in ("DOM-SHOP", "DOM-FOOD"):
        reasons = order_ent.get("refundReasonOptions")
        if not isinstance(reasons, list) or not reasons:
            order_ent["refundReasonOptions"] = list(_DEFAULT_REFUND_REASONS)
        labels.setdefault("refundReasonLabel", "售后原因")
        labels.setdefault("refundReasonHint", "请选择或填写具体原因，便于商家处理。")
        labels.setdefault("refundReasonRequiredHint", "请填写售后原因")
        labels.setdefault("refundReasonChartLabel", "售后原因分布")
        labels.setdefault("refundReasonChartHint", "按已提交售后申请的原因汇总。")
        thicken["refundReasonCategories"] = True
        thicken["refundReasonRequired"] = True
        _add_feature(spec, "售后原因分类")
        _add_feature(spec, "售后原因必填")

    if domain == "DOM-SHOP":
        labels.setdefault("refundTypeLabel", "售后类型")
        labels.setdefault("refundTypeRefundOnly", "仅退款")
        labels.setdefault("refundTypeReturnRefund", "退货退款")
        labels.setdefault("refundTypeExchange", "换货")
        labels.setdefault("refundTypeExchangeOnly", "仅换货")
        labels.setdefault(
            "refundTypeHint",
            "未收到货可选仅退款；已收货退回请选退货退款；换货请选换货或仅换货。",
        )
        thicken["refundType"] = True
        thicken["refundExchange"] = True
        _add_feature(spec, "仅退款与退货退款分流")
        _add_feature(spec, "售后换货")
        _add_feature(spec, "仅换货不退款")

        labels.setdefault("refundTrackingLabel", "退货物流单号")
        labels.setdefault("refundTrackingHint", "退货寄出后填写承运单号，便于商家签收。")
        thicken["refundTracking"] = True
        _add_feature(spec, "退货物流单号")

        current_days = int(schema.get("afterSaleDays") or 0)
        days = current_days if current_days > 0 else _AFTER_SALE_DAYS_DEFAULT
        schema["afterSaleDays"] = days
        labels.setdefault(
            "afterSaleDaysHint",
            f"确认收货后 {days} 天内可申请售后。",
        )
        thicken["afterSaleDays"] = True
        _add_feature(spec, "收货后限时售后")

        labels.setdefault("refundTraceLabel", "售后进度")
        labels.setdefault("refundTraceEmpty", "暂无售后进度")
        thicken["refundTrace"] = True
        _add_feature(spec, "售后进度时间轴")

        labels.setdefault("logisticsTraceLabel", "物流进度")
        labels.setdefault("shipNodeLabel", "登记物流进度")
        labels.setdefault("shipNodeHint", "填写当前物流节点，便于买家查看。")
        thicken["shipNodes"] = True
        _add_feature(spec, "物流进度手填")

        labels.setdefault("partialShipLabel", "部分发货")
        labels.setdefault("partialShipHint", "本单先发出部分商品。")
        thicken["partialShip"] = True
        _add_feature(spec, "订单部分发货")

        labels.setdefault("warrantyLabel", "延保至")
        labels.setdefault("warrantyHint", "登记本单质保截止日期。")
        thicken["warranty"] = True
        _add_feature(spec, "订单延保登记")

    if domain in ("DOM-SHOP", "DOM-FOOD"):
        labels.setdefault("orderShareLabel", "分享口令")
        labels.setdefault("orderShareHint", "凭口令可查看本单进度，无需登录。")
        thicken["orderShare"] = True
        _add_feature(spec, "订单分享口令")

        labels.setdefault("receiveCodeLabel", "收货码")
        labels.setdefault("receiveCodeHint", "当面交付时出示，商家核对后完成核销。")
        labels.setdefault("receiveCodeVerifyLabel", "核销收货码")
        thicken["receiveCode"] = True
        _add_feature(spec, "订单收货码核销")

    # —— T-06a：影院选座（截止 / 占座 / 连座 / 售罄 / 须知）——
    if domain == "DOM-CINEMA":
        try:
            current_cut = int(schema.get("ticketRefundCutoffMinutes") or 0)
        except (TypeError, ValueError):
            current_cut = 0
        cut = current_cut if current_cut > 0 else _TICKET_REFUND_CUTOFF_DEFAULT
        schema["ticketRefundCutoffMinutes"] = cut
        labels.setdefault("ticketRefundCutoffHint", f"开场前 {cut} 分钟内不可退票。")
        labels.setdefault("cinemaRefundLabel", "申请退票")
        thicken["ticketRefundCutoff"] = True
        _add_feature(spec, "影院退票截止")

        try:
            current_hold = int(schema.get("seatHoldTimeoutMinutes") or 0)
        except (TypeError, ValueError):
            current_hold = 0
        hold = current_hold if current_hold > 0 else _SEAT_HOLD_TIMEOUT_DEFAULT
        schema["seatHoldTimeoutMinutes"] = hold
        labels.setdefault(
            "seatHoldTimeoutHint",
            f"选定座位后请在 {hold} 分钟内确认购票，超时将释放。",
        )
        thicken["seatHoldTimeout"] = True
        _add_feature(spec, "选座占座倒计时")

        labels.setdefault("adjacentSeatHintTitle", "连座提示")
        labels.setdefault("adjacentSeatHintEmpty", "当前没有相邻空座。")
        thicken["adjacentSeatHint"] = True
        _add_feature(spec, "连座推荐提示")

        labels.setdefault("showSoldOutLabel", "已售罄")
        labels.setdefault("showSoldOutHint", "余座售完后本场次不再开放选座。")
        thicken["showSoldOut"] = True
        _add_feature(spec, "场次售罄关售")

        labels.setdefault("cinemaNoticeLabel", "观影须知")
        labels.setdefault(
            "cinemaNoticeBody",
            "请按时入场、对号入座；观影期间请将手机调至静音，不要喧哗或录屏。",
        )
        labels.setdefault("cinemaNoticeRequiredHint", "请先确认已阅读观影须知")
        thicken["cinemaNotice"] = True
        _add_feature(spec, "观影须知勾选")

        labels.setdefault(
            "seatShowsLead",
            "选择场次后进入座位图，确认购票后出票。开场后该场次不再售票。",
        )

        # —— T-06b：座属性 / 特效厅 / 手续费 / 周视图 / 连场 ——
        labels.setdefault("seatAttrCoupleLabel", "情侣座")
        labels.setdefault("seatAttrAccessibleLabel", "无障碍座")
        labels.setdefault("seatAttrLegendLabel", "座位说明")
        labels.setdefault("seatAttrEditLabel", "座位属性")
        thicken["seatAttrs"] = True
        _add_feature(spec, "情侣座无障碍座标记")

        labels.setdefault("effectHallLabel", "特效厅")
        labels.setdefault("effectHallImax", "IMAX")
        thicken["effectHall"] = True
        _add_feature(spec, "特效厅标记")

        labels.setdefault("refundFeeLabel", "退票手续费")
        labels.setdefault("refundFeeHint", "登记本单退票手续费（元）。")
        thicken["refundFee"] = True
        _add_feature(spec, "退票手续费登记")

        labels.setdefault("showWeekViewLabel", "周视图")
        labels.setdefault("showWeekViewEmpty", "本周暂无场次")
        thicken["showWeekView"] = True
        _add_feature(spec, "排片日历周视图")

        labels.setdefault("cinemaComboLabel", "连场套票")
        labels.setdefault(
            "cinemaComboBody",
            "同日相邻场次可一并选座购票；具体优惠以影院当日说明为准。",
        )
        thicken["cinemaCombo"] = True
        _add_feature(spec, "连场套票说明")

    # —— T-07：点餐（桌号/餐具打包/包装费/营业时段/骑手回池/配送费送达/必选/拼单/评分）——
    if domain == "DOM-FOOD":
        labels.setdefault("tableNoLabel", "桌号")
        labels.setdefault("tableNoHint", "堂食请填写桌号，便于送餐到桌。")
        labels.setdefault("pickupNoLabel", "取餐号")
        labels.setdefault("pickupNoHint", "下单或出餐后生成，到窗口出示即可取餐。")
        thicken["tableNo"] = True
        thicken["pickupNo"] = True
        _add_feature(spec, "堂食桌号取餐号")

        labels.setdefault("utensilOptLabel", "餐具")
        labels.setdefault("packOptLabel", "打包")
        utensil_opts = order_ent.get("utensilOpts")
        if not isinstance(utensil_opts, list) or not utensil_opts:
            order_ent["utensilOpts"] = list(_DEFAULT_UTENSIL_OPTS)
        pack_opts = order_ent.get("packOpts")
        if not isinstance(pack_opts, list) or not pack_opts:
            order_ent["packOpts"] = list(_DEFAULT_PACK_OPTS)
        thicken["utensilPack"] = True
        _add_feature(spec, "餐具打包选项")

        try:
            pkg = float(schema.get("packagingFeeYuan") or 0)
        except (TypeError, ValueError):
            pkg = 0.0
        if pkg <= 0:
            pkg = _PACKAGING_FEE_DEFAULT
        schema["packagingFeeYuan"] = pkg
        labels.setdefault("packagingFeeLabel", "包装费")
        labels.setdefault("packagingFeeHint", f"选择打包时加收 ¥{pkg:g} 包装费。")
        thicken["packagingFee"] = True
        _add_feature(spec, "包装费选项")

        labels.setdefault("stallOpenHoursLabel", "营业时段")
        labels.setdefault(
            "stallOpenHoursHint",
            f"可填如 {_DEFAULT_STALL_OPEN_HOURS}；时段外不可下单。",
        )
        labels.setdefault("stallClosedHint", "当前不在营业时段，请稍后再点。")
        archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
        if not isinstance(archive, dict):
            archive = {}
        _ensure_archive_field(
            archive,
            {
                "key": "openHours",
                "label": labels.get("stallOpenHoursLabel") or "营业时段",
                "type": "string",
                "hint": labels.get("stallOpenHoursHint") or "",
            },
        )
        thicken["stallOpenHours"] = True
        _add_feature(spec, "档口营业时段禁单")

        try:
            fee_base = float(schema.get("deliveryFeeBaseYuan") or 0)
        except (TypeError, ValueError):
            fee_base = 0.0
        if fee_base <= 0:
            fee_base = _DELIVERY_FEE_BASE_DEFAULT
        schema["deliveryFeeBaseYuan"] = fee_base
        try:
            fee_free = float(schema.get("deliveryFeeFreeYuan") or 0)
        except (TypeError, ValueError):
            fee_free = 0.0
        if fee_free <= 0:
            fee_free = _DELIVERY_FEE_FREE_DEFAULT
        schema["deliveryFeeFreeYuan"] = fee_free
        labels.setdefault("deliveryFeeLabel", "配送费")
        labels.setdefault(
            "deliveryFeeLadderBody",
            f"外卖配送费 ¥{fee_base:g}；餐品满 ¥{fee_free:g} 免配送费。",
        )
        thicken["deliveryFeeLadder"] = True
        _add_feature(spec, "外卖配送费阶梯")

        try:
            eta_min = int(schema.get("etaMinutes") or 0)
        except (TypeError, ValueError):
            eta_min = 0
        if eta_min <= 0:
            eta_min = _ETA_MINUTES_DEFAULT
        schema["etaMinutes"] = eta_min
        labels.setdefault("etaLabel", "预计送达")
        labels.setdefault("etaHint", f"外卖下单后预计约 {eta_min} 分钟送达。")
        thicken["etaText"] = True
        _add_feature(spec, "外卖预计送达")

        labels.setdefault("requiredCategoryLabel", "必选品类")
        labels.setdefault(
            "requiredCategoryHint",
            "勾选「下单必选」后，购物车须包含该品类至少一件。",
        )
        labels.setdefault("requiredCategoryMissingHint", "请先选择必选品类中的餐品。")
        thicken["requiredCategory"] = True
        _add_feature(spec, "点餐必选品类")

        labels.setdefault("mergeCodeLabel", "拼单码")
        labels.setdefault(
            "mergeCodeHint",
            "同桌可填相同拼单码，商家按码一并备餐；≠平台拼单优惠。",
        )
        thicken["tableMerge"] = True
        _add_feature(spec, "点餐拼单")

        labels.setdefault("stallScoreLabel", "档口评分")
        labels.setdefault("stallScoreHint", "用于列表排序，可按口碑调整。")
        _ensure_archive_field(
            archive,
            {
                "key": "stallScore",
                "label": labels.get("stallScoreLabel") or "档口评分",
                "type": "number",
                "hint": labels.get("stallScoreHint") or "",
            },
        )
        ents["archive"] = archive
        thicken["stallScoreSort"] = True
        _add_feature(spec, "档口评分排序")

        # 骑手接单超时回池：仅扫词挂骑手时开
        wants_rider = False
        try:
            from app.bake.staff_posts import food_wants_rider

            wants_rider = food_wants_rider(proposal_text or "")
        except Exception:
            wants_rider = False
        roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
        posts = roles.get("staff_posts") if isinstance(roles.get("staff_posts"), list) else []
        if not wants_rider and posts:
            wants_rider = any(
                isinstance(p, dict) and str(p.get("id") or "") == "rider" for p in posts
            )
        if wants_rider:
            try:
                claim_min = int(schema.get("riderClaimTimeoutMinutes") or 0)
            except (TypeError, ValueError):
                claim_min = 0
            if claim_min <= 0:
                claim_min = _RIDER_CLAIM_TIMEOUT_DEFAULT
            schema["riderClaimTimeoutMinutes"] = claim_min
            labels.setdefault("riderClaimLabel", "接单配送")
            labels.setdefault(
                "riderClaimTimeoutHint",
                f"骑手接单后 {claim_min} 分钟内未出餐配送，订单将重新进入待接池。",
            )
            thicken["riderPool"] = True
            _add_feature(spec, "骑手接单超时回池")

    # —— T-08：发票 + 只读规则文案 ——
    caps_set = {str(c) for c in (spec.get("capabilities") or []) if c}

    if domain == "DOM-SHOP":
        labels.setdefault("invoiceTitleLabel", "发票抬头")
        labels.setdefault("invoiceTitleHint", "选填；用于开具普通发票演示，非税控。")
        labels.setdefault("invoiceStatusLabel", "开票状态")
        labels.setdefault("invoiceStatusPending", "申请中")
        labels.setdefault("invoiceStatusIssued", "已开")
        labels.setdefault("invoiceRequestLabel", "申请开票")
        labels.setdefault("invoiceIssueLabel", "标记已开")
        labels.setdefault("invoiceDownloadLabel", "下载发票")
        labels.setdefault(
            "invoiceDownloadHint",
            "演示用固定模板，可浏览器打印或保存；≠税控电子发票。",
        )
        thicken["invoiceTitle"] = True
        thicken["invoiceStatus"] = True
        thicken["invoicePdf"] = True
        _add_feature(spec, "发票抬头与开票状态")
        _add_feature(spec, "订单发票下载占位")

        labels.setdefault("giftPromoLabel", "满赠说明")
        labels.setdefault(
            "giftPromoBody",
            "购满指定金额可获赠品或加价购，以结算页与活动说明为准；赠品不叠加现金券面额。",
        )
        thicken["giftPromo"] = True
        _add_feature(spec, "满赠说明")

    if domain in ("DOM-SHOP", "DOM-FOOD"):
        labels.setdefault("refundOriginLabel", "退款说明")
        labels.setdefault(
            "refundOriginHint",
            "同意售后后退回系统内余额或订单原支付演示渠道，不对接微信/支付宝商户清算。",
        )
        thicken["refundOrigin"] = True
        _add_feature(spec, "退款原路退回说明")

    if domain == "DOM-SHOP" and "spend_discount" in caps_set:
        labels.setdefault("spendDiscountHelpLabel", "满减规则")
        labels.setdefault(
            "spendDiscountHelpBody",
            "按实付金额阶梯满减；与优惠券同单时取更优优惠，不重复叠加。",
        )
        thicken["spendDiscountHelp"] = True
        _add_feature(spec, "满减叠加说明")

    if domain == "DOM-SHOP" and "coupon" in caps_set:
        labels.setdefault("couponMutexLabel", "优惠券说明")
        labels.setdefault(
            "couponMutexBody",
            "一张订单一般只用一张券；与满减互斥时自动取更省的那一项。",
        )
        thicken["couponMutex"] = True
        _add_feature(spec, "优惠券互斥说明")

    if domain == "DOM-SHOP" and "member_tier" in caps_set:
        labels.setdefault("memberDayLabel", "会员日")
        labels.setdefault(
            "memberDayHint",
            "会员日以当前会员等级折扣展示为准；具体活动日以店内说明为准。",
        )
        thicken["memberDay"] = True
        _add_feature(spec, "会员日折扣说明")

    # —— T-09：商品侧 ——
    archive = ents.get("archive") if isinstance(ents.get("archive"), dict) else {}
    if not isinstance(archive, dict):
        archive = {}

    if domain in ("DOM-SHOP", "DOM-FOOD"):
        labels.setdefault("shelfScheduleLabel", "定时上下架")
        labels.setdefault("shelfOnLabel", "上架时间")
        labels.setdefault("shelfOffLabel", "下架时间")
        labels.setdefault(
            "shelfScheduleHint",
            "到点自动上架或下架；未填则按库存与手动状态。",
        )
        _ensure_archive_field(
            archive,
            {
                "key": "shelfOn",
                "label": labels.get("shelfOnLabel") or "上架时间",
                "type": "datetime",
                "hint": labels.get("shelfScheduleHint") or "",
            },
        )
        _ensure_archive_field(
            archive,
            {
                "key": "shelfOff",
                "label": labels.get("shelfOffLabel") or "下架时间",
                "type": "datetime",
                "hint": labels.get("shelfScheduleHint") or "",
            },
        )
        thicken["shelfSchedule"] = True
        _add_feature(spec, "商品上下架定时")

        labels.setdefault("goodRateLabel", "好评率")
        labels.setdefault("goodRateHint", "按已评价订单中 4～5 星占比统计。")
        labels.setdefault("goodRateEmpty", "暂无评价")
        thicken["goodRate"] = True
        _add_feature(spec, "商品好评率展示")

    if domain == "DOM-SHOP":
        labels.setdefault("stockNotifyLabel", "到货通知我")
        labels.setdefault("stockNotifyHint", "补货后会发站内信；可再次订阅。")
        labels.setdefault("stockNotifyDoneLabel", "已登记到货提醒")
        labels.setdefault("stockNotifyAgainLabel", "再次订阅到货")
        thicken["stockNotify"] = True
        _add_feature(spec, "缺货到货通知")
        _add_feature(spec, "商品到货订阅")

        labels.setdefault("presaleNoteLabel", "预售说明")
        labels.setdefault(
            "presaleNoteHint",
            "可填写定金/尾款或发货节奏；仅说明，不对接第三方支付分账。",
        )
        _ensure_archive_field(
            archive,
            {
                "key": "presaleNote",
                "label": labels.get("presaleNoteLabel") or "预售说明",
                "type": "string",
                "hint": labels.get("presaleNoteHint") or "",
            },
        )
        thicken["presaleNote"] = True
        _add_feature(spec, "商品预售定金尾款说明")

        labels.setdefault("specStockLabel", "规格库存")
        labels.setdefault(
            "specStockHint",
            "同名在售规格可分看库存；完整多维 SKU 矩阵不支持。",
        )
        thicken["specStock"] = True
        _add_feature(spec, "商品规格库存分记")

        labels.setdefault("itemQaLabel", "商品问答")
        labels.setdefault("itemQaHint", "对这件商品提问，店家会在留言里回复。")
        labels.setdefault("itemQaEmpty", "还没有人提问")
        labels.setdefault("itemQaSubmitLabel", "提问")
        thicken["itemQa"] = True
        _add_feature(spec, "商品详情页问答")

        # 浏览足迹：SHOP 域默认挂 browse_history
        caps_list = list(spec.get("capabilities") or [])
        if "browse_history" not in caps_list and "archive" in caps_list:
            caps_list.append("browse_history")
            spec["capabilities"] = caps_list
            schema["capabilities"] = caps_list
            caps_set = set(caps_list)
            try:
                from app.bake.features.ux_scan import attach_ux_schema
                from app.bake.gate_contracts import merge_ux_gate

                attach_ux_schema(schema, caps_list)
                gate = dict(spec.get("gate") or {})
                spec["gate"] = merge_ux_gate(gate, caps_list)
            except Exception:
                pass
            thicken["browseHistory"] = True
            _add_feature(spec, "商品浏览足迹")

    if "order_review" in caps_set and domain in ("DOM-SHOP", "DOM-FOOD"):
        labels.setdefault("reviewImageLabel", "晒图")
        labels.setdefault("reviewImageHint", "可上传一张实物图（选填）。")
        labels.setdefault("reviewFollowLabel", "追评")
        labels.setdefault("reviewFollowHint", "确认收货评价后可再补充一次。")
        thicken["reviewImage"] = True
        thicken["reviewFollow"] = True
        _add_feature(spec, "评价晒图")
        _add_feature(spec, "商品评论追评")

    # —— T-10：能力岛加深（仅已挂对应 cap 时）——
    if "coupon" in caps_set and domain == "DOM-SHOP":
        labels.setdefault("couponRedeemCodeLabel", "核销码")
        labels.setdefault(
            "couponRedeemCodeHint",
            "下单选用的券码，可在订单详情核对。",
        )
        labels.setdefault("couponClaimCenterTitle", labels.get("couponsPageTitle") or "领券中心")
        labels.setdefault(
            "couponClaimCenterLead",
            labels.get("couponsPageLead") or "领取可用券，下单时选用券码抵扣。",
        )
        labels["couponsPageTitle"] = labels.get("couponClaimCenterTitle") or "领券中心"
        labels["couponsPageLead"] = labels.get("couponClaimCenterLead") or labels["couponsPageLead"]
        labels.setdefault("couponExpireNotifyTitle", "优惠券即将失效")
        labels.setdefault(
            "couponExpireNotifyBody",
            "您有优惠券已过期未使用，可到领券中心查看是否有新券。",
        )
        thicken["couponRedeemCode"] = True
        thicken["couponClaimCenter"] = True
        thicken["couponExpireNotify"] = True
        _add_feature(spec, "优惠券核销码展示")
        _add_feature(spec, "优惠券领取中心页")
        _add_feature(spec, "优惠券过期站内信提醒")

    if "group_buy" in caps_set and domain == "DOM-SHOP":
        labels.setdefault("groupBuyProgressLabel", "拼团进度")
        labels.setdefault("groupBuyProgressHint", "已参团人数 / 成团人数。")
        labels.setdefault(
            "groupBuyFailRefundHint",
            "拼团失败后会自动退回系统内支付金额；未支付单直接取消。",
        )
        thicken["groupBuyProgress"] = True
        thicken["groupBuyFailRefund"] = True
        _add_feature(spec, "拼团进度条")
        _add_feature(spec, "拼团失败自动退款说明")

    if "flash_price" in caps_set and domain == "DOM-SHOP":
        labels.setdefault("flashCountdownLabel", "距结束")
        labels.setdefault("flashCountdownEnded", "已结束")
        thicken["flashCountdown"] = True
        _add_feature(spec, "限时购倒计时展示")

    if "blind_box" in caps_set and domain == "DOM-SHOP":
        labels.setdefault("blindDrawsPageTitle", "中赏记录")
        labels.setdefault("blindDrawsPageLead", "查看已抽中的奖品记录。")
        labels.setdefault("blindDrawsEmpty", "还没有抽中记录")
        thicken["blindDraws"] = True
        _add_feature(spec, "盲盒中赏记录页")
        try:
            from app.bake.schema.menu_utils import ensure_menu

            menus = schema.setdefault("menus", {})
            user = menus.setdefault("user", [])
            ensure_menu(
                user,
                "blind_draws",
                {"key": "blind_draws", "label": labels.get("blindDrawsPageTitle") or "中赏记录"},
                before_key="my_orders",
            )
        except Exception:
            pass

    if "points" in caps_set:
        if domain == "DOM-SHOP":
            labels.setdefault("pointsLedgerPageTitle", "积分明细")
            labels.setdefault("pointsLedgerPageLead", "查看积分增减流水。")
            labels.setdefault("pointsLedgerEmpty", "暂无积分流水")
            labels.setdefault("pointsFreightHint", "积分兑换抵扣运费以结算页为准；不足时仍按原运费。")
            thicken["pointsLedger"] = True
            thicken["pointsFreight"] = True
            _add_feature(spec, "积分明细流水页")
            _add_feature(spec, "积分商城兑换运费说明")
            try:
                from app.bake.schema.menu_utils import ensure_menu

                menus = schema.setdefault("menus", {})
                user = menus.setdefault("user", [])
                ensure_menu(
                    user,
                    "points_ledger",
                    {
                        "key": "points_ledger",
                        "label": labels.get("pointsLedgerPageTitle") or "积分明细",
                    },
                    before_key="profile",
                )
            except Exception:
                pass
        if domain == "DOM-CINEMA":
            labels.setdefault("cinemaPointsTicketLabel", "积分兑票")
            labels.setdefault(
                "cinemaPointsTicketHint",
                "可用积分抵扣票价，以选座结算页展示为准；不足时请补余额。",
            )
            thicken["cinemaPointsTicket"] = True
            _add_feature(spec, "影院积分兑票说明")

    if "member_tier" in caps_set and domain == "DOM-CINEMA":
        labels.setdefault("cinemaMemberPriceLabel", "会员价")
        labels.setdefault(
            "cinemaMemberPriceHint",
            "当前会员等级可享折扣价，以结算页实付为准。",
        )
        thicken["cinemaMemberPrice"] = True
        _add_feature(spec, "影院会员价说明")

    # —— T-11：影院卖品 + SHOP 包装费 ——
    if domain == "DOM-CINEMA":
        labels.setdefault("cinemaSnackLabel", "卖品加购")
        labels.setdefault("cinemaSnackHint", "选座时可加购爆米花等卖品，随票一并结算。")
        labels.setdefault("cinemaSnackEmpty", "暂无可加购卖品")
        labels.setdefault("cinemaSnackStockHint", "下单时扣减卖品库存，取消订单后回补。")
        labels.setdefault("cinemaSnackSoldOutLabel", "卖品暂时无货")
        labels.setdefault("cinemaSnackSaveLabel", "保存卖品")
        thicken["cinemaSnack"] = True
        thicken["cinemaSnackStock"] = True
        _add_feature(spec, "影院卖品加购")
        _add_feature(spec, "影院卖品库存扣减")

    if domain == "DOM-SHOP":
        try:
            pkg = float(schema.get("packagingFeeYuan") or 0)
        except (TypeError, ValueError):
            pkg = 0.0
        if pkg <= 0:
            pkg = _PACKAGING_FEE_DEFAULT
        schema["packagingFeeYuan"] = pkg
        labels.setdefault("packagingFeeLabel", "包装费")
        labels.setdefault("packagingFeeHint", f"需要包装袋或纸箱时加收 ¥{pkg:g}。")
        thicken["packagingFee"] = True
        _add_feature(spec, "包装费选项")

    ents["archive"] = archive
    ents["order"] = order_ent
    schema["tradeThicken"] = thicken
    return spec
