"""用例图客户画法配置（按学校/客户切换，勿写死在业务归桶里）。

当前默认 = 现客户硬约束：
1. 圈同尺寸；一/二级各自竖线对齐
2. 一级→二级虚线箭头 + <<include>>（需要时也可 <<extend>>，方向按 UML）
3. 描述若写序号，个数必须与一级用例个数严格一致
4. 描述建议段落形式
5. 二级用例全部动词开头

明年换校：新增 profile，在 resolve_usecase_style 里切换即可。
"""

from __future__ import annotations

from typing import Any

# 当前接单客户（默认）
DEFAULT_USECASE_STYLE_ID = "customer_l1_five_include_verb"

USECASE_STYLE_PROFILES: dict[str, dict[str, Any]] = {
    # —— 现客户硬约束 ——
    "customer_l1_five_include_verb": {
        "id": "customer_l1_five_include_verb",
        "label": "现客户·一级5·include·二级动词",
        "level1_count": 5,
        "ellipse_w": 140.0,
        "ellipse_h": 56.0,
        "same_size_ellipses": True,
        "l1_column_align": True,
        "l2_column_align": True,
        "require_include_dashed": True,
        "allow_extend": True,
        "description_form": "paragraph",  # paragraph | lines
        "description_numbers_match_l1": True,
        "l2_verb_required": True,
        "rules_zh": [
            "每个用例椭圆尺寸相同；一级圆心共线、二级圆心共线（两条竖线）",
            "一级与二级之间为带箭头虚线，标注 <<include>>（条件扩展用 <<extend>>，箭头反向）",
            "图上文字若写序号，须与图中一级用例一一对应（几个一级圈就几个序号，不多不少；现客户一级为 5）",
            "文字描述以段落形式呈现",
            "全部二级用例必须以动词开头（如「查看订单信息」的「查看」）",
        ],
    },
    # —— 预留：明年换校可复制改参数 ——
    # "school_b_2027": { ... },
}


def resolve_usecase_style(
    style_id: str | None = None,
    *,
    spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """解析生效样式：显式 id > spec.usecase_style > 默认客户。"""
    sid = (style_id or "").strip()
    if not sid and isinstance(spec, dict):
        sid = str(spec.get("usecase_style") or spec.get("thesis_usecase_style") or "").strip()
    if not sid:
        sid = DEFAULT_USECASE_STYLE_ID
    prof = USECASE_STYLE_PROFILES.get(sid) or USECASE_STYLE_PROFILES[DEFAULT_USECASE_STYLE_ID]
    return dict(prof)


def style_public_view(style: dict[str, Any]) -> dict[str, Any]:
    """给前端/API 的精简视图。"""
    return {
        "id": style.get("id"),
        "label": style.get("label"),
        "level1_count": style.get("level1_count"),
        "rules_zh": list(style.get("rules_zh") or []),
        "description_form": style.get("description_form"),
        "allow_extend": bool(style.get("allow_extend")),
    }
