from __future__ import annotations

import re
from pathlib import Path

from app.bake.proposal_lexicon import (
    FEATURE_HEAD_TERMS,
    FEATURE_HEAD_RE as _FEATURE_HEAD,
    OUT_HEAD_RE as _OUT_HEAD,
    RESEARCH_WITH_IMPL_RE as _RESEARCH_WITH_IMPL,
    dedupe_out_scope_vs_features,
)

_SECTION = re.compile(r"^[一二三四五六七八九十百]+[、．.]|^第[一二三四五六七八九十\d]+[章节部分]")
_BULLET = re.compile(r"^(\d+[\.、\)）]|[（(]\d+[)）]|[-•·▪])\s*")
# 参考文献 / 进度 / 致谢：对开发匹配是噪声
_NOISE_SECTION = re.compile(
    r"(?:^|\n)\s*(?:#{1,6}\s*)?(?:[七八九十百零〇\d]+[、．.]|[（(]?\d+[)）.、]|第[一二三四五六七八九十\d]+[章节部分])?\s*"
    r"(?:参考文献|参考资料|主要参考资料|进度安排|研究进度|时间安排|致谢|附录)\b"
)
_TITLE_EXPLICIT = re.compile(
    r"(?:题目|课题|课题名称|论文题目|毕业设计题目)\s*[：:\s]\s*(.+)$"
)
_TITLE_HEADING = re.compile(
    r"^(?:[一二三四五六七八九十百]+[、．.]|[（(]?\d+[)）.、])?\s*"
    r"(?:毕业设计题目|论文题目|课题名称|题目)\s*$"
)
_TITLE_TABLE = re.compile(
    r"\|\s*(?:课题名称|题目|毕业设计题目)\s*\|\s*([^|]+?)\s*\|"
)
_TITLE_PHRASE = re.compile(
    r"(?:设计并实现|实现)(?:一个|一套)?(?:基于[\w\-＋+、/]{2,30}的)?"
    r"([\u4e00-\u9fffA-Za-z0-9]{4,36}(?:管理系统|交易平台|信息平台|服务平台|预约系统|申报系统|系统|平台|网站))"
)
_MODULE_LINE = re.compile(
    r"^[\s\d\.、)）（]*([\u4e00-\u9fffA-Za-z0-9、/与及]{4,40}模块)(?:[（(].*[)）])?$"
)
_TABLE_FEAT = re.compile(
    r"^\|\s*(?:F?\d+|编号)?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"
)
_SKIP_TITLE_LINE = re.compile(
    r"^(?:[一二三四五六七八九十]+[、．.]|第[一二三四五六七八九十\d]+|"
    r"学院|专业|学生|学号|指导|开题|选题背景|研究意义|国内外|任务书|"
    r"一是|二是|三是|随着|目前|近年来|\|)"
)
_LEAVE_FEAT = re.compile(
    r"^(?:\d+\.\d+\s*)?(?:拟解决|关键问题|系统测试|测试计划|进度|预期成果|"
    r"研究方法|技术路线|重点研究|非功能)"
)


def _read_docx(path: Path) -> str:
    try:
        from docx import Document

        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:  # noqa: BLE001
        return f"[docx 解析失败: {e}]\n文件名: {path.name}"


def _read_doc_via_word_com(path: Path) -> str | None:
    """Windows + 已装 Microsoft Word：用 COM 抽纯文本。"""
    import sys

    if sys.platform != "win32":
        return None
    src = str(path.resolve())
    # PowerShell 单引号路径，避免空格问题
    ps = (
        "$ErrorActionPreference='Stop'; "
        f"$src = '{src.replace(chr(39), chr(39)+chr(39))}'; "
        "$word = New-Object -ComObject Word.Application; "
        "$word.Visible = $false; "
        "try { "
        "$doc = $word.Documents.Open($src, $false, $true); "
        "$t = $doc.Content.Text; "
        "$doc.Close($false); "
        "$t "
        "} finally { $word.Quit() | Out-Null; "
        "[System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }"
    )
    try:
        import subprocess

        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="ignore",
        )
        if r.returncode != 0:
            return None
        out = (r.stdout or "").strip()
        return out or None
    except Exception:  # noqa: BLE001
        return None


