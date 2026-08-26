#!/usr/bin/env python3
"""CLI：填岛拆解流水线（与 Job step 2 同实现）。

示例：
  cd backend
  python scripts/run_unit_flow.py --project-id <uuid> --plan-only
  python scripts/run_unit_flow.py --project-id <uuid> --no-llm
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.core.database import SessionLocal  # noqa: E402
from app.llm.unit_flow import build_plan_only, fill_unit_concurrency, run_fill_pipeline  # noqa: E402
from app.models import Project  # noqa: E402


async def _main(args: argparse.Namespace) -> int:
    async with SessionLocal() as db:
        project = await db.get(Project, args.project_id)
        if not project:
            print(f"项目不存在: {args.project_id}", file=sys.stderr)
            return 1
        if not project.workspace_path:
            print("请先一键生成 / bake 出工作区", file=sys.stderr)
            return 2
        ws = Path(project.workspace_path)
        if not ws.is_dir():
            print(f"工作区不存在: {ws}", file=sys.stderr)
            return 3

        spec = dict(project.spec or {})

        if args.plan_only:
            from app.services.proposal import load_merged_proposal_text

            proposal = ""
            if project.source_path:
                try:
                    proposal = load_merged_proposal_text(project.source_path)
                except Exception:  # noqa: BLE001
                    pass
            plan = build_plan_only(ws, spec, proposal)
            out = ws / "islands" / "unit_flow" / "plan.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"plan units={len(plan.units)} → {out}")
            for u in plan.units:
                print(f"  - {u.id} ({u.kind.value})")
            return 0

        summary = await run_fill_pipeline(
            db,
            project_id=project.id,
            workspace=ws,
            spec=spec,
            source_path=project.source_path,
            llm_enabled=not args.no_llm,
            merge=not args.no_merge,
            concurrency=args.concurrency or fill_unit_concurrency(),
        )

        if not args.no_merge:
            from sqlalchemy.orm.attributes import flag_modified

            project.spec = spec
            flag_modified(project, "spec")
            await db.commit()

        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
        mr = summary.merge_result
        print(
            f"done={summary.done} failed={summary.failed} skipped={summary.skipped} "
            f"merged={summary.merged} mode={mr.mode if mr else '-'}"
        )
        return 0 if summary.failed == 0 and (mr.ok if mr else True) else 4


def main() -> None:
    p = argparse.ArgumentParser(description="毕设港填岛拆解流水线 CLI")
    p.add_argument("--project-id", required=True, help="工厂项目 ID")
    p.add_argument("--plan-only", action="store_true", help="只生成 DeliveryPlan，不调 LLM")
    p.add_argument("--no-llm", action="store_true", help="跳过 LLM，merge 时走确定性填岛")
    p.add_argument("--no-merge", action="store_true", help="只跑 unit，不合并写回 workspace")
    p.add_argument("--concurrency", type=int, default=None, help="并发 unit 数")
    args = p.parse_args()
    raise SystemExit(asyncio.run(_main(args)))


if __name__ == "__main__":
    main()
