"""学生项目前后端进程启停（本机）。"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from shutil import which
from typing import Optional, TextIO

from app.core.config import get_settings

# Vite / chalk 等彩色日志；纯文本 UI 需剥掉，否则显示成 [32m 乱码
_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


@dataclass
class ProcHandle:
    pid: int
    log_path: Path
    process: subprocess.Popen


@dataclass
class RuntimeStore:
    backends: dict[str, ProcHandle] = field(default_factory=dict)
    frontends: dict[str, ProcHandle] = field(default_factory=dict)


STORE = RuntimeStore()

# 残缺 node_modules 的典型症状：目录在但关键包缺失
_FE_REQUIRED_PKG_MARKERS = (
    "node_modules/vue/package.json",
    "node_modules/element-plus/package.json",
    "node_modules/@element-plus/icons-vue/package.json",
    "node_modules/@ctrl/tinycolor/package.json",
    "node_modules/vite/package.json",
)


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text or "")


def _tail(path: Path, n: int = 40) -> str:
    if not path.exists():
        return "等待启动…"
    raw = path.read_text(encoding="utf-8", errors="ignore")
    lines = _strip_ansi(raw).splitlines()
    return "\n".join(lines[-n:]) or "（空）"


def _kill(handle: ProcHandle) -> None:
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(handle.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            os.killpg(os.getpgid(handle.pid), signal.SIGTERM)
    except Exception:  # noqa: BLE001
        try:
            handle.process.kill()
        except Exception:  # noqa: BLE001
            pass


def _listening_ports_win() -> dict[int, set[int]]:
    """一次 netstat：port -> pids（仅 LISTENING）。"""
    out_map: dict[int, set[int]] = {}
    try:
        out = subprocess.check_output(
            ["netstat", "-ano", "-p", "TCP"],
            text=True,
            errors="ignore",
        )
    except Exception:  # noqa: BLE001
        return out_map
    for line in out.splitlines():
        if "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        local = parts[1] if parts[0].upper().startswith("TCP") else parts[0]
        if ":" not in local:
            continue
        try:
            port = int(local.rsplit(":", 1)[-1])
            pid = int(parts[-1])
        except ValueError:
            continue
        if port > 0 and pid > 0:
            out_map.setdefault(port, set()).add(pid)
    return out_map


def listening_tcp_ports() -> set[int]:
    """当前本机 TCP LISTENING 端口集合（供系统页/批量清理，避免逐端口探测）。"""
    if sys.platform == "win32":
        return set(_listening_ports_win())
    ports: set[int] = set()
    try:
        out = subprocess.check_output(
            ["ss", "-lntH"],
            text=True,
            errors="ignore",
        )
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            local = parts[3]
            if ":" not in local:
                continue
            try:
                ports.add(int(local.rsplit(":", 1)[-1]))
            except ValueError:
                continue
    except Exception:  # noqa: BLE001
        pass
    return ports


def _pids_on_port(port: int) -> list[int]:
    """查出占用端口的 PID（工厂重启后 STORE 会丢，必须按端口杀）。"""
    if sys.platform == "win32":
        return sorted(_listening_ports_win().get(port, ()))
    pids: set[int] = set()
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f"tcp:{port}"],
            text=True,
            errors="ignore",
        )
        for tok in out.split():
            try:
                pids.add(int(tok))
            except ValueError:
                pass
    except Exception:  # noqa: BLE001
        return []
    return sorted(pids)


def _kill_port(port: int) -> None:
    for pid in _pids_on_port(port):
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    check=False,
                )
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception:  # noqa: BLE001
            pass


def _resolve_cmd(name: str) -> Optional[str]:
    """Windows 下优先 .cmd/.bat，避免 CreateProcess 找不到无扩展名脚本。"""
    if sys.platform == "win32":
        for cand in (f"{name}.cmd", f"{name}.bat", name):
            found = which(cand)
            if found:
                return found
        return None
    return which(name)


def _creationflags() -> int:
    if sys.platform == "win32":
        return subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    return 0


def _popen(cmd: list[str], *, cwd: Path, log_f, env: Optional[dict] = None) -> subprocess.Popen:
    use_shell = sys.platform == "win32"
    if use_shell:
        from subprocess import list2cmdline

        args: str | list[str] = list2cmdline(cmd)
    else:
        args = cmd
    return subprocess.Popen(
        args,
        cwd=str(cwd),
        stdout=log_f,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=_creationflags(),
        shell=use_shell,
    )


def _http_ok(url: str, timeout: float = 0.35) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 500
    except Exception:  # noqa: BLE001
        return False


def _log_has_fe_fatal(text: str) -> bool:
    needles = (
        "Could not resolve",
        "Build failed",
        "npm ERR!",
        "ERESOLVE",
        "ENOENT",
        "ERROR start frontend",
        "deps incomplete",
        "npm install FAILED",
    )
    return any(n in text for n in needles)


def frontend_deps_ok(fe: Path) -> bool:
    return all((fe / rel).exists() for rel in _FE_REQUIRED_PKG_MARKERS)


def detach_frontend_deps(workspace: Path) -> None:
    """删除工作区前先卸掉 node_modules 联接，避免 rmtree 误删共享缓存。"""
    fe = workspace / "frontend"
    if fe.is_dir():
        _remove_node_modules(fe)


def _remove_node_modules(fe: Path) -> None:
    nm = fe / "node_modules"
    if not nm.exists() and not nm.is_symlink():
        try:
            if hasattr(nm, "is_junction") and nm.is_junction():
                pass
            else:
                return
        except OSError:
            return
    try:
        is_link = nm.is_symlink() or (hasattr(nm, "is_junction") and nm.is_junction())
        if is_link:
            # 联接 / 符号链接：只删入口，不动目标
            if sys.platform == "win32":
                subprocess.run(
                    ["cmd", "/c", "rmdir", str(nm)],
                    check=False,
                    capture_output=True,
                )
            nm.unlink(missing_ok=True)
        else:
            shutil.rmtree(nm, ignore_errors=True)
            if nm.exists() and sys.platform == "win32":
                subprocess.run(
                    ["cmd", "/c", "rmdir", "/s", "/q", str(nm)],
                    check=False,
                    capture_output=True,
                )
    except OSError:
        if sys.platform == "win32":
            subprocess.run(
                ["cmd", "/c", "rmdir", str(nm)],
                check=False,
                capture_output=True,
            )
        shutil.rmtree(nm, ignore_errors=True)


def _link_node_modules(cache_nm: Path, fe: Path) -> None:
    """把共享 node_modules 挂到项目 frontend（Windows 目录联接 / 其它系统 symlink）。"""
    _remove_node_modules(fe)
    dest = fe / "node_modules"
    if sys.platform == "win32":
        r = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dest), str(cache_nm)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not dest.exists():
            raise RuntimeError((r.stderr or r.stdout or "mklink failed").strip())
    else:
        dest.symlink_to(cache_nm, target_is_directory=True)


def prepare_frontend_deps(fe: Path, npm: str, log_f: TextIO) -> None:
    """
    确保 frontend 依赖可用。
    首次：在 data/cache/baseline-frontend 里 npm install 一次；
    之后：目录联接/软链到各项目，跳过重复安装（Windows 上可省数分钟）。
    """
    if frontend_deps_ok(fe):
        log_f.write("deps ok · skip npm install\n")
        log_f.flush()
        return

    pkg = fe / "package.json"
    if not pkg.exists():
        raise RuntimeError("frontend/package.json 不存在")

    settings = get_settings()
    cache = settings.cache_dir / "baseline-frontend"
    cache.mkdir(parents=True, exist_ok=True)
    cache_pkg = cache / "package.json"
    pkg_text = pkg.read_text(encoding="utf-8")

    cache_stale = (not frontend_deps_ok(cache)) or (
        not cache_pkg.exists() or cache_pkg.read_text(encoding="utf-8") != pkg_text
    )
    if cache_stale:
        log_f.write("warming shared frontend cache (npm install once) …\n")
        log_f.flush()
        cache_pkg.write_text(pkg_text, encoding="utf-8")
        lock = fe / "package-lock.json"
        if lock.exists():
            shutil.copy2(lock, cache / "package-lock.json")
        _remove_node_modules(cache)
        r = subprocess.run(
            [npm, "install"],
            cwd=str(cache),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        if r.returncode != 0 or not frontend_deps_ok(cache):
            tail = (r.stderr or r.stdout or "")[-2000:]
            log_f.write(f"npm install FAILED in cache\n{tail}\n")
            log_f.flush()
            raise RuntimeError("共享前端依赖安装失败，见 frontend.log")
        log_f.write("shared cache ready\n")
        log_f.flush()
    else:
        log_f.write("shared frontend cache hit\n")
        log_f.flush()

    try:
        _link_node_modules(cache / "node_modules", fe)
        log_f.write("linked node_modules ← data/cache/baseline-frontend\n")
        log_f.flush()
    except Exception as e:  # noqa: BLE001
        log_f.write(f"link failed ({e}); copying node_modules …\n")
        log_f.flush()
        _remove_node_modules(fe)
        shutil.copytree(cache / "node_modules", fe / "node_modules")

    if not frontend_deps_ok(fe):
        raise RuntimeError("前端依赖仍不完整")


def start_backend(project_id: str, workspace: Path, port: int, db_name: str = "") -> str:
    stop_backend(project_id, port)
    settings = get_settings()
    log_dir = settings.logs_dir / project_id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "backend.log"
    be = workspace / "backend"

    # 先落库再启 Spring，避免无库/空库启动失败
    if db_name:
        from app.services.student_db import datasource_env, ensure_student_schema

        try:
            ensure_student_schema(workspace, db_name)
        except RuntimeError as e:
            with open(log_path, "w", encoding="utf-8") as lf:
                lf.write(f"--- start port={port} ---\nERROR ensure DB: {e}\n")
            raise

    mvn = _resolve_cmd("mvn")
    log_f = open(log_path, "w", encoding="utf-8")
    log_f.write(f"--- start port={port} db={db_name or '-'} ---\n")
    log_f.flush()

    env = os.environ.copy()
    if db_name:
        from app.services.student_db import datasource_env

        env.update(datasource_env(db_name))
        log_f.write(f"datasource: {env.get('SPRING_DATASOURCE_URL')}\n")
        log_f.flush()

    try:
        if (be / "pom.xml").exists() and mvn:
            args = [f"--server.port={port}"]
            cmd = [
                mvn,
                "-q",
                "spring-boot:run",
                f"-Dspring-boot.run.arguments={' '.join(args)}",
            ]
            log_f.write(f"cmd: {cmd[0]} spring-boot:run port={port}\n")
            log_f.flush()
            p = _popen(cmd, cwd=be, log_f=log_f, env=env)
        else:
            stub = log_dir / "_be_stub.py"
            stub.write_text(
                f"""
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'OK')
    def log_message(self, *a): pass
