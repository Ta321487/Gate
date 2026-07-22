"""跨题 API 传参风格：整题统一，按种子轻微变体。

bake 时把抽中的风格写进 Controller / apiCalls（学生 ZIP 只有一套，无运行时开关）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.bake.themes import label_from_catalog, normalize_from_catalog, pick_from_catalog

ITEM_REF_STYLES = [
    {"id": "path", "label": "资源 id 走路由"},
    {"id": "body", "label": "资源 id 走请求体"},
]

CART_MUTATE_STYLES = [
    {"id": "body", "label": "购物车增删走请求体"},
    {"id": "path", "label": "购物车增删走路由"},
]

_DEFAULT = {"item_ref": "path", "cart_mutate": "body"}


def pick_api_style(seed: str | None) -> dict[str, str]:
    """按种子稳定抽签；同 title|domain 重 bake 可复现。"""
    base = seed or "default"
    return {
        "item_ref": pick_from_catalog(ITEM_REF_STYLES, f"{base}|item-ref", _DEFAULT["item_ref"]),
        "cart_mutate": pick_from_catalog(
            CART_MUTATE_STYLES, f"{base}|cart", _DEFAULT["cart_mutate"]
        ),
    }


def normalize_api_style(raw: dict[str, Any] | None) -> dict[str, str]:
    src = raw if isinstance(raw, dict) else {}
    item = src.get("item_ref") or src.get("itemRef") or _DEFAULT["item_ref"]
    cart = src.get("cart_mutate") or src.get("cartMutate") or _DEFAULT["cart_mutate"]
    return {
        "item_ref": normalize_from_catalog(ITEM_REF_STYLES, str(item), _DEFAULT["item_ref"]),
        "cart_mutate": normalize_from_catalog(
            CART_MUTATE_STYLES, str(cart), _DEFAULT["cart_mutate"]
        ),
    }


def api_style_labels(style: dict[str, str] | None) -> dict[str, str]:
    s = normalize_api_style(style)
    return {
        "item_ref": label_from_catalog(ITEM_REF_STYLES, s["item_ref"]),
        "cart_mutate": label_from_catalog(CART_MUTATE_STYLES, s["cart_mutate"]),
    }


def api_style_notes(style: dict[str, str] | None) -> list[str]:
    """工厂接口清单旁注（不进学生包）。"""
    s = normalize_api_style(style)
    notes: list[str] = [
        "本课题传参在生成时已写死进源码；清单只展示本套接口。",
    ]
    if s["item_ref"] == "path":
        notes.append(
            "资源 id：POST /api/favorites/{itemId}/toggle、POST /api/browse-history/{itemId}。"
        )
    else:
        notes.append(
            "资源 id：POST /api/favorites/toggle、POST /api/browse-history（body.itemId）。"
        )
    if s["cart_mutate"] == "body":
        notes.append("购物车：POST /api/cart、POST /api/cart/remove（body）。")
    else:
        notes.append("购物车：POST /api/cart/{itemId}、DELETE /api/cart/{itemId}。")
    return notes


def apply_api_style_to_workspace(workspace: Path, style: dict[str, Any] | None) -> None:
    """按风格覆盖可变接口源码；须在 java 包名 remap 之前调用（包名仍为 com.thesis）。"""
    s = normalize_api_style(style)
    be = workspace / "backend" / "src" / "main" / "java" / "com" / "thesis"
    fe = workspace / "frontend" / "src" / "utils"
    ctrl = be / "controller"
    cap = be / "capability"

    if ctrl.is_dir():
        (ctrl / "FavoriteController.java").write_text(
            _favorite_controller(s["item_ref"]), encoding="utf-8"
        )
        (ctrl / "BrowseHistoryController.java").write_text(
            _browse_history_controller(s["item_ref"]), encoding="utf-8"
        )
        order_path = ctrl / "OrderController.java"
        if order_path.is_file():
            order_path.write_text(
                _patch_order_cart(order_path.read_text(encoding="utf-8"), s["cart_mutate"]),
                encoding="utf-8",
            )

    dead = cap / "ApiStyle.java"
    if dead.is_file():
        dead.unlink()

    if fe.is_dir():
        (fe / "apiCalls.js").write_text(_api_calls_js(s), encoding="utf-8")


def _favorite_controller(item_ref: str) -> str:
    if item_ref == "body":
        toggle = """
    @PostMapping("/toggle")
    public R<?> toggle(@RequestBody Map<String, Object> body, HttpSession session) {
        return doToggle(toLong(body.get("itemId")), session);
    }

    private static long toLong(Object v) {
        if (v == null) throw new BizException(ErrorCode.BAD_REQUEST, "缺少 itemId");
        try {
            return Long.parseLong(String.valueOf(v));
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "itemId 无效");
        }
    }
