"""列中文名：只认学生页上写明字段的绑定，不靠全量词表猜。"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.bake.schema.er import collect_english_gaps, schema_model
from app.bake.schema.er_model import build_schema_model
from app.bake.schema.page_columns import (
    _template_of,
    bindings_in_template,
    pick_page_label,
    resolve_api_stem,
    resolve_page_table,
)

_ROOT = Path(__file__).resolve().parents[2]
_FRONT = _ROOT / "skeletons" / "baseline" / "frontend" / "src"

_SQL = """
CREATE TABLE order_review (
  id BIGINT PRIMARY KEY,
  order_id BIGINT NOT NULL,
  username VARCHAR(64) NOT NULL,
  rating INT NOT NULL,
  body VARCHAR(500),
  reply VARCHAR(500),
  replied_at DATETIME NULL,
  created_at DATETIME
);
CREATE TABLE sys_guestbook (
  id BIGINT PRIMARY KEY,
  username VARCHAR(64) NOT NULL,
  body VARCHAR(500) NOT NULL,
  reply VARCHAR(500),
  replied_at DATETIME NULL,
  created_at DATETIME
);
CREATE TABLE book_suggest (
  id BIGINT PRIMARY KEY,
  username VARCHAR(64) NOT NULL,
  title VARCHAR(200) NOT NULL,
  reason VARCHAR(512),
  created_at DATETIME,
  handled_at DATETIME NULL
);
CREATE TABLE staff_roster (
  id BIGINT PRIMARY KEY,
  username VARCHAR(64) NOT NULL,
  work_date DATE NOT NULL,
  shift_label VARCHAR(64),
  note VARCHAR(255),
  created_at DATETIME
);
"""


def _labels(table_name: str, model: dict) -> dict[str, dict]:
    table = next(t for t in model["tables"] if t["name"] == table_name)
    return {c["name"]: c for c in table["columns"]}


def test_pick_longer_label_when_one_contains_the_other():
    assert pick_page_label({"回复", "商家回复"}) == "商家回复"
    assert pick_page_label({"平台回复", "商家回复"}) is None


def test_resolve_api_stem_to_schema_table():
    tables = {
        "order_review",
        "sys_guestbook",
        "book_suggest",
        "staff_roster",
        "sys_audit_log",
        "user_address",
        "item_comment",
    }
    assert resolve_api_stem("order-reviews", tables) == "order_review"
    assert resolve_api_stem("guestbook", tables) == "sys_guestbook"
    assert resolve_api_stem("book-suggest", tables) == "book_suggest"
    assert resolve_api_stem("staff-roster", tables) == "staff_roster"
    assert resolve_api_stem("audit-logs", tables) == "sys_audit_log"
    assert resolve_api_stem("addresses", tables) == "user_address"
    assert resolve_api_stem("item-comments", tables) == "item_comment"
    assert resolve_api_stem("upload", tables) is None


def test_resolve_page_skips_multi_resource_cart():
    tables = {"biz_order", "user_address", "shop_coupon", "cart_item"}
    cols = {
        "biz_order": {"id", "username", "status", "total_amount", "created_at"},
        "user_address": {"id", "username", "phone", "detail", "created_at"},
        "shop_coupon": {"id", "code", "label", "status", "expire_at"},
        "cart_item": {"id", "username", "item_id", "qty"},
    }
    src = """
    http.get('/api/cart')
    http.get('/api/addresses')
    http.get('/api/coupons/mine')
    http.post('/api/orders', payload)
    """
    # 共有列打不出唯一主表
    assert (
        resolve_page_table(src, {"username", "created_at"}, tables, cols) is None
    )


def test_real_pages_bind_reply_without_chrome_time():
    admin = (_FRONT / "views/admin/OrderReviewsAdmin.vue").read_text(encoding="utf-8")
    user = (_FRONT / "views/user/MyOrderReviews.vue").read_text(encoding="utf-8")
    found: dict[str, set[str]] = {}
    for src in (admin, user):
        for col, labels in bindings_in_template(_template_of(src)).items():
            found.setdefault(col, set()).update(labels)
    assert pick_page_label(found["reply"]) == "商家回复"
    assert "时间" not in found.get("created_at", set())
    assert "replied_at" not in found

    guest = (_FRONT / "views/admin/GuestbookAdmin.vue").read_text(encoding="utf-8")
    guest_found = bindings_in_template(_template_of(guest))
    assert pick_page_label(guest_found["reply"]) == "平台回复"


def test_schema_model_without_pages_still_uses_suffix_default():
    model = schema_model(_SQL)
    assert _labels("order_review", model)["replied_at"]["label"] == "时间"


def test_build_schema_model_uses_page_binding(tmp_path: Path):
    front = tmp_path / "frontend" / "src"
    (front / "router").mkdir(parents=True)
    shutil.copy(_FRONT / "router" / "index.js", front / "router" / "index.js")
    for rel in (
        "views/admin/OrderReviewsAdmin.vue",
        "views/user/MyOrderReviews.vue",
        "views/admin/GuestbookAdmin.vue",
        "views/Guestbook.vue",
        "views/admin/BookSuggestAdmin.vue",
        "views/user/BookSuggest.vue",
        "views/admin/ItemCommentAdmin.vue",
        "views/admin/StaffRosterAdmin.vue",
    ):
        dest = front / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(_FRONT / rel, dest)
    (tmp_path / "sql").mkdir()
    (tmp_path / "sql" / "schema.sql").write_text(_SQL, encoding="utf-8")

    model = build_schema_model(tmp_path, with_er_patch=False)
    assert model
    review = _labels("order_review", model)
    assert review["reply"]["label"] == "商家回复"
    assert not review["reply"].get("page_missing")
    assert review["body"]["label"] == "正文"
    assert review["created_at"]["label"] == "创建时间"
    assert not review["created_at"].get("page_missing")
    assert review["replied_at"]["label"] == "replied_at"
    assert review["replied_at"].get("page_missing") is True

    guest = _labels("sys_guestbook", model)
    assert guest["reply"]["label"] == "平台回复"
    assert guest["replied_at"]["label"] == "replied_at"
    assert guest["replied_at"].get("page_missing") is True

    suggest = _labels("book_suggest", model)
    assert suggest["username"]["label"] == "用户名"
    assert suggest["created_at"]["label"] == "创建时间"
    assert suggest["handled_at"]["label"] == "handled_at"
    assert suggest["handled_at"].get("page_missing") is True

    roster = _labels("staff_roster", model)
    assert roster["work_date"]["label"] == "日期"
    assert roster["shift_label"]["label"] == "班次"
    assert not roster["work_date"].get("page_missing")

    gaps = collect_english_gaps(model)
    gap_cols = {(c["table"], c["name"]) for c in gaps["columns"]}
    assert ("order_review", "reply") not in gap_cols
    assert ("order_review", "replied_at") not in gap_cols
    assert ("book_suggest", "handled_at") not in gap_cols
    assert ("staff_roster", "work_date") not in gap_cols
