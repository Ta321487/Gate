"""论文「类图」：领域实体 UML 类图（三栏框 + 折线关联）。

拆分：
- class_model：SQL/Java 模型组装、display、layout 补丁 I/O
- class_layout：零交叉摆框、选边、正交折线
- class_svg：SVG 渲染
- class_code：Java 成员与 OO 关系（已独立）

本模块保持原 import 路径兼容。
"""

from __future__ import annotations

from app.bake.schema.class_layout import (
    _BOX_GAP,
    _LANE_GAP,
    _assoc_route,
    _nudge_layout_for_zero_cross,
    _path_obstacle_hits,
    _path_respects_endpoint_ports,
    _paths_conflict,
    _paths_proper_cross,
    _route_tree_edge,
    _trial_zero_crossing,
    attach_layout,
    ortho_path,
)
from app.bake.schema.class_model import (
    _CLASS_MODEL_CACHE,
    _EDGE_MARGIN,
    _FONT_BODY,
    _H_PAD,
    _box_size,
    _classify_fk_relation_kind,
    _format_method_display,
    _normalize_rel_kind,
    _sample_attributes,
    _sample_methods,
    _text_w,
    apply_class_display_mode,
    apply_class_layout_patch,
    build_class_model,
    class_model_from_er_tables,
    clear_class_layout_patch,
    load_class_layout_patch,
    load_class_model,
    normalize_class_display_mode,
    refine_and_persist_class_layout,
    save_class_layout_patch,
    sql_type_to_java,
    table_to_class_name,
)
from app.bake.schema.class_svg import (
    _edge_marker_attrs,
    _marker_defs,
    render_class_svg,
)

__all__ = [
    "_BOX_GAP",
    "_CLASS_MODEL_CACHE",
    "_EDGE_MARGIN",
    "_FONT_BODY",
    "_H_PAD",
    "_LANE_GAP",
    "_assoc_route",
    "_box_size",
    "_classify_fk_relation_kind",
    "_edge_marker_attrs",
    "_format_method_display",
    "_marker_defs",
    "_normalize_rel_kind",
    "_nudge_layout_for_zero_cross",
    "_path_obstacle_hits",
    "_path_respects_endpoint_ports",
    "_paths_conflict",
    "_paths_proper_cross",
    "_route_tree_edge",
    "_sample_attributes",
    "_sample_methods",
    "_text_w",
    "_trial_zero_crossing",
    "apply_class_display_mode",
    "apply_class_layout_patch",
    "attach_layout",
    "build_class_model",
    "class_model_from_er_tables",
    "clear_class_layout_patch",
    "load_class_layout_patch",
    "load_class_model",
    "normalize_class_display_mode",
    "ortho_path",
    "refine_and_persist_class_layout",
    "render_class_svg",
    "save_class_layout_patch",
    "sql_type_to_java",
    "table_to_class_name",
]
