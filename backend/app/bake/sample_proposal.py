"""测试开题生成：TopicPack 选题 + 九段正式腔模板。

不读 DOMAINS 原文当唯一真理；pack 独立维护以覆盖常见本科/专科 Web 毕设。
可选 LLM 润色见 app.llm.agents.run_sample_proposal_agent。
HTTP：POST /tools/sample-proposal；CLI：

  cd backend && python -m app.bake.sample_proposal --list
  cd backend && python -m app.bake.sample_proposal --domain DOM-FORUM --seed 42 --no-llm
"""

from __future__ import annotations

import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.bake.proposal_packs import PACKS

_HEADER = """本科毕业设计（论文）开题报告

题目：{title}

学院：            专业：软件工程 / 计算机科学与技术
学生姓名：         学号：
指导教师：         职称：
开题日期：{year} 年 {month} 月
"""

_FOOTER = """
九、主要参考文献

[1] 王珊, 萨师煊. 数据库系统概论[M]. 5 版. 北京: 高等教育出版社, 2014.
[2] Craig Walls. Spring Boot 实战[M]. 北京: 人民邮电出版社, 2016.
[3] 尤雨溪. Vue.js 设计与实现[M]. 北京: 人民邮电出版社, 2022.
[4] 张海藩, 牟永敏. 软件工程导论[M]. 6 版. 北京: 清华大学出版社, 2013.


学生签字：         指导教师意见：

                 指导教师签字：      年 月 日
"""


@dataclass
class SampleProposal:
    pack_id: str
    anchor_domain: str
    title: str
    filename: str
    text: str
    used_llm: bool = False
    digressions: list[str] | None = None
    l1_extras: list[str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "anchor_domain": self.anchor_domain,
            "title": self.title,
            "filename": self.filename,
            "text": self.text,
            "used_llm": self.used_llm,
            "digressions": list(self.digressions or []),
            "l1_extras": list(self.l1_extras or []),
        }


def list_packs() -> list[dict[str, str]]:
    return [
        {
            "id": p["id"],
            "anchor_domain": p["anchor_domain"],
            "label": p.get("label") or p["id"],
            "kind": p.get("kind") or "single",
        }
        for p in PACKS
    ]


def _pick_pack(rng: random.Random, domain: str | None) -> dict[str, Any]:
    pool = list(PACKS)
    if domain:
        d = domain.strip().upper()
        filtered = [p for p in pool if p["anchor_domain"] == d]
        if not filtered:
            raise ValueError(f"无匹配领域的选题包: {domain}")
        pool = filtered
    return dict(rng.choice(pool))


def _sample_some(rng: random.Random, items: list[str], lo: int, hi: int) -> list[str]:
    if not items:
        return []
    n = rng.randint(lo, min(hi, len(items)))
    return rng.sample(list(items), n)


def _safe_filename(title: str) -> str:
    # 取「的…系统」前的主题短名
    m = re.search(r"的(.+?)的设计与实现", title)
    short = m.group(1) if m else title
    short = re.sub(r"[\\/:*?\"<>|]", "", short).strip()
    short = short.replace("基于 Spring Boot 与 Vue 的", "")[:40] or "测试开题"
    if not short.endswith("开题"):
        short = f"{short}开题"
    return f"{short}.txt"


def _features_block(features: list[str], l1: list[str]) -> str:
    lines = [f"{i}. {f}" for i, f in enumerate(features, 1)]
    n = len(features)
    for j, extra in enumerate(l1, 1):
        lines.append(f"{n + j}. 若进度允许，可补充{extra}。")
    return "\n".join(lines)


def _out_scope_phrase(digressions: list[str]) -> str:
    if not digressions:
        return "过重子系统"
    if len(digressions) == 1:
        return digressions[0]
    return "、".join(digressions[:-1]) + "与" + digressions[-1]


