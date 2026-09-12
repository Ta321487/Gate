"""用例图客户画法配置（按学校/客户切换，勿写死在业务归桶里）。

当前默认 = 大连科技学院类硬约束（样例论文到（5）则画 5 圈；不是永远写死 5）：
1. 圈同尺寸；一/二级各自竖线对齐
2. 一级→二级虚线箭头 + <<include>>（需要时也可 <<extend>>，方向按 UML）
3. 描述若写序号，个数必须与一级用例个数严格一致（段落到几，圈就是几）
4. 描述建议段落形式
5. 二级用例全部动词开头

一级个数：优先跟开题模块枚举；无材料时在 [min,max] 内归桶（preferred 仅作软目标）。
明年换校：新增 profile，在 resolve_usecase_style 里切换即可。
"""

from __future__ import annotations

from typing import Any

# 当前接单客户（默认）；id 保留兼容，语义已改为「跟材料对齐」而非写死 5
DEFAULT_USECASE_STYLE_ID = "customer_l1_five_include_verb"

USECASE_STYLE_PROFILES: dict[str, dict[str, Any]] = {
    "customer_l1_five_include_verb": {
        "id": "customer_l1_five_include_verb",
        "label": "现客户·序号对齐一级·include·二级动词",
        # None = 不写死个数；门禁用实际 len(level1) 与描述序号对齐
        "level1_count": None,
        "level1_min": 3,
        "level1_max": 10,
        "level1_preferred": 5,
        "ellipse_w": 140.0,
        "ellipse_h": 56.0,
        "same_size_ellipses": True,
        "l1_column_align": True,
        "l2_column_align": True,
        "require_include_dashed": True,
        "allow_extend": True,
        "description_form": "paragraph",
        "description_numbers_match_l1": True,
        "l2_verb_required": True,
        "rules_zh": [
            "每个用例椭圆尺寸相同；一级圆心共线、二级圆心共线（两条竖线）",
            "一级与二级之间为带箭头虚线，标注 <<include>>（条件扩展用 <<extend>>，箭头反向）",
            "图上文字若写序号，须与图中一级用例一一对应（段落写到（n），一级圈就是 n 个，不多不少）",
            "文字描述以段落形式呈现；须引用全部一/二级用例名；禁止空壳「完成相关操作」与凑数「确认×」",
            "全部二级用例必须以动词开头，且不得与所属一级同名",
        ],
    },
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


def l1_count_bounds(style: dict[str, Any] | None = None) -> tuple[int, int, int]:
    """返回 (min, max, preferred)。preferred 仅菜单回落软目标。"""
    st = style or resolve_usecase_style()
    mn = int(st.get("level1_min") or 3)
    mx = int(st.get("level1_max") or 8)
    if mn < 1:
        mn = 1
    if mx < mn:
        mx = mn
    raw_pref = st.get("level1_preferred")
    if raw_pref is None:
        raw_pref = st.get("level1_count")
    pref = int(raw_pref if raw_pref is not None else 5)
    pref = max(mn, min(mx, pref))
    return mn, mx, pref


def style_public_view(style: dict[str, Any]) -> dict[str, Any]:
    """给前端/API 的精简视图。"""
    mn, mx, pref = l1_count_bounds(style)
    return {
        "id": style.get("id"),
        "label": style.get("label"),
        "level1_count": style.get("level1_count"),
        "level1_min": mn,
        "level1_max": mx,
        "level1_preferred": pref,
        "rules_zh": list(style.get("rules_zh") or []),
        "description_form": style.get("description_form"),
        "allow_extend": bool(style.get("allow_extend")),
    }
