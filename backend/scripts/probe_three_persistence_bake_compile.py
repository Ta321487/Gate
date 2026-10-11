"""探针：DOMAIN_GROUPS 全部域 × jdbc/mybatis/jpa bake + mvn compile。

使用独立 GF_DATA_DIR（data/probe_run），避开工厂孤儿清理误删 workspace。
默认扫全族全域；传 --canary 仅各族代表。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

# 必须在 import app.* 之前切换数据目录
_ROOT = Path(__file__).resolve().parents[2]
_PROBE_DATA = _ROOT / "data" / "probe_run"
_PROBE_DATA.mkdir(parents=True, exist_ok=True)
os.environ["GF_DATA_DIR"] = str(_PROBE_DATA)

from app.bake.catalog import _DOMAIN_DEFAULT_ARCH, build_spec  # noqa: E402
from app.bake.domains import DOMAIN_GROUPS, DOMAINS  # noqa: E402
from app.bake.engine import bake_project  # noqa: E402
from app.core.config import get_settings  # noqa: E402

# 各族代表（--canary）
FAMILY_CANARIES: list[tuple[str, str, str, str]] = [
    ("borrow", "DOM-LIBRARY", "图书借阅管理系统", "ARCH-FLOW"),
    ("follow", "DOM-ATTEND", "学生请假销假管理系统", "ARCH-FLOW"),
    ("ticket", "DOM-DORM", "宿舍报修管理系统", "ARCH-FLOW"),
    ("apply", "DOM-ACTIVITY", "校园活动报名管理系统", "ARCH-FLOW"),
    ("approve", "DOM-SEAL", "印章使用审批管理系统", "ARCH-FLOW"),
    ("trade", "DOM-SHOP", "校园二手商城管理系统", "ARCH-TRADE"),
    ("reserve", "DOM-HOSPITAL", "校医院挂号预约管理系统", "ARCH-RESERVE"),
    ("content", "DOM-FORUM", "校园论坛社区管理系统", "ARCH-CONTENT"),
    ("interact", "DOM-SURVEY", "校园问卷调查管理系统", "ARCH-CRUD"),
]


def _all_cases() -> list[tuple[str, str, str, str]]:
    out: list[tuple[str, str, str, str]] = []
    for family, _label, domains in DOMAIN_GROUPS:
        for domain in domains:
            meta = DOMAINS.get(domain) or {}
            title = str(meta.get("label") or domain)
            # 题名补「管理系统」便于匹配，避免过短
            if "管理" not in title:
                title = f"{title}管理系统"
            arch = _DOMAIN_DEFAULT_ARCH.get(domain, "ARCH-CRUD")
            out.append((family, domain, title, arch))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canary", action="store_true", help="仅各族代表域")
    ap.add_argument(
        "--family",
        action="append",
        default=[],
        help="只跑指定族（可重复），如 reserve approve",
    )
    args = ap.parse_args()

    get_settings.cache_clear()
    settings = get_settings()
    cases = FAMILY_CANARIES if args.canary else _all_cases()
    if args.family:
        want = {f.strip() for f in args.family}
        cases = [c for c in cases if c[0] in want]

    results: list[dict[str, str]] = []
    total = len(cases) * 3
    idx = 0
    for family, domain, title, arch in cases:
        for pers in ("jdbc", "mybatis", "jpa"):
            idx += 1
            short = domain.replace("DOM-", "").lower().replace("_", "")
            pid = f"gf-ut-{short}-{pers}-{uuid.uuid4().hex[:6]}"
            dest = settings.workspace_dir / pid
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            spec = build_spec(
                title=title,
                archetype=arch,
                domain=domain,
                theme="gen-ink",
                llm_enabled=False,
                match_mode="recommended",
                confidence=0.9,
                persistence=pers,
            )
            keep = False
            row = {
                "family": family,
                "domain": domain,
                "pers": pers,
                "bake": "",
                "mvn": "",
                "log": "",
            }
            try:
                ws = bake_project(pid, spec, f"{domain}_{pers}")
                pom = ws / "backend" / "pom.xml"
                if not pom.is_file():
                    found = sorted(ws.rglob("pom.xml"))
                    pom = found[0] if found else pom
                if not pom.is_file():
                    row.update(bake="BAKE_OK", mvn="NO_POM", log=str(ws))
                    keep = True
                else:
                    r = subprocess.run(
                        "mvn -q -DskipTests compile",
                        cwd=str(pom.parent),
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=360,
                        shell=True,
                    )
                    out = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
                    ok = r.returncode == 0
                    row.update(
                        bake="BAKE_OK",
                        mvn="MVN_OK" if ok else "MVN_FAIL",
                        log=out[-2500:],
                    )
                    keep = not ok
                if not keep:
                    shutil.rmtree(dest, ignore_errors=True)
            except Exception as e:  # noqa: BLE001
                row.update(bake="BAKE_FAIL", mvn="", log=str(e)[:2500])
            results.append(row)
            ok = row["bake"] == "BAKE_OK" and row["mvn"] == "MVN_OK"
            print(
                f"{'OK' if ok else 'FAIL':4} [{idx}/{total}] "
                f"{family:8} {domain:20} {pers:7} {row['bake']} {row['mvn']}",
                flush=True,
            )
            if not ok and row["log"]:
                print(row["log"][-1600:], flush=True)
                print("---", flush=True)

    fail = sum(1 for r in results if not (r["bake"] == "BAKE_OK" and r["mvn"] == "MVN_OK"))
    out_path = _PROBE_DATA / "probe_all_domains_result.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY fail=", fail, "total=", len(results), flush=True)
    print("probe_data=", settings.workspace_dir, flush=True)
    print("result_json=", out_path, flush=True)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
