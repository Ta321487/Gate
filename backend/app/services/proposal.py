from __future__ import annotations

import re
from pathlib import Path


_FEATURE_HEAD = re.compile(r"(主要功能|功能需求|功能模块|实现内容|研究内容|系统功能)")
_OUT_HEAD = re.compile(r"(非本期|不在本期|本期不|范围外|不做|不实现)")
_SECTION = re.compile(r"^[一二三四五六七八九十百]+[、．.]|^第[一二三四五六七八九十\d]+[章节部分]")
_BULLET = re.compile(r"^(\d+[\.、\)）]|[-•·▪])\s*")


def read_proposal(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        try:
            from docx import Document

            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:  # noqa: BLE001
            return f"[docx 解析失败: {e}]\n文件名: {path.name}"
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
        return f"暂不支持 .doc，请另存为 .docx 或 .txt · {path.name}"
    return path.read_text(encoding="utf-8", errors="ignore")


def summarize_proposal(text: str, hits: list[str] | None = None) -> dict:
    """从开题正文抽可读摘要（确定性规则，不调 LLM）。"""
    from app.bake.catalog import extract_title

    raw = (text or "").strip()
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
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
        # 只把短标题 / 「一、二、」当章节；正文里带「不在本期」的长句不当标题
        is_heading = bool(_SECTION.match(ln)) or (
            len(ln) <= 18 and bool(_FEATURE_HEAD.search(ln) or _OUT_HEAD.search(ln))
        )
        if is_heading:
            flush_section()
            current_heading = ln
            if _FEATURE_HEAD.search(ln):
                mode = "feat"
            elif _OUT_HEAD.search(ln):
                mode = "out"
            else:
                mode = "sec"
            continue

        if mode == "feat" and _BULLET.match(ln):
            feature_lines.append(_BULLET.sub("", ln).strip())
        elif mode == "out":
            cleaned = _BULLET.sub("", ln).strip()
            if cleaned:
                # 顿号并列拆开，便于阅读
                parts = [p.strip() for p in re.split(r"[、；;]", cleaned) if p.strip()]
                out_lines.extend(parts if len(parts) > 1 else [cleaned])
        elif mode == "sec" and current_heading:
            current_body.append(ln)

    flush_section()

    background = ""
    for sec in sections:
        if any(k in sec["heading"] for k in ("背景", "意义", "概述", "简介")):
            background = " ".join(sec["lines"][:3])
            break
    if not background:
        for ln in lines[1:6]:
            if len(ln) >= 12 and not _SECTION.match(ln):
                background = ln
                break

    return {
        "title": title,
        "background": background[:240],
        "feature_lines": feature_lines[:20],
        "out_scope_lines": out_lines[:12],
        "sections": sections[:8],
        "hits": list(hits or []),
        "excerpt": raw[:2000],
        "char_count": len(raw),
    }
