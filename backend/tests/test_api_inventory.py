"""学生端 API 清单：对准工作区 Controller 源码。"""

from __future__ import annotations

from pathlib import Path

from app.bake.api_inventory import load_api_inventory, parse_controller_source


def test_flow_keys_path_need_is_exact_not_prefix():
    src = """
package com.thesis.controller;
@RestController
@RequestMapping("/api/archive")
public class ArchiveController {
  @GetMapping
  public Object page() { return null; }
  @GetMapping("/by-author")
  public Object byAuthor() { return null; }
  @GetMapping("/promo-active")
  public Object promoActive() { return null; }
}
"""
    flow = {
        "flash_price": {
            "file": "ArchiveController.java",
            "need": ["/api/archive", "promoActive"],
        }
    }
    parsed = parse_controller_source(src, rel_file="ArchiveController.java", flow_api=flow)
    assert parsed
    by_handler = {e["handler"]: e["flow_keys"] for e in parsed["endpoints"]}
    assert by_handler["page"] == ["flash_price"]
    assert by_handler["promoActive"] == ["flash_price"]
    assert by_handler["byAuthor"] == []


def test_inventory_matches_controller_mapping_count(tmp_path: Path):
    be = tmp_path / "backend" / "src" / "main" / "java" / "com" / "thesis" / "controller"
    be.mkdir(parents=True)
    (be / "DemoController.java").write_text(
        """
package com.thesis.controller;
@RestController
@RequestMapping("/api/demo")
public class DemoController {
  @GetMapping
  public Object list() { return null; }
  @PostMapping
  public Object create() { return null; }
  @GetMapping("/{id}")
  public Object one() { return null; }
}
""",
        encoding="utf-8",
    )
    inv = load_api_inventory(tmp_path, {"api_style": {"item_ref": "path", "cart_mutate": "path"}})
    assert inv["count"] == 3
    assert {(e["method"], e["path"]) for e in inv["endpoints"]} == {
        ("GET", "/api/demo"),
        ("POST", "/api/demo"),
        ("GET", "/api/demo/{id}"),
    }


def test_baseline_inventory_parity_with_controller_sources():
    """基线骨架：清单条数 = 各 *Controller.java 可解析 Mapping 之和（不准少列）。"""
    root = Path(__file__).resolve().parents[2]
    ws = root / "skeletons" / "baseline"
    inv = load_api_inventory(ws, {})
    assert inv and inv["count"] > 0
    be = ws / "backend" / "src" / "main" / "java"
    expected = 0
    for path in be.rglob("*Controller.java"):
        parsed = parse_controller_source(
            path.read_text(encoding="utf-8", errors="ignore"),
            rel_file=path.name,
        )
        if parsed:
            expected += len(parsed["endpoints"])
    assert inv["count"] == expected
