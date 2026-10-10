"""baseline 骨架后端真实 mvn compile（slow）。

mybatis/jpa overlay 不是完整工程（须叠到 baseline 上），三栈真编见
``test_bake_mvn_compile_probe``。本测拦住加厚改共享骨架时的 javac 硬伤。
出包侧 build_verify 仍自动编学生包。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.llm.agents_fix import _mvn_compile

ROOT = Path(__file__).resolve().parents[2]
_BASELINE = ROOT / "skeletons/baseline"


def _require_mvn_or_skip() -> None:
    if not shutil.which("mvn"):
        pytest.skip("本机未安装 mvn，跳过骨架真编")


@pytest.mark.slow
def test_baseline_skeleton_mvn_compile() -> None:
    """baseline 骨架 backend 必须能 mvn -q -DskipTests compile。"""
    _require_mvn_or_skip()
    assert (_BASELINE / "backend" / "pom.xml").is_file(), "baseline 缺 pom.xml"
    ok, log = _mvn_compile(_BASELINE)
    if ok and "未检测到 mvn" in (log or ""):
        pytest.skip("本机未安装 mvn，跳过骨架真编")
    assert ok, f"baseline 骨架 mvn compile 失败:\n{(log or '')[-2000:]}"
