"""jdbc bake + mvn compile 探针（slow）。

盖住「骨架能编、但 bake 写出的 AppPolicy 缺常量」这类出包路径。
工厂出包页仍自动 build_verify，无需开关。

探针域用 DOM-ATTEND（出包稳）。mybatis/jpa 叠层洁净契约另案（见
``test_persistence_bake``）；overlay 不是完整工程，不能单独 mvn。
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from app.bake.catalog import build_spec
from app.bake.engine import bake_project
from app.core.config import get_settings
from app.llm.agents_fix import _mvn_compile


def _require_mvn_or_skip() -> None:
    if not shutil.which("mvn"):
        pytest.skip("本机未安装 mvn，跳过 bake+compile 探针")


def _rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


@pytest.mark.slow
def test_attend_jdbc_bake_mvn_compile_probe() -> None:
    """DOM-ATTEND jdbc 出包后须写出完整 AppPolicy 且 backend 能编过。"""
    _require_mvn_or_skip()
    settings = get_settings()
    # 唯一 pid，避免并发/残留目录导致 Windows 读文件失败
    pid = f"gf-ut-bake-mvn-{uuid.uuid4().hex[:10]}"
    dest = settings.workspace_dir / pid
    _rmtree(dest)

    spec = build_spec(
        title="学生请假销假管理系统",
        archetype="ARCH-FLOW",
        domain="DOM-ATTEND",
        theme="gen-ink",
        llm_enabled=False,
        match_mode="recommended",
        confidence=0.9,
        persistence="jdbc",
    )

    ws: Path | None = None
    try:
        ws = bake_project(pid, spec, "bake_mvn_jdbc")
        assert (ws / "backend" / "pom.xml").is_file()
        app_policy = list((ws / "backend").rglob("AppPolicy.java"))
        assert app_policy, "缺 AppPolicy.java"
        text = app_policy[0].read_text(encoding="utf-8")
        assert "SLOT_REQUIRE_CONFIRM" in text, "AppPolicy 缺预约侧常量（bake 写瘦）"
        assert "CANCEL_FREE_HOURS" in text, "AppPolicy 缺 CANCEL_FREE_HOURS"
        # 编译前确认源码可读（挡「目录半删 / 锁文件」假红）
        sample = next((ws / "backend").rglob("*Application.java"), None)
        assert sample is not None and sample.is_file(), "缺 Spring Boot Application"
        sample.read_bytes()
        ok, log = _mvn_compile(ws)
        if ok and "未检测到 mvn" in (log or ""):
            pytest.skip("本机未安装 mvn，跳过 bake+compile 探针")
        assert ok, f"jdbc bake 探针 mvn compile 失败:\n{(log or '')[-2500:]}"
    finally:
        _rmtree(ws if ws is not None else dest)