print('stub backend on {port} (no mvn)')
HTTPServer(('127.0.0.1', {port}), H).serve_forever()
""",
                encoding="utf-8",
            )
            log_f.write("fallback: python stub (mvn not found)\n")
            log_f.flush()
            p = _popen([sys.executable, str(stub)], cwd=log_dir, log_f=log_f, env=env)
    except Exception as e:  # noqa: BLE001
        log_f.write(f"ERROR start backend: {e}\n")
        log_f.flush()
        log_f.close()
        raise RuntimeError(f"后端启动失败: {e}") from e

    STORE.backends[project_id] = ProcHandle(pid=p.pid, log_path=log_path, process=p)
    return _tail(log_path)


def _clear_vite_cache(fe: Path, log_f: TextIO) -> None:
    """清掉 Vite 预构建缓存。共享 node_modules 时默认写在联接目录里，Windows 易 EBUSY。"""
    for rel in (".vite", "node_modules/.vite"):
        target = fe / rel
        if not target.exists():
            continue
        shutil.rmtree(target, ignore_errors=True)
        # Windows 偶发删不净：再清 deps_temp_*
        if target.exists() and target.is_dir():
            for child in target.iterdir():
                if child.name.startswith("deps_temp"):
                    shutil.rmtree(child, ignore_errors=True)
        log_f.write(f"cleared vite cache: {rel}\n")
        log_f.flush()


def start_frontend(project_id: str, workspace: Path, port: int, backend_port: int) -> str:
    stop_frontend(project_id, port)
    settings = get_settings()
    log_dir = settings.logs_dir / project_id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "frontend.log"
    fe = workspace / "frontend"

    npm = _resolve_cmd("npm")
    log_f = open(log_path, "w", encoding="utf-8")
    log_f.write(f"--- start port={port} proxy={backend_port} ---\n")
    log_f.flush()

    try:
        if (fe / "package.json").exists() and npm:
            env = os.environ.copy()
            env["VITE_API_PROXY"] = f"http://127.0.0.1:{backend_port}"
            # 关闭彩色输出，避免前端日志里 ESC 码在运营端显示成乱码
            env["NO_COLOR"] = "1"
            env["FORCE_COLOR"] = "0"
            env["npm_config_color"] = "false"
            # 共享缓存联接 node_modules，避免每题全量 npm install
            prepare_frontend_deps(fe, npm, log_f)
            _clear_vite_cache(fe, log_f)
            if sys.platform == "win32":
                lines = [
                    "@echo off",
                    f'cd /d "{fe}"',
                    "echo deps ready · starting vite",
                    f'call "{npm}" run dev -- --host 127.0.0.1 --port {port}',
                    "exit /b %ERRORLEVEL%",
                ]
                script = log_dir / "_start_fe.cmd"
                script.write_text("\r\n".join(lines), encoding="utf-8")
                log_f.write(f"cmd: {script.name}\n")
                log_f.flush()
                p = subprocess.Popen(
                    ["cmd.exe", "/c", str(script)],
                    cwd=str(fe),
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    env=env,
                    creationflags=_creationflags(),
                )
            else:
                script = log_dir / "_start_fe.sh"
                script.write_text(
                    f"""#!/bin/sh