def _read_doc_via_soffice(path: Path) -> str | None:
    """本机有 LibreOffice/OpenOffice 时：转 txt 再读。"""
    import os
    import shutil
    import subprocess
    import tempfile

    bin_name = None
    for cand in ("soffice", "libreoffice"):
        if shutil.which(cand):
            bin_name = cand
            break
    # Windows 常见安装路径
    if not bin_name:
        for p in (
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ):
            if Path(p).exists():
                bin_name = p
                break
    if not bin_name:
        return None
    try:
        with tempfile.TemporaryDirectory(prefix="gf_doc_") as td:
            out_dir = Path(td)
            r = subprocess.run(
                [
                    bin_name,
                    "--headless",
                    "--convert-to",
                    "txt:Text",
                    "--outdir",
                    str(out_dir),
                    str(path.resolve()),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="ignore",
                env={**os.environ, "SAL_USE_VCLPLUGIN": "svp"},
            )
            if r.returncode != 0:
                return None
            # 输出文件名与源同 stem
            txt = out_dir / f"{path.stem}.txt"
            if not txt.exists():
                found = list(out_dir.glob("*.txt"))
                txt = found[0] if found else None
            if not txt or not txt.exists():
                return None
            return txt.read_text(encoding="utf-8", errors="ignore").strip() or None
    except Exception:  # noqa: BLE001
        return None


def _read_doc(path: Path) -> str:
    """旧版 .doc：优先 Word COM，其次 LibreOffice；都没有则提示另存 docx。"""
    text = _read_doc_via_word_com(path)
    if text:
        return text
    text = _read_doc_via_soffice(path)
    if text:
        return text
    return (
        f"[.doc 未能解析] 未检测到可用的 Microsoft Word 或 LibreOffice。\n"
        f"请将「{path.name}」另存为 .docx 后重新上传（.docx 可直接解析）。"
    )


def read_proposal(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        return _read_docx(path)
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            parts = []
            for page in reader.pages:
                t = page.extract_text() or ""
                if t.strip():
                    parts.append(t)
            return "\n".join(parts) or f"PDF 无可提取文本 · {path.name}"
        except Exception as e:  # noqa: BLE001
            return f"[pdf 解析失败: {e}]\n文件名: {path.name}"
    if suffix == ".doc":
        return _read_doc(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def strip_non_dev_sections(text: str) -> str:
    """去掉参考文献/进度/致谢等对匹配无帮助的后半段。

    若整篇从文首就是「参考文献」，返回空串（纯文献材料不计业务）。
    """
    raw = text or ""
    m = _NOISE_SECTION.search(raw)
    if not m:
        return raw
    # 文首即参考文献/进度 → 无业务正文
    if m.start() <= 40:
        return raw[: m.start()].rstrip()
    # 命中点偏后半才裁切，避免正文误伤
    if m.start() < max(200, len(raw) // 5):
        return raw
    return raw[: m.start()].rstrip()


def extract_module_lines(text: str, limit: int = 20) -> list[str]:
    """捞「XXX模块」行——不依赖固定章节标题。"""
    body = strip_non_dev_sections(text)
    out: list[str] = []
    seen: set[str] = set()
    for raw_ln in body.splitlines():
        ln = raw_ln.strip()
        if not ln or len(ln) > 80:
            continue
        m = _MODULE_LINE.match(ln)
        if not m:
            continue
        name = m.group(1).strip()
        if name not in seen:
            seen.add(name)
            out.append(name)
        if len(out) >= limit:
            break
    return out[:limit]


def extract_table_features(text: str, limit: int = 20) -> list[str]:
    """Markdown/Wiki 表格式功能清单：| F1 | 交易 | 购物车下单 |"""
    out: list[str] = []
    seen: set[str] = set()
    for raw_ln in (text or "").splitlines():
        ln = raw_ln.strip()
        if not ln.startswith("|") or re.search(r"\|\s*-+\s*\|", ln):
            continue
        if re.search(r"编号|功能|说明|项目\s*\|", ln) and "注册" not in ln:
            # 表头
            if re.search(r"\|\s*(编号|功能|说明|项目)\s*\|", ln):
                continue
        m = _TABLE_FEAT.match(ln)
        if not m:
            continue
        a, b = m.group(1).strip(), m.group(2).strip()
        if a in ("功能", "编号", "项目", "---", "-"):
            continue
        # 合成短句：账号：注册登录 / 或只用说明列
        if b and b not in ("说明", "内容", "---"):
            item = f"{a}：{b}" if a and a not in ("内容",) else b
        else:
            item = a
        item = re.sub(r"\s+", "", item)
        if 2 <= len(item) <= 60 and item not in seen:
            seen.add(item)
            out.append(item)
        if len(out) >= limit:
            break
    return out[:limit]


def _is_feature_heading(ln: str) -> bool:
    if _FEATURE_HEAD.search(ln):
        return True
    return bool(_RESEARCH_WITH_IMPL.search(ln))


def business_signal_score(text: str) -> int:
    """材料里「对开发有用」的信号强度；综述/进度/纯参考文献会很低。"""
    body = strip_non_dev_sections(text or "")
    if len(body.strip()) < 20:
        return 0
    score = 0
    mods = extract_module_lines(body)
    tabs = extract_table_features(body)
    score += min(12, len(mods) * 3)
    score += min(10, len(tabs) * 2)
    if _FEATURE_HEAD.search(body) or _RESEARCH_WITH_IMPL.search(body):
        score += 3
    if _TITLE_EXPLICIT.search(body) or _TITLE_HEADING.search(body) or _TITLE_PHRASE.search(body):
        score += 2
    for kw in (
        "订单", "购物车", "预约", "挂号", "报修", "借阅", "申领", "审核", "下单",
        "功能清单", "任务书", "用例", "实体", "数据库", "角色",
    ):
        if kw in body:
            score += 1
    return score


def merge_proposal_documents(
    docs: list[tuple[str, str]],
) -> tuple[str, str, list[dict], list[str]]:
    """合并多份材料。

    返回 (匹配用加权正文, 摘要用全文, 分档信息, 提示)。
    业务信号强的材料加权，避免只传文献综述时把匹配带偏；信号全弱时仍合并但给出提示。
    """
    if not docs:
        return "", "", [], ["提示：未读到任何材料正文"]

    scored: list[tuple[str, str, int]] = []
    for name, raw in docs:
        score = business_signal_score(raw or "")
        body = strip_non_dev_sections(raw or "")
        # 纯参考文献等裁空后：匹配侧不再灌回原文噪声
        use_text = body if body.strip() else ("" if score < 3 else (raw or ""))
        if not use_text.strip() and (raw or "").strip():
            # 摘要里仍留一行说明，避免「材料消失」
            use_text = f"（{name}：无有效业务正文，已忽略噪声段）"
        scored.append((name, use_text, score))

    scored.sort(key=lambda t: (-t[2], -len(t[1])))
    info = [
        {"name": n, "score": s, "chars": len(t)}
        for n, t, s in scored
    ]
    tips: list[str] = []
    best = scored[0][2]
    if best < 3:
        tips.append(
            "提示：上传材料业务信号偏弱（偏综述/进度/参考文献），"
            "匹配可能落通用壳；建议补充任务书或带功能清单的开题后再确认。"
        )
    elif len(scored) > 1 and scored[-1][2] == 0 and best >= 5:
        tips.append("提示：部分材料几乎无业务内容，已降低其在匹配中的权重。")

    # 摘要：全量拼接（带材料名），供 Agent / 展示
    summary_parts = [f"【材料：{n}】\n{t}" for n, t, _ in scored if t.strip()]
    summary_text = "\n\n".join(summary_parts)

    # 匹配：按信号加权复制（强×3 / 中×2 / 弱×1）
    match_parts: list[str] = []
    for n, t, s in scored:
        if not t.strip():
            continue
        block = f"【材料：{n}】\n{t}"
        weight = 3 if s >= 8 else 2 if s >= 3 else 1
        match_parts.extend([block] * weight)
    match_text_body = "\n\n".join(match_parts) or summary_text
    return match_text_body, summary_text, info, tips


def read_proposal_documents(paths: list[tuple[Path, str]]) -> tuple[str, str, list[dict], list[str]]:
    """paths: (path, display_name)"""
    docs: list[tuple[str, str]] = []
    for path, name in paths:
        docs.append((name or path.name, read_proposal(path)))
    return merge_proposal_documents(docs)


def load_source_documents(source_path: str | Path | None) -> list[tuple[str, str]]:
    """兼容单文件与多文件 manifest.json。"""
    if not source_path:
        return []
    path = Path(source_path)
    if not path.exists():
        return []
    if path.name == "manifest.json":
        import json

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return []
        root = path.parent
        out: list[tuple[str, str]] = []
        for item in data.get("files") or []:
            rel = item.get("path") or item.get("name")
            if not rel:
                continue
            fp = root / rel
            if fp.exists():
                out.append((item.get("name") or fp.name, read_proposal(fp)))
        return out
    return [(path.name, read_proposal(path))]


def load_merged_proposal_text(source_path: str | Path | None) -> str:
    docs = load_source_documents(source_path)
    if not docs:
        return ""
    _match, summary, _info, _tips = merge_proposal_documents(docs)
    return summary


def summarize_proposal(text: str, hits: list[str] | None = None) -> dict:
    """从开题/任务书等正文抽可读摘要（确定性规则，不调 LLM）。"""
    from app.bake.catalog import extract_title

    raw = (text or "").strip()
    body = strip_non_dev_sections(raw)
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    title = extract_title(raw)

    feature_lines: list[str] = []
    out_lines: list[str] = []
    sections: list[dict] = []
    mode: str | None = None
    current_heading: str | None = None
    current_body: list[str] = []

    def flush_section():
        nonlocal current_heading, current_body
        if current_heading and current_body:
            sections.append({"heading": current_heading, "lines": current_body[:12]})
        current_heading = None
        current_body = []

    for ln in lines:
        is_heading = bool(_SECTION.match(ln)) or (
            len(ln) <= 28 and bool(_is_feature_heading(ln) or _OUT_HEAD.search(ln))
        )
        # 「3. 实现下列功能：」或「（3）系统实现」
        if not is_heading and re.match(
            rf"^[（(]?\d*[)）.、]?\s*(?:{FEATURE_HEAD_TERMS})",
            ln,
        ):
            is_heading = True
            ln = ln.split("。")[0].strip().rstrip("：:")

        if mode == "feat" and _LEAVE_FEAT.match(ln):
            mode = "sec"
            flush_section()
            current_heading = ln
            continue

        if is_heading:
            flush_section()
            current_heading = ln
            if _is_feature_heading(ln):
                mode = "feat"
            elif _OUT_HEAD.search(ln):
                mode = "out"
            else:
                mode = "sec"
            continue

        if mode == "feat":
            cleaned = _BULLET.sub("", ln).strip()
            cleaned = re.sub(r"[。；;]+$", "", cleaned)
            if cleaned in ("系统设计", "系统测试", "需求分析") or cleaned.endswith("。"):
                continue
            if "：" in cleaned and len(cleaned) > 40:
                continue
            if cleaned and 4 <= len(cleaned) <= 80:
                if re.match(r"^[（(][一二三四五六七八九十\d]+[)）]", cleaned) and len(cleaned) <= 12:
                    continue
                feature_lines.append(cleaned)
        elif mode == "out":
            cleaned = _BULLET.sub("", ln).strip()
            if cleaned:
                parts = [p.strip() for p in re.split(r"[、；;]", cleaned) if p.strip()]
                out_lines.extend(parts if len(parts) > 1 else [cleaned])
        elif mode == "sec" and current_heading:
            current_body.append(ln)

    flush_section()

    modules = extract_module_lines(body)
    table_feats = extract_table_features(body)
    if len(modules) >= 3:
        feature_lines = modules
    elif len(table_feats) >= 3:
        feature_lines = table_feats
    else:
        merged: list[str] = []
        for x in modules + table_feats + feature_lines:
            if x not in merged:
                merged.append(x)
        feature_lines = merged

    background = ""
    for sec in sections:
        if any(k in sec["heading"] for k in ("背景", "意义", "概述", "简介", "重点研究")):
            background = " ".join(sec["lines"][:3])
            break
    if not background:
        for ln in lines[1:8]:
            if len(ln) >= 12 and not _SECTION.match(ln) and not _SKIP_TITLE_LINE.match(ln):
                background = ln
                break

    return {
        "title": title,
        "background": background[:240],
        "feature_lines": feature_lines[:20],
        "out_scope_lines": dedupe_out_scope_vs_features(
            feature_lines[:20], out_lines, limit=12
        ),
        "sections": sections[:8],
        "hits": list(hits or []),
        "excerpt": raw[:2000],
        "char_count": len(raw),
    }