def render_template(
    pack: dict[str, Any],
    *,
    digressions: list[str],
    l1_extras: list[str],
    title: str | None = None,
    when: datetime | None = None,
) -> str:
    when = when or datetime.now()
    title = title or pack["title"]
    user = pack.get("user_role") or "用户"
    admin = pack.get("admin_role") or "管理人员"
    out_scope = _out_scope_phrase(digressions)
    features = list(pack.get("features") or [])
    feat_block = _features_block(features, l1_extras)
    main_path = pack.get("main_path") or "主业务办理"
    focus = pack.get("focus") or main_path
    problem = pack["problem"]
    value = pack["value"]
    commercial = pack["commercial_ref"]
    research_focus = pack.get("research_focus") or f"围绕{focus}"
    roles_para = pack.get("roles_para") or (
        f"系统面向{user}与{admin}。"
        f"{user}可注册登录、维护个人资料、办理主业务并查看本人记录与公告；"
        f"管理侧负责基础数据维护、业务审核或办理、用户与公告管理。"
        f"总管与业务岗位职责在详细设计中划分。"
    )
    key_scope = pack.get("key_scope") or (
        f"开题调研阶段易涉及{out_scope}等扩展能力；"
        f"本期以{main_path}主流程及必要基础数据为准，其余能力不作为答辩必演示项。"
    )
    # 若 pack 自带 key_scope 模板含 {out_scope}
    key_scope = key_scope.format(out_scope=out_scope, main_path=main_path)

    body = f"""{_HEADER.format(title=title, year=when.year, month=when.month)}

一、选题背景与意义

{problem}

{value}本课题拟设计并实现一套基于 B/S 架构的{pack.get("system_name") or "业务管理系统"}，作为毕业设计工程实践课题，突出需求分析、系统设计与实现能力训练。


二、国内外研究现状简述

{commercial}部署成本与业务范围往往超出本科毕业设计可承受规模。国内毕业设计选题里，基于 Java Web、Spring Boot 实现同类系统的案例较为常见，技术路线成熟、可参考性强。

经与指导教师讨论，本课题将研究重点放在「{focus}」主路径。{out_scope}等可作为背景对比，不纳入本期必实现范围，以保证在有限周期内完成分析、设计、编码、测试与说明书撰写。


三、研究目标

1. 分析{pack.get("scene") or "目标"}业务，梳理{user}与管理侧的使用需求。
2. 完成系统总体设计、模块划分与数据库设计。
3. 采用 Spring Boot 与 Vue 实现可运行系统，覆盖{focus}等功能。
4. 完成功能测试，整理源码、数据库脚本与毕业设计说明书，准备答辩。


四、研究内容与拟实现功能

（一）用户与权限

{roles_para}

（二）主要功能

{feat_block}

（三）研究重点

{research_focus}，以及用户端与管理端的功能边界，形成从办理到记录查询的基本业务过程。


五、关键问题与解决思路

1. 需求范围控制：{key_scope}
2. {pack.get("key_consistency") or "业务一致性：关键状态流转与数量/名额占用规则在详细设计中约定，防止超卖或越权办理。"}
3. 权限与数据安全：区分用户端与管理端，防止越权查看或改动他人数据。
4. 前后端协作：明确接口与页面流程，保证联调测试可执行。


六、技术路线

1. 体系结构：B/S，前后端分离。
2. 后端：Java、Spring Boot、MySQL。
3. 前端：Vue、Element Plus 等。
4. 开发过程：需求分析 → 系统设计 → 编码实现 → 测试修改 → 撰写说明书。


七、进度安排（参考）

第 1–2 周：查阅资料，完成开题，细化需求与用例。
第 3–4 周：完成总体设计、数据库设计与界面草案。
第 5–8 周：实现登录注册、主业务模块、基础数据与公告等。
第 9–10 周：系统联调与测试，补充说明材料。
第 11–12 周：完善毕业论文（设计说明书），准备答辩。


八、预期成果

1. {pack.get("system_name") or "业务管理系统"}软件一套（含源码与数据库脚本）。
2. 毕业设计说明书一份。
3. 系统演示环境及主要操作说明。

{_FOOTER}
"""
    return body.strip() + "\n"


