"""身份 / 壳场景对齐闸（只断言，不改扫词与 builder）。

共用硬规则：
1. 门户 user 种子 profile_json 键 ⊆ 资料页字段
2. 资料页有 identityType 选项 → 种子必须带且落在选项内
3. 企业/商业档种子禁止校园专用键（studentNo 等）
4. 壳 authEyebrow / 用户角色名 / identityType 选项不得与 scene 对打
   （禁止项，不强制每个域的具体文案，避免绑死业务措辞）

用法：``assert_identity_aligned`` 在测试与 bake 出包时硬拦；
带病包不准出炉。查问题列表用 ``check_identity_alignment``。
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.bake.profile_fields import profile_fields_for
from app.bake.scene_scan import scene_for

_USER_SEED_PROFILE = re.compile(
    r"\('(?:user|patient|buyer|reader|student)'[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,\s*'(\{.*?\})'",
    re.S,
)

_SEED_KEY_ALLOW = frozenset({"realName", "email", "gender", "phone"})

_CAMPUS_ONLY_SEED_KEYS = frozenset(
    {
        "studentNo",
        "campusNo",
        "dormBuilding",
        "dormRoom",
        "gradeYear",
        "className",
        "college",
    }
)

# 非校园档壳上不应出现的校园皮（子串匹配；宁少勿误伤共用词如「预约」）
_CAMPUS_SHELL_MARKERS = (
    "校园",
    "食堂",
    "学工",
    "校内",
    "高校",
    "学生请假",
    "学生资助",
    "晨午检",
    "因病缺课",
)

# 校园档壳上不应出现的企业/商业皮
_OFFCAMPUS_SHELL_MARKERS = (
    "在线商城",
    "点餐外卖",
    "企业运维",
    "企业复工",
    "员工考勤",
    "员工福利",
    "客户跟进",
    "影视点播",
)

_OFF_CAMPUS_SCENES = frozenset(
    {"commercial", "enterprise", "community", "institution", "adopt"}
)

_OFF_CAMPUS_USER_FORBID = frozenset({"学生", "师生"})
_CAMPUS_USER_FORBID = frozenset({"业务员", "员工"})


def extract_portal_user_profile(sql: str) -> dict[str, Any] | None:
    """从 schema.sql 抽出门户终端用户演示 profile_json；找不到返回 None。"""
    m = _USER_SEED_PROFILE.search(sql or "")
    if not m:
        return None
    return json.loads(m.group(1).replace("''", "'"))


def _identity_options(fields: list[dict[str, Any]]) -> list[str] | None:
    for f in fields:
        if not isinstance(f, dict) or f.get("key") != "identityType":
            continue
        opts = f.get("options") or []
        out: list[str] = []
        for o in opts:
            if isinstance(o, dict):
                out.append(str(o.get("value") or o.get("label") or ""))
            else:
                out.append(str(o))
        return [x for x in out if x]
    return None


def _resolve_schema(
    domain: str,
    *,
    title: str,
    proposal_text: str,
    schema: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if isinstance(schema, dict) and schema:
        return schema
    if not title and not proposal_text:
        return None
    from app.bake.domain_schema import build_domain_schema

    return build_domain_schema(title, domain, proposal_text=proposal_text)


def _check_shell_vs_scene(
    scene: str,
    *,
    brow: str,
    user: str,
    opts: list[str] | None,
) -> list[str]:
    issues: list[str] = []
    if scene in _OFF_CAMPUS_SCENES:
        for m in _CAMPUS_SHELL_MARKERS:
            if m in brow:
                issues.append(
                    f"scene={scene} 壳 eyebrow 含校园词 {m!r}: {brow!r}"
                )
                break
        if user in _OFF_CAMPUS_USER_FORBID:
            issues.append(f"scene={scene} 用户角色仍是校园身份: {user!r}")
        if opts and scene in {"commercial", "enterprise"}:
            bad_opts = [x for x in ("学生", "教职工") if x in opts]
            if bad_opts:
                issues.append(
                    f"scene={scene} 资料页身份选项仍含校园档 {bad_opts}"
                )
    elif scene == "campus":
        for m in _OFFCAMPUS_SHELL_MARKERS:
            if m in brow:
                issues.append(
                    f"scene=campus 壳 eyebrow 含企业/商业词 {m!r}: {brow!r}"
                )
                break
        if user in _CAMPUS_USER_FORBID:
            issues.append(f"scene=campus 用户角色仍是企业身份: {user!r}")
        if opts and "员工" in opts and "学生" not in opts and "教职工" not in opts:
            issues.append(
                f"scene=campus 资料页身份选项像企业档: {opts}"
            )
    return issues


def check_identity_alignment(
    domain: str,
    *,
    title: str = "",
    proposal_text: str = "",
    sql: str,
    profile_fields: list[dict[str, Any]] | None = None,
    schema: dict[str, Any] | None = None,
) -> list[str]:
    """返回问题列表；空列表 = 通过。不抛异常。"""
    if domain in {"", "DOM-GENERIC"}:
        return []

    schema_obj = _resolve_schema(
        domain, title=title, proposal_text=proposal_text, schema=schema
    )
    fields = profile_fields
    if fields is None and isinstance(schema_obj, dict):
        raw = schema_obj.get("profileFields")
        if isinstance(raw, list):
            fields = raw
    if fields is None:
        fields = profile_fields_for(
            domain, title=title, proposal_text=proposal_text
        )

    keys = {
        str(f.get("key"))
        for f in fields
        if isinstance(f, dict) and f.get("key")
    }
    opts = _identity_options(fields)
    scene = scene_for(domain, title, proposal_text)
    issues: list[str] = []

    if sql:
        prof = extract_portal_user_profile(sql)
        if prof is not None:
            extra = set(prof) - keys - _SEED_KEY_ALLOW
            if extra:
                issues.append(f"seed profile 键超出资料页: {sorted(extra)}")
            if opts is not None:
                ident = prof.get("identityType")
                if not ident:
                    issues.append("资料页有 identityType，演示种子缺少 identityType")
                elif str(ident) not in opts:
                    issues.append(
                        f"演示 identityType={ident!r} 不在资料页选项 {opts} 内"
                    )
            if scene in {"commercial", "enterprise"}:
                bad = _CAMPUS_ONLY_SEED_KEYS & set(prof)
                if bad:
                    issues.append(
                        f"scene={scene} 演示种子仍含校园键: {sorted(bad)}"
                    )

    if isinstance(schema_obj, dict):
        brow = str((schema_obj.get("labels") or {}).get("authEyebrow") or "")
        user = str(
            ((schema_obj.get("roles") or {}).get("user") or {}).get("label") or ""
        )
        issues.extend(
            _check_shell_vs_scene(scene, brow=brow, user=user, opts=opts)
        )

    return issues


def assert_identity_aligned(
    domain: str,
    *,
    title: str = "",
    proposal_text: str = "",
    sql: str,
    profile_fields: list[dict[str, Any]] | None = None,
    schema: dict[str, Any] | None = None,
) -> None:
    """bake / 冒烟硬闸：有问题直接 ValueError。"""
    issues = check_identity_alignment(
        domain,
        title=title,
        proposal_text=proposal_text,
        sql=sql,
        profile_fields=profile_fields,
        schema=schema,
    )
    if issues:
        raise ValueError(
            f"身份/壳未对齐 [{domain}] title={title!r}: " + "; ".join(issues)
        )