cd "{fe}" || exit 1
echo "deps ready · starting vite"
exec "{npm}" run dev -- --host 127.0.0.1 --port {port}
""",
                    encoding="utf-8",
                )
                script.chmod(0o755)
                log_f.write(f"cmd: {script.name}\n")
                log_f.flush()
                p = subprocess.Popen(
                    ["/bin/sh", str(script)],
                    cwd=str(fe),
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    env=env,
                )
        else:
            stub = log_dir / "_fe_stub.py"
            stub.write_text(
                f"""
from http.server import BaseHTTPRequestHandler, HTTPServer
html = b'<html><body><h1>Thesis Preview Stub</h1></body></html>'
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers(); self.wfile.write(html)
    def log_message(self, *a): pass
print('stub frontend on {port}')
HTTPServer(('127.0.0.1', {port}), H).serve_forever()
""",
                encoding="utf-8",
            )
            log_f.write("fallback: python stub (npm not found)\n")
            log_f.flush()
            p = _popen([sys.executable, str(stub)], cwd=log_dir, log_f=log_f)
    except Exception as e:  # noqa: BLE001
        log_f.write(f"ERROR start frontend: {e}\n")
        log_f.flush()
        log_f.close()
        raise RuntimeError(f"前端启动失败: {e}") from e

    STORE.frontends[project_id] = ProcHandle(pid=p.pid, log_path=log_path, process=p)
    return _tail(log_path)


def stop_backend(project_id: str, port: int | None = None) -> None:
    h = STORE.backends.pop(project_id, None)
    if h:
        _kill(h)
    if port is not None:
        _kill_port(port)
    _mark_log_stopped(project_id, "backend")


def stop_frontend(project_id: str, port: int | None = None) -> None:
    h = STORE.frontends.pop(project_id, None)
    if h:
        _kill(h)
    if port is not None:
        _kill_port(port)
    _mark_log_stopped(project_id, "frontend")


def _mark_log_stopped(project_id: str, side: str) -> None:
    """停止后截断日志，避免 UI 仍展示上次启动输出造成误导。"""
    settings = get_settings()
    path = settings.logs_dir / project_id / f"{side}.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("--- stopped ---\n", encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def stop_all(
    project_id: str,
    backend_port: int | None = None,
    frontend_port: int | None = None,
) -> None:
    """停句柄 + 按端口清孤儿进程（工厂 API 重启后 STORE 会丢）。"""
    stop_backend(project_id, backend_port)
    stop_frontend(project_id, frontend_port)


def backend_running(project_id: str) -> bool:
    h = STORE.backends.get(project_id)
    return bool(h and h.process.poll() is None)


def frontend_running(project_id: str) -> bool:
    h = STORE.frontends.get(project_id)
    return bool(h and h.process.poll() is None)


def backend_status(project_id: str, port: int) -> str:
    """stopped | starting | healthy | error —— 以端口可服务为准（不依赖进程表是否丢过）。"""
    if (
        _http_ok(f"http://127.0.0.1:{port}/actuator/health")
        or _http_ok(f"http://127.0.0.1:{port}/api/meta")
        or _http_ok(f"http://127.0.0.1:{port}/")
    ):
        return "healthy"
    if backend_running(project_id):
        log = backend_log(project_id)
        if "BUILD FAILURE" in log or "ERROR start backend" in log:
            return "error"
        return "starting"
    return "stopped"


def frontend_status(project_id: str, port: int) -> str:
    """stopped | starting | healthy | error"""
    if _http_ok(f"http://127.0.0.1:{port}/"):
        return "healthy"
    if frontend_running(project_id):
        log = frontend_log(project_id)
        if _log_has_fe_fatal(log):
            return "error"
        return "starting"
    return "stopped"


def backend_log(project_id: str) -> str:
    h = STORE.backends.get(project_id)
    if h:
        return _tail(h.log_path)
    settings = get_settings()
    return _tail(settings.logs_dir / project_id / "backend.log")


def frontend_log(project_id: str) -> str:
    h = STORE.frontends.get(project_id)
    if h:
        return _tail(h.log_path)
    settings = get_settings()
    return _tail(settings.logs_dir / project_id / "frontend.log")


def job_log(project_id: str) -> str:
    settings = get_settings()
    return _tail(settings.logs_dir / project_id / "job.log", 200)


async def allocate_ports(used_be: set[int], used_fe: set[int]) -> tuple[int, int]:
    s = get_settings()
    be = next(p for p in range(s.backend_port_start, s.backend_port_end + 1) if p not in used_be)
    fe = next(p for p in range(s.frontend_port_start, s.frontend_port_end + 1) if p not in used_fe)
    return be, fe


def side_active(
    project_id: str,
    port: int | None,
    side: str,
    listening: set[int] | None = None,
) -> bool:
    """是否仍占用端口：进程表在跑，或端口 LISTENING（不打 HTTP，避免系统页卡死）。"""
    if not port:
        return False
    if side == "backend" and backend_running(project_id):
        return True
    if side == "frontend" and frontend_running(project_id):
        return True
    if listening is not None:
        return port in listening
    return bool(_pids_on_port(port))


def free_idle_ports(
    project_id: str,
    backend_port: int | None,
    frontend_port: int | None,
    listening: set[int] | None = None,
) -> bool:
    """清理工厂未托管但仍占端口的进程；本进程表仍在跑的跳过。"""
    if backend_running(project_id) or frontend_running(project_id):
        return False
    listen = listening if listening is not None else listening_tcp_ports()
    had = bool(
        STORE.backends.get(project_id)
        or STORE.frontends.get(project_id)
        or (backend_port and backend_port in listen)
        or (frontend_port and frontend_port in listen)
    )
    if not had:
        return False
    stop_all(project_id, backend_port or None, frontend_port or None)
    return True
