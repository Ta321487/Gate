"""填岛 SSE 快照合并。"""

from __future__ import annotations

import unittest

from app.services.fill_events import FillEventHub, _merge_event, _empty_snapshot


class FillEventsTest(unittest.TestCase):
    def test_merge_plan_and_units(self) -> None:
        snap = _empty_snapshot()
        _merge_event(
            snap,
            {
                "type": "fill_plan",
                "total": 2,
                "units": [
                    {"id": "er.labels", "kind": "er_labels", "budget_chars": 1000, "source_refs": ["a"]},
                    {"id": "module.labels", "kind": "module_labels", "budget_chars": 800, "source_refs": []},
                ],
            },
        )
        self.assertEqual(snap["total"], 2)
        self.assertEqual(snap["phase"], "running")
        _merge_event(snap, {"type": "unit_started", "unit_id": "er.labels", "kind": "er_labels"})
        self.assertEqual(snap["units"]["er.labels"]["status"], "running")
        self.assertEqual(snap["running"], 1)
        _merge_event(snap, {"type": "unit_done", "unit_id": "er.labels"})
        self.assertEqual(snap["units"]["er.labels"]["status"], "done")
        self.assertEqual(snap["done"], 1)
        self.assertEqual(snap["running"], 0)
        _merge_event(snap, {"type": "fill_complete"})
        self.assertEqual(snap["phase"], "done")

    def test_skipped_unit_not_counted_as_failed(self) -> None:
        snap = _empty_snapshot()
        _merge_event(
            snap,
            {
                "type": "fill_plan",
                "total": 1,
                "units": [{"id": "er.labels", "kind": "er_labels", "budget_chars": 1, "source_refs": []}],
            },
        )
        _merge_event(snap, {"type": "unit_started", "unit_id": "er.labels"})
        _merge_event(snap, {"type": "unit_skipped", "unit_id": "er.labels"})
        self.assertEqual(snap["units"]["er.labels"]["status"], "skipped")
        self.assertEqual(snap["failed"], 0)
        self.assertEqual(snap["running"], 0)

    def test_fill_failed_sets_phase(self) -> None:
        snap = _empty_snapshot()
        _merge_event(snap, {"type": "fill_failed", "error": "boom"})
        self.assertEqual(snap["phase"], "failed")
        self.assertEqual(snap["error"], "boom")

    def test_hub_snapshot_roundtrip(self) -> None:
        async def run() -> None:
            hub = FillEventHub()
            await hub.handle(
                "p1",
                {
                    "type": "fill_plan",
                    "total": 1,
                    "units": [{"id": "u1", "kind": "er_labels", "budget_chars": 1, "source_refs": []}],
                },
            )
            snap = hub.snapshot("p1")
            self.assertEqual(snap["total"], 1)
            await hub.handle("p1", {"type": "fill_complete"})

        import asyncio

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
