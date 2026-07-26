"""错皮 / 怪交互硬闸：已知串台模式出包即拦。

与 identity_align / menu_routes 同级：只断言，不改扫词。
踩过的坑写进这里 + tests/test_domain_skin_leak.py，禁止静默回潮。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def check_schema_skin_leaks(
    schema: dict[str, Any] | None,
    *,
    domain: str = "",
    title: str = "",
    proposal_text: str = "",
) -> list[str]:
    """对单份 schema 查已知错皮；返回问题列表（空=通过）。"""
    issues: list[str] = []
    if not isinstance(schema, dict):
        return ["schema 缺失"]
    dom = str(domain or schema.get("domain") or "").strip()
    caps = set(schema.get("capabilities") or [])
    labels = schema.get("labels") if isinstance(schema.get("labels"), dict) else {}
    ents = schema.get("entities") if isinstance(schema.get("entities"), dict) else {}
    order = ents.get("order") if isinstance(ents.get("order"), dict) else {}
    roles = schema.get("roles") if isinstance(schema.get("roles"), dict) else {}
    posts = roles.get("staff_posts")

    # 无能力却残留猜你喜欢 / 私信页标题
    if "recommend" not in caps and "recommendSectionTitle" in labels:
        issues.append("无 recommend 能力却有 recommendSectionTitle")
    if "dm" not in caps and labels.get("dmPageTitle"):
        issues.append("无 dm 能力却有 dmPageTitle")

    # 客房订单必须 stay，禁止物流皮
    if "order_lines" in caps and dom == "DOM-HOTEL":
        if order.get("fulfillMode") != "stay":
            issues.append("DOM-HOTEL 订单 fulfillMode 须为 stay")
        if "物流" in str(order):
            issues.append("DOM-HOTEL 订单文案不得含「物流」")

    # 论坛默认不得挂私信/推荐
    if dom == "DOM-FORUM":
        if "dm" in caps:
            issues.append("DOM-FORUM 默认不得挂 dm（开题点名另议，默认壳禁止）")
        if "recommend" in caps:
            issues.append("DOM-FORUM 默认不得挂 recommend")

    # 应急上报皮不得仍是「提交打卡」
    if dom == "DOM-EVENT" and (title or proposal_text):
        from app.bake.scene_scan import event_product_kind

        if event_product_kind(title, proposal_text) == "incident":
            sub = str(labels.get("archiveLogSubmitLabel") or "")
            if "打卡" in sub:
                issues.append(f"应急上报皮 archiveLogSubmitLabel 仍含打卡: {sub!r}")

    # 有岗位表时任命开关必须 bool（与 validate_schema 对齐，bake 再拦一次）
    if isinstance(posts, list) and posts:
        ap = roles.get("allowAppointFromUsers")
        if not isinstance(ap, bool):
            issues.append("有 staff_posts 时 allowAppointFromUsers 须为 bool")

    return issues


def check_frontend_skin_leaks(frontend_src: Path) -> list[str]:
    """学生包前端禁止用 DOM-* 做业务分支（Login 材料清洗正则除外）。"""
    import re

    issues: list[str] = []
    if not frontend_src.is_dir():
        return issues
    pat = re.compile(r"['\"]DOM-[A-Z]{2,}")
    for path in frontend_src.rglob("*"):
        if path.suffix not in {".vue", ".js", ".ts"}:
            continue
        rel = path.as_posix()
        if rel.endswith("/views/Login.vue") or rel.endswith("\\views\\Login.vue"):
            # 登录页清洗开题材料污染，允许匹配 DOM- 字样
            continue
        text = path.read_text(encoding="utf-8")
        if pat.search(text):
            issues.append(f"前端业务分支禁止硬编码 DOM-*: {path.name}")
    return issues


def assert_skin_invariants(
    schema: dict[str, Any] | None,
    *,
    domain: str = "",
    title: str = "",
    proposal_text: str = "",
    frontend_src: Path | None = None,
) -> None:
    issues = check_schema_skin_leaks(
        schema, domain=domain, title=title, proposal_text=proposal_text
    )
    if frontend_src is not None:
        issues.extend(check_frontend_skin_leaks(frontend_src))
    if issues:
        raise ValueError(
            f"错皮/怪交互硬闸失败 [{domain}] title={title!r}: " + "; ".join(issues)
        )
