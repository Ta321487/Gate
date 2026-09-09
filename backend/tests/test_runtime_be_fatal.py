"""预览后端：编译失败须标 error，不能在进程退出后藏成 stopped。"""

from __future__ import annotations

from unittest.mock import patch

from app.services.runtime import _log_has_be_fatal, backend_status


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
