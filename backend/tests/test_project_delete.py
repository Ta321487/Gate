"""删除项目：磁盘清理可靠 + 库名避开本机残留。"""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.bake.naming import student_db_name
from app.services import projects as project_svc
from app.services.student_db import _is_droppable_student_db


class TestRemoveTreeReliable(unittest.TestCase):
    def test_removes_dir(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            (root / "a").mkdir(parents=True)
            (root / "a" / "f.txt").write_text("x", encoding="utf-8")
            project_svc.remove_tree_reliable(root)
            self.assertFalse(root.exists())

    def test_missing_ok(self) -> None:
        project_svc.remove_tree_reliable(Path("/nonexistent/path/xyz_gf_test"))


class TestPurgeProjectDisk(unittest.TestCase):
    def test_clears_workspace_and_zips(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ws = base / "gf-demo"
            ws.mkdir()
            (ws / "readme.txt").write_text("ok", encoding="utf-8")
            zip1 = base / "gf-demo-thesis-app.zip"
            zip2 = base / "gf-demo-dorm.zip"
            zip1.write_bytes(b"PK")
            zip2.write_bytes(b"PK")
            logs = base / "logs" / "gf-demo"
            logs.mkdir(parents=True)
            (logs / "job.log").write_text("x", encoding="utf-8")

            p = SimpleNamespace(
                id="gf-demo",
                workspace_path=str(ws),
                zip_path=str(zip1),
            )
            with (
                patch("app.services.projects.get_settings") as gs,
                patch("app.services.projects.rt.detach_frontend_deps"),
            ):
                settings = SimpleNamespace(workspace_dir=base, logs_dir=base / "logs")
                gs.return_value = settings
                project_svc.purge_project_disk(p)

            self.assertFalse(ws.exists())
            self.assertFalse(zip1.exists())
            self.assertFalse(zip2.exists())
            self.assertFalse(logs.exists())


class TestDbNameAvoidsLiveOrphans(unittest.TestCase):
    def test_droppable_filter(self) -> None:
        self.assertTrue(_is_droppable_student_db("dorm_repair"))
        self.assertTrue(_is_droppable_student_db("gf_thesis_x"))
        self.assertFalse(_is_droppable_student_db("mysql"))
        self.assertFalse(_is_droppable_student_db("information_schema"))

    def test_student_db_name_skips_live(self) -> None:
        name = student_db_name(
            "dorm_repair",
            "gf-20260725-215435",
            reserved={"dorm_repair"},
        )
        self.assertEqual(name, "dorm_repair_215435")


class TestPurgeOrphanDisk(unittest.TestCase):
    def test_keeps_alive_removes_orphan(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ws = base / "workspace"
            logs = base / "logs"
            ws.mkdir()
            logs.mkdir()
            (ws / "gf-alive").mkdir()
            (ws / "gf-dead").mkdir()
            (ws / "gf-dead-app.zip").write_bytes(b"PK")
            (ws / "gf-alive-app.zip").write_bytes(b"PK")
            (logs / "gf-alive").mkdir()
            (logs / "gf-dead").mkdir()
            (logs / "notes.txt").write_text("keep", encoding="utf-8")

            with (
                patch("app.services.projects.get_settings") as gs,
                patch("app.services.projects.rt.detach_frontend_deps"),
            ):
                gs.return_value = SimpleNamespace(workspace_dir=ws, logs_dir=logs)
                data = project_svc.purge_orphan_project_disk({"gf-alive"})

            self.assertTrue((ws / "gf-alive").is_dir())
            self.assertFalse((ws / "gf-dead").exists())
            self.assertTrue((ws / "gf-alive-app.zip").is_file())
            self.assertFalse((ws / "gf-dead-app.zip").exists())
            self.assertTrue((logs / "gf-alive").is_dir())
            self.assertFalse((logs / "gf-dead").exists())
            self.assertTrue((logs / "notes.txt").is_file())
            self.assertIn("gf-dead", data["removed_workspaces"])
            self.assertIn("gf-dead", data["removed_logs"])
            self.assertEqual(data["errors"], [])


class TestSourceCleanup(unittest.TestCase):
    def test_skips_when_shared(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            uploads = Path(td)
            f = uploads / "a_bundle" / "开题.docx"
            f.parent.mkdir()
            f.write_bytes(b"x")
            with patch("app.services.projects.get_settings") as gs:
                gs.return_value = SimpleNamespace(uploads_dir=uploads)
                project_svc.remove_project_source_if_owned(str(f), shared=True)
            self.assertTrue(f.exists())

    def test_removes_bundle(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            uploads = Path(td)
            bundle = uploads / "stamp_0_bundle"
            f = bundle / "开题.docx"
            bundle.mkdir()
            f.write_bytes(b"x")
            with patch("app.services.projects.get_settings") as gs:
                gs.return_value = SimpleNamespace(uploads_dir=uploads)
                project_svc.remove_project_source_if_owned(str(f), shared=False)
            self.assertFalse(bundle.exists())


if __name__ == "__main__":
    unittest.main()