"""
    else:
        toggle = """
    @PostMapping("/{itemId}/toggle")
    public R<?> toggle(@PathVariable long itemId, HttpSession session) {
        return doToggle(itemId, session);
    }
"""
    return f"""package com.thesis.controller;

import com.thesis.capability.FavoriteStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/favorites")
public class FavoriteController {{

    private static void requireFav() {{
        if (!FavoriteStore.enabled()) throw new BizException(ErrorCode.BAD_REQUEST, "收藏功能暂不可用");
    }}

    @GetMapping
    public R<?> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {{
        requireFav();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(FavoriteStore.page(uid, page, size));
    }}

    @GetMapping("/ids")
    public R<?> ids(HttpSession session) {{
        requireFav();
        String uid = AdminAuth.requireLogin(session);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ids", FavoriteStore.idsOf(uid));
        return R.ok(out);
    }}
{toggle}
    private R<?> doToggle(long itemId, HttpSession session) {{
        requireFav();
        String uid = AdminAuth.requireLogin(session);
        try {{
            boolean on = FavoriteStore.toggle(uid, itemId);
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("favorited", on);
            return R.ok(out);
        }} catch (IllegalArgumentException | IllegalStateException e) {{
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }}
    }}
}}
"""


def _browse_history_controller(item_ref: str) -> str:
    if item_ref == "body":
        touch = """
    @PostMapping
    public R<?> touch(@RequestBody Map<String, Object> body, HttpSession session) {
        return doTouch(toLong(body.get("itemId")), session);
    }

    private static long toLong(Object v) {
        if (v == null) throw new BizException(ErrorCode.BAD_REQUEST, "缺少 itemId");
        try {
            return Long.parseLong(String.valueOf(v));
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, "itemId 无效");
        }
    }
"""
    else:
        touch = """
    @PostMapping("/{itemId}")
    public R<?> touch(@PathVariable long itemId, HttpSession session) {
        return doTouch(itemId, session);
    }
"""
    return f"""package com.thesis.controller;

import com.thesis.capability.BrowseHistoryStore;
import com.thesis.common.AdminAuth;
import com.thesis.common.BizException;
import com.thesis.common.ErrorCode;
import com.thesis.common.R;
import jakarta.servlet.http.HttpSession;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/browse-history")
public class BrowseHistoryController {{

    private static void require() {{
        if (!BrowseHistoryStore.enabled()) {{
            throw new BizException(ErrorCode.BAD_REQUEST, "浏览历史暂不可用");
        }}
    }}

    @GetMapping
    public R<?> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            HttpSession session) {{
        require();
        String uid = AdminAuth.requireLogin(session);
        return R.ok(BrowseHistoryStore.page(uid, page, size));
    }}
{touch}
    @DeleteMapping
    public R<?> clear(HttpSession session) {{
        require();
        String uid = AdminAuth.requireLogin(session);
        BrowseHistoryStore.clear(uid);
        return R.ok(null);
    }}

