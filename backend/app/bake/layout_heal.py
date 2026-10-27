"""出包前门禁：把布局关键 CSS 与基线对齐。

Profile 换头像槽曾缺 align-self；旧包还有：
- 无 companion ``Profile.css``（样式写死在 Profile.vue 内联）；
- 过期 ``accountFace.css``（stretch 身份栏下 avatar-slot 未自限高）；
- 过期 ``cardVoice.css`` 头注释仍写 ``§2.5`` → p3lean 注记红。

仅「dst 已存在才覆写」会漏 → p3layout / p3lean 仍红。
禁止只擦单包——门禁前从骨架回拷 / 补齐 / 给内联槽打 align-self。
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.config import get_settings

# 相对 frontend/src；布局契约 + 易残留工厂注记的全局皮（可创建缺失文件）。
_LAYOUT_CRITICAL_CSS: tuple[str, ...] = (
    "views/Profile.css",
    "styles/accountFace.css",
    "styles/cardVoice.css",
)

_AVATAR_SLOT_RULE = re.compile(r"(\.avatar-slot\s*\{)([^}]*)(\})", re.I)
_STYLE_SRC_PROFILE = re.compile(
    r"""<style\b[^>]*\bsrc\s*=\s*['\"][^'\"]*Profile\.css['\"][^>]*>\s*</style>""",
    re.I,
)
_INLINE_STYLE_BLOCK = re.compile(
    r"""<style\b(?![^>]*\bsrc\s*=)[^>]*>([\s\S]*?)</style>""",
    re.I,
)


def _ensure_avatar_slot_self_size(text: str) -> str:
    """内联 / companion 里的 .avatar-slot 缺 align-self 时补上，避免 stretch 条把钮拽到底。"""

    def _repl(m: re.Match[str]) -> str:
        head, body, tail = m.group(1), m.group(2), m.group(3)
        if re.search(r"align-self\s*:", body, re.I):
            return m.group(0)
        # 与基线 Profile.css 同口径：槽高跟头像走
        inject = "\n  align-self: flex-start;"
        if body.startswith("\n"):
            return f"{head}{inject}{body}{tail}"
        return f"{head}{inject}\n  {body.lstrip()}{tail}"

    return _AVATAR_SLOT_RULE.sub(_repl, text)


def _avatar_slot_needs_self_size(text: str) -> bool:
    """任一 .avatar-slot 规则体缺 align-self / max-content / fit-content → 需补。"""
    for m in _AVATAR_SLOT_RULE.finditer(text or ""):
        body = m.group(2)
        if re.search(
            r"align-self\s*:|width\s*:\s*max-content|height\s*:\s*fit-content",
            body,
            re.I,
        ):
            continue
        return True
    return False


def _migrate_profile_to_companion(raw: str) -> str:
    """旧内联 Profile → 改挂 companion，去掉会盖掉限高的残缺内联 avatar-slot。"""
    if _STYLE_SRC_PROFILE.search(raw):
        # 已挂 companion：仍把内联里残缺槽补限高（双源时契约认「任一规则自限高」）
        if _avatar_slot_needs_self_size(raw):
            return _ensure_avatar_slot_self_size(raw)
        return raw

    # 无 companion 引用：挂上 Profile.css，并删掉含 avatar-slot 的残缺内联 style
    new = raw
    if "</template>" in new and not _STYLE_SRC_PROFILE.search(new):
        # 插在 script 前或文件末
        link = '\n<style scoped src="./Profile.css"></style>\n'
        if "<script" in new:
            new = re.sub(r"(<script\b)", link + r"\1", new, count=1, flags=re.I)
        else:
            new = new.rstrip() + link

    def _drop_or_patch_style(m: re.Match[str]) -> str:
        body = m.group(1)
        if ".avatar-slot" not in body:
            return m.group(0)
        # 整块只剩槽相关且无自限高 → 删内联，交给 companion
        if _avatar_slot_needs_self_size(body) and body.count("{") <= 3:
            return ""
        return f"<style scoped>{_ensure_avatar_slot_self_size(body)}</style>"

    new = _INLINE_STYLE_BLOCK.sub(_drop_or_patch_style, new)
    if _avatar_slot_needs_self_size(new):
        new = _ensure_avatar_slot_self_size(new)
    return new


def heal_layout_companions_from_baseline(workspace: Path) -> list[str]:
    """回拷/补齐布局关键 CSS；旧 Profile 内联槽补 align-self。返回已写相对路径。"""
    workspace = Path(workspace)
    fe = workspace / "frontend" / "src"
    if not fe.is_dir():
        return []
    sk = get_settings().skeletons_dir / "baseline" / "frontend" / "src"
    if not sk.is_dir():
        return []

    written: list[str] = []
    profile_vue = fe / "views" / "Profile.vue"
    need_profile_css = profile_vue.is_file()

    for rel in _LAYOUT_CRITICAL_CSS:
        src = sk / rel
        dst = fe / rel
        if not src.is_file():
            continue
        # Profile.css：有 Profile 页则允许创建；样式皮：有 styles 或目标父目录可建
        if not dst.is_file():
            if rel == "views/Profile.css" and not need_profile_css:
                continue
            if rel.startswith("styles/") and not (fe / "styles").is_dir():
                if not need_profile_css:
                    continue
                (fe / "styles").mkdir(parents=True, exist_ok=True)
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                clean = src.read_text(encoding="utf-8")
                dst.write_text(clean, encoding="utf-8")
                written.append(("frontend/src/" + rel).replace("\\", "/"))
            except OSError:
                continue
            continue
        try:
            clean = src.read_text(encoding="utf-8")
            cur = dst.read_text(encoding="utf-8")
        except OSError:
            continue
        if clean == cur:
            continue
        dst.write_text(clean, encoding="utf-8")
        written.append(("frontend/src/" + rel).replace("\\", "/"))

    # 旧包：内联残缺槽 → 挂 companion + 限高
    if profile_vue.is_file():
        try:
            raw = profile_vue.read_text(encoding="utf-8")
        except OSError:
            return written
        new = _migrate_profile_to_companion(raw)
        if new != raw:
            profile_vue.write_text(new, encoding="utf-8")
            written.append("frontend/src/views/Profile.vue")

    return written
