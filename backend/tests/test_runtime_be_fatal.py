"""预览后端：编译失败须标 error，不能在进程退出后藏成 stopped。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from app.services.runtime import _log_has_be_fatal, backend_status, frontend_deps_ok


def test_log_has_be_fatal_compilation_error_quiet_maven():
    """mvn -q 失败日志常无 BUILD FAILURE，只有 COMPILATION ERROR。"""
    sample = """--- start port=9100 db=agri_shop ---
cmd: mvn spring-boot:run
[ERROR] COMPILATION ERROR :
[ERROR] ... ArchiveStore.java:[710,14] 找不到符号
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.13.0:compile
"""
    assert _log_has_be_fatal(sample)
    assert not _log_has_be_fatal("--- start ---\nTomcat started on port(s): 9100")


def test_backend_status_error_after_process_exits():
    log = "[ERROR] COMPILATION ERROR :\n[ERROR] Failed to execute goal"
    with (
        patch("app.services.runtime._http_ok", return_value=False),
        patch("app.services.runtime.backend_running", return_value=False),
        patch("app.services.runtime.backend_log", return_value=log),
    ):
        assert backend_status("p1", 9100) == "error"


def test_backend_status_stopped_when_clean_exit():
    with (
        patch("app.services.runtime._http_ok", return_value=False),
        patch("app.services.runtime.backend_running", return_value=False),
        patch("app.services.runtime.backend_log", return_value="--- start ---\nTomcat started"),
    ):
        assert backend_status("p1", 9100) == "stopped"


def test_frontend_deps_ok_requires_package_json_deps(tmp_path: Path):
    """旧共享缓存缺 qrcode 时不得判 ok（否则会 skip npm install 导致 Vite 一直 reload）。"""
    for rel in (
        "node_modules/vue/package.json",
        "node_modules/element-plus/package.json",
        "node_modules/@element-plus/icons-vue/package.json",
        "node_modules/@ctrl/tinycolor/package.json",
        "node_modules/vite/package.json",
        "node_modules/qrcode/package.json",
    ):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"vue": "3", "qrcode": "1.5.4", "echarts": "5"},
                "devDependencies": {"vite": "6"},
            }
        ),
        encoding="utf-8",
    )
    assert not frontend_deps_ok(tmp_path)  # echarts 未装
    echarts = tmp_path / "node_modules/echarts/package.json"
    echarts.parent.mkdir(parents=True, exist_ok=True)
    echarts.write_text("{}", encoding="utf-8")
    assert frontend_deps_ok(tmp_path)
