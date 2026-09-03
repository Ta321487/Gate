# -*- coding: utf-8 -*-
"""One-shot acceptance for gf-accept-ai-farm bake."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ws = Path(r"D:\graduate_factory_v3\data\workspace\gf-accept-ai-farm")
checks: list[tuple[bool, str, str]] = []


def ok(name: str, cond: bool, detail: str = "") -> None:
    checks.append((bool(cond), name, detail))


def main() -> None:
    spec = json.loads((ws / "spec.json").read_text(encoding="utf-8"))
    caps = spec.get("capabilities") or []
    ok("cap ai_assistant", "ai_assistant" in caps)
    ok("spec.ai_assistant true", bool(spec.get("ai_assistant")))

    sql = (ws / "sql" / "schema.sql").read_text(encoding="utf-8")
    ok("SQL sys_ai_knowledge", "sys_ai_knowledge" in sql)
    ok("SQL sys_ai_message", "sys_ai_message" in sql)
    ok("SQL sys_ai_feedback", "sys_ai_feedback" in sql)
    ok(
        "product cats fruit/veg/grain",
        "水果" in sql and "蔬菜" in sql and "粮油" in sql and "INSERT IGNORE INTO category" in sql,
    )
    ok("AI FAQ has fruit category", "sys_ai_knowledge" in sql and "'水果'" in sql)
    ok("no thesis leak 毕设", "毕设" not in sql)
    ok("no 毕业设计", "毕业设计" not in sql)
    ok("no 演示环境", "演示环境" not in sql)

    pom = (ws / "backend" / "pom.xml").read_text(encoding="utf-8")
    ok("pom spring-ai-bom", "spring-ai-bom" in pom)
    ok("pom spring-ai-deepseek", "spring-ai-deepseek" in pom)

    be = ws / "backend"
    ok("DeepSeekClient", any(be.rglob("DeepSeekClient.java")))
    ok("AiBizContext", any(be.rglob("AiBizContext.java")))
    ok("AiAssistantStore", any(be.rglob("AiAssistantStore.java")))
    ok("AiAssistantController", any(be.rglob("AiAssistantController.java")))
    ok("AiAssistantFloat", any((ws / "frontend").rglob("AiAssistantFloat.vue")))
    portal = (ws / "frontend" / "src" / "layouts" / "PortalLayout.vue").read_text(encoding="utf-8")
    ok("PortalLayout float", "AiAssistantFloat" in portal)

    ds = next(be.rglob("DeepSeekClient.java")).read_text(encoding="utf-8")
    ok("Spring AI DeepSeekChatModel", "DeepSeekChatModel" in ds)
    biz = next(be.rglob("AiBizContext.java")).read_text(encoding="utf-8")
    for name in (
        "OrderStore",
        "ArchiveStore",
        "TicketStore",
        "SlotStore",
        "RecommendStore",
        "ExamStore",
    ):
        ok(f"Biz {name}", name in biz)
    ok("Biz no invent SQL", "CREATE TABLE" not in biz)

    store = next(be.rglob("AiAssistantStore.java")).read_text(encoding="utf-8")
    ok("no 毕业设计演示 prompt", "毕业设计演示" not in store)
    ok("ask uses AiBizContext", "AiBizContext.buildExcerpt" in store)

    yml = (ws / "backend" / "src" / "main" / "resources" / "application.yml").read_text(
        encoding="utf-8"
    )
    ok("yml DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY" in yml)

    readme = (ws / "README.md").read_text(encoding="utf-8")
    ok("README Spring AI", "Spring AI" in readme)
    ok("README DeepSeek", "DeepSeek" in readme)
    ok("README key", "DEEPSEEK_API_KEY" in readme)
    ok("README float", "悬浮" in readme)

    float_vue = next((ws / "frontend").rglob("AiAssistantFloat.vue")).read_text(encoding="utf-8")
    ok("UI upload not 识图演示", "上传图片" in float_vue and "识图演示" not in float_vue)

    menus = ((spec.get("schema") or {}).get("menus") or {}).get("user") or []
    ok(
        "user menu ai_assistant",
        any(isinstance(m, dict) and m.get("key") == "ai_assistant" for m in menus),
    )

    r = subprocess.run(
        "mvn -q -DskipTests compile",
        cwd=str(ws / "backend"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    ok("student backend compile", r.returncode == 0, (r.stderr or r.stdout or "")[-400:])

    print("=== ACCEPTANCE gf-accept-ai-farm ===")
    fail = 0
    for good, name, detail in checks:
        mark = "PASS" if good else "FAIL"
        if not good:
            fail += 1
        line = f"{mark}  {name}"
        if detail and not good:
            line += f"  :: {detail[:200]}"
        print(line)
    print(f"--- {len(checks) - fail}/{len(checks)} passed, {fail} failed ---")
    print("WORKSPACE", ws)


if __name__ == "__main__":
    main()