def build_sample_proposal(
    *,
    domain: str | None = None,
    seed: int | None = None,
    pack_id: str | None = None,
) -> SampleProposal:
    rng = random.Random(seed)
    if pack_id:
        found = next((p for p in PACKS if p["id"] == pack_id), None)
        if not found:
            raise ValueError(f"未知选题包: {pack_id}")
        pack = dict(found)
    else:
        pack = _pick_pack(rng, domain)

    digressions = _sample_some(rng, list(pack.get("digressions") or []), 1, 2)
    l1 = _sample_some(rng, list(pack.get("l1_optional") or []), 0, 2)
    titles = list(pack.get("title_variants") or [])
    title = rng.choice(titles) if titles else pack["title"]

    text = render_template(pack, digressions=digressions, l1_extras=l1, title=title)

    return SampleProposal(
        pack_id=pack["id"],
        anchor_domain=pack["anchor_domain"],
        title=title,
        filename=_safe_filename(title),
        text=text,
        digressions=digressions,
        l1_extras=l1,
    )


def _cli_default_out_dir() -> Path:
    # bake/sample_proposal.py → 仓库根 / data/samples/_generated
    return Path(__file__).resolve().parents[3] / "data" / "samples" / "_generated"


async def _cli_maybe_llm(
    text: str, title: str, domain: str, use_llm: bool
) -> tuple[str, bool]:
    if not use_llm:
        return text, False
    try:
        from app.core.database import SessionLocal
        from app.llm.agents import run_sample_proposal_agent
        from app.llm.runtime import load_llm_runtime
    except Exception as e:  # noqa: BLE001
        print(f"[warn] LLM 不可用，使用模板稿: {e}", file=sys.stderr)
        return text, False

    async with SessionLocal() as db:
        rt = await load_llm_runtime(db)
        return await run_sample_proposal_agent(
            db, rt, draft_text=text, title=title, anchor_domain=domain
        )


def main(argv: list[str] | None = None) -> int:
    """CLI：与工厂「生成测试开题」同一套 bake 能力。"""
    import argparse
    import asyncio

    ap = argparse.ArgumentParser(description="生成测试开题报告")
    ap.add_argument("--domain", help="锚定 DOM-*")
    ap.add_argument("--pack", dest="pack_id", help="指定选题包 id")
    ap.add_argument("--seed", type=int, help="随机种子")
    ap.add_argument("--no-llm", action="store_true", help="不调用 DeepSeek/Gemini")
    ap.add_argument("--list", action="store_true", help="列出选题包")
    ap.add_argument("--check-match", action="store_true", help="打印 match_text（不改文）")
    ap.add_argument("--out", type=Path, help="输出文件路径")
    ap.add_argument("--stdout", action="store_true", help="只打印到标准输出")
    args = ap.parse_args(argv)

    if args.list:
        for p in list_packs():
            print(f"{p['id']:16} {p['anchor_domain']:14} {p['label']} ({p['kind']})")
        return 0

    try:
        sample = build_sample_proposal(
            domain=args.domain, seed=args.seed, pack_id=args.pack_id
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2

    text, used_llm = asyncio.run(
        _cli_maybe_llm(sample.text, sample.title, sample.anchor_domain, not args.no_llm)
    )

    print(f"pack={sample.pack_id} domain={sample.anchor_domain}")
    print(f"title={sample.title}")
    print(f"used_llm={used_llm}")
    if sample.digressions:
        print(f"digressions={sample.digressions}")
    if sample.l1_extras:
        print(f"l1={sample.l1_extras}")

    if args.check_match:
        from app.bake.catalog import match_text

        r = match_text(text, sample.filename)
        print(f"match domain={r.domain} archetype={r.archetype} archetypes={r.archetypes}")
        if getattr(r, "match_warnings", None):
            print(f"warnings={r.match_warnings}")

    if args.stdout:
        print("---")
        print(text)
        return 0

    out = args.out
    if out is None:
        out = _cli_default_out_dir() / sample.filename
    elif out.is_dir():
        out = out / sample.filename
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