    private R<?> doTouch(long itemId, HttpSession session) {{
        require();
        String uid = AdminAuth.requireLogin(session);
        BrowseHistoryStore.touch(uid, itemId);
        return R.ok(Map.of("ok", true));
    }}
}}
"""


_CART_MARK_BEGIN = "    /* @@CART_MUTATE_BEGIN */"
_CART_MARK_END = "    /* @@CART_MUTATE_END */"


def _cart_methods(cart_mutate: str) -> str:
    """写入学生工程的购物车段（无工厂标记）。"""
    if cart_mutate == "path":
        return """    @PostMapping("/api/cart/{itemId}")
    public R<?> upsertCart(
            @PathVariable long itemId,
            @RequestBody(required = false) Map<String, Object> body,
            HttpSession session) {
        return doUpsertCart(itemId, qtyOf(body), session);
    }

    @DeleteMapping("/api/cart/{itemId}")
    public R<Void> removeCart(@PathVariable long itemId, HttpSession session) {
        return doRemoveCart(itemId, session);
    }

    private R<?> doUpsertCart(long itemId, int qty, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(OrderStore.upsertCart(uid, itemId, qty));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private R<Void> doRemoveCart(long itemId, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        OrderStore.removeCart(uid, itemId);
        return R.ok(null);
    }

    private static int qtyOf(Map<String, Object> body) {
        if (body == null || body.get("qty") == null) return 1;
        try {
            return Integer.parseInt(String.valueOf(body.get("qty")));
        } catch (NumberFormatException e) {
            return 1;
        }
    }"""
    return """    @PostMapping("/api/cart")
    public R<?> upsertCart(@RequestBody Map<String, Object> body, HttpSession session) {
        return doUpsertCart(toLong(body.get("itemId")), qtyOf(body), session);
    }

    @PostMapping("/api/cart/remove")
    public R<Void> removeCart(@RequestBody Map<String, Object> body, HttpSession session) {
        return doRemoveCart(toLong(body.get("itemId")), session);
    }

    private R<?> doUpsertCart(long itemId, int qty, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        try {
            return R.ok(OrderStore.upsertCart(uid, itemId, qty));
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw new BizException(ErrorCode.BAD_REQUEST, e.getMessage());
        }
    }

    private R<Void> doRemoveCart(long itemId, HttpSession session) {
        requireOrder();
        String uid = AdminAuth.requireLogin(session);
        OrderStore.removeCart(uid, itemId);
        return R.ok(null);
    }

    private static int qtyOf(Map<String, Object> body) {
        if (body == null || body.get("qty") == null) return 1;
        try {
            return Integer.parseInt(String.valueOf(body.get("qty")));
        } catch (NumberFormatException e) {
            return 1;
        }
    }"""


def _patch_order_cart(src: str, cart_mutate: str) -> str:
    """替换 OrderController 中购物车可变段；去掉 ApiStyle 引用与工厂标记。"""
    import re

    text = src.replace("import com.thesis.capability.ApiStyle;\n", "")
    text = re.sub(r"\s*ApiStyle\.requireCartMutate\([^;]+;\n", "\n", text)
    block = _cart_methods(cart_mutate)
    if _CART_MARK_BEGIN in text and _CART_MARK_END in text:
        return re.sub(
            re.escape(_CART_MARK_BEGIN) + r".*?" + re.escape(_CART_MARK_END),
            block,
            text,
            count=1,
            flags=re.DOTALL,
        )
    # 无标记：替换 GET /api/cart 之后到 addresses 之前的可变段
    m = re.search(
        r'(@GetMapping\("/api/cart"\)\s+public R<\?> cart\([^}]+?\}\s*\n)',
        text,
        flags=re.DOTALL,
    )
    if not m:
        return text
    rest = text[m.end() :]
    end = re.search(r'\n\s*@GetMapping\("/api/addresses"\)', rest)
    if not end:
        return text
    return text[: m.end()] + "\n" + block + "\n" + rest[end.start() :]


def _api_calls_js(style: dict[str, str]) -> str:
    item = style["item_ref"]
    cart = style["cart_mutate"]
    if item == "body":
        fav = "  return http.post('/api/favorites/toggle', { itemId: id })"
        hist = "  return http.post('/api/browse-history', { itemId: id })"
    else:
        fav = "  return http.post(`/api/favorites/${id}/toggle`)"
        hist = "  return http.post(`/api/browse-history/${id}`)"
    if cart == "path":
        up = "  return http.post(`/api/cart/${id}`, { qty: n })"
        rm = "  return http.delete(`/api/cart/${id}`)"
    else:
        up = "  return http.post('/api/cart', { itemId: id, qty: n })"
        rm = "  return http.post('/api/cart/remove', { itemId: id })"
    return f"""/**
 * 收藏 / 足迹 / 购物车等接口封装。
 */
import http from '../api/http.js'

export function toggleFavorite(itemId) {{
  const id = Number(itemId)
{fav}
}}

export function touchBrowseHistory(itemId) {{
  const id = Number(itemId)
{hist}
}}

export function upsertCart(itemId, qty = 1) {{
  const id = Number(itemId)
  const n = Number(qty) || 1
{up}
}}

export function removeCart(itemId) {{
  const id = Number(itemId)
{rm}
}}
"""
