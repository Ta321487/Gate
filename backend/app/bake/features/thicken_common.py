"""加厚组共用壳：live schema / 加 feature / 档案字段幂等。

各组 ``*_thicken.py`` 业务扫词与挂载仍各管各的；此处只收无差异的三行壳。
"""

from __future__ import annotations

from typing import Any


def live_schema(spec: dict[str, Any]) -> dict[str, Any]:
    schema = spec.get("schema")
    if not isinstance(schema, dict):
        schema = {}
        spec["schema"] = schema
    return schema


def add_feature(spec: dict[str, Any], name: str, status: str = "flow") -> None:
    features = list(spec.get("features") or [])
    names = {f.get("name") for f in features if isinstance(f, dict)}
    if name not in names:
        features.append({"name": name, "status": status})
        spec["features"] = features


def ensure_archive_field(archive: dict[str, Any], field: dict[str, Any]) -> None:
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
