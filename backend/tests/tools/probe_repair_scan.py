"""不 bake：探针报修三域扫词挂载。backend/ 下: python tests/tools/probe_repair_scan.py"""

from __future__ import annotations

from pathlib import Path

from app.bake.domain_schema import attach_accept
from app.bake.domains import DOMAIN_CAPABILITIES
from app.bake.staff_posts import staff_posts_for_domain

ROOT = Path(__file__).resolve().parents[3]
SAMPLES = ROOT / "data" / "samples" / "域开题样例近五年"

CASES = [
    ("DORM", "DOM-DORM", "11-DOM-DORM-学生宿舍报修管理系统.txt"),
    ("PROP", "DOM-PROPERTY", "12-DOM-PROPERTY-智慧社区物业报修管理系统.txt"),
    ("IT", "DOM-IT", "13-DOM-IT-校园网故障报修与 IT 运维工单系统.txt"),
]


def main() -> None:
    print("--- 样例开题扫挂 ---")
    for name, dom, fn in CASES:
        text = (SAMPLES / fn).read_text(encoding="utf-8")
        spec = attach_accept(
            {
                "domain": dom,
                "title": name,
                "capabilities": list(DOMAIN_CAPABILITIES[dom]),
                "features": [],
            },
            text,
        )
        caps = spec.get("capabilities") or []
        ticket = ((spec.get("schema") or {}).get("entities") or {}).get("ticket") or {}
        posts = [p["id"] for p in staff_posts_for_domain(dom, proposal_text=text)]
        print(f"{name}: caps={caps}")
        print(f"      slaDeadline={ticket.get('slaDeadline')} posts={posts}")

    print("--- 空开题仍有催办 ---")
    for dom in ("DOM-DORM", "DOM-PROPERTY", "DOM-IT"):
        spec = attach_accept(
            {
                "domain": dom,
                "title": "x",
                "capabilities": list(DOMAIN_CAPABILITIES[dom]),
                "features": [],
            },
            "提交报修。",
        )
        has = "deadline" in (spec.get("capabilities") or [])
        sla = (
            ((spec.get("schema") or {}).get("entities") or {})
            .get("ticket", {})
            .get("slaDeadline")
        )
        print(dom, "deadline=", has, "sla=", sla)


if __name__ == "__main__":
    main()
