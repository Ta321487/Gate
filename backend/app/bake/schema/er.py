"""从 schema.sql 解析表结构，推断联系，输出陈氏 E-R 线框图 SVG。

拆分：
- schema_er_model：SQL 解析与模型组装
- schema_er_labels：中文标签、角色展开、LLM 补丁
- schema_er_svg：布局与 SVG 渲染

本模块保持原 import 路径兼容。
"""

from __future__ import annotations

from app.bake.schema.er_labels import (
    apply_er_label_patch,
    collect_english_gaps,
    count_er_gaps,
    count_er_patch_fills,
    er_labels_path,
    expand_user_role_entities,
    load_er_label_patch,
    looks_latin,
    sanitize_er_label_patch,
    save_er_label_patch,
    scrub_relation_labels,
)
from app.bake.schema.er_model import (
    Column,
    Relation,
    Table,
    build_schema_model,
    infer_relations,
    load_schema_model,
    parse_schema_sql,
    pick_core_attrs,
    schema_model,
)
from app.bake.schema.er_svg import (
    _book_embedding,
    _circular_crossings,
    _layout_entities,
    _two_page_partition,
    render_er_svg,
)

__all__ = [
    "Column",
    "Relation",
    "Table",
    "apply_er_label_patch",
    "build_schema_model",
    "collect_english_gaps",
    "count_er_gaps",
    "count_er_patch_fills",
    "er_labels_path",
    "expand_user_role_entities",
    "infer_relations",
    "load_er_label_patch",
    "load_schema_model",
    "looks_latin",
    "parse_schema_sql",
    "pick_core_attrs",
    "render_er_svg",
    "sanitize_er_label_patch",
    "save_er_label_patch",
    "schema_model",
    "scrub_relation_labels",
    "_book_embedding",
    "_circular_crossings",
    "_layout_entities",
    "_two_page_partition",
]
