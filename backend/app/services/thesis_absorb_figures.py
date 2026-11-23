"""终稿吸收·图/表侧（用库 · 禁止自研抠框）。

真源：docs/thesis-absorb.md §3.3b。
- 层0：题注锚点（功能结构图 / 用例图）
- 层1：PyMuPDF 渲页、导嵌图
- 层2a：pdfplumber 抽表
- 层2b：RapidOCR/PaddleOCR/Tesseract 读结构图标签（主路径；未装则告警）
- 层3：与文字 P1/P2 交叉（extract 侧）
默认不上 LLM。同材同果。
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any, Callable

_CAPTION = re.compile(
    r"(?:图|表)\s*[0-9０-９一二三四五六七八九十]+(?:\.[0-9０-９一二三四五六七八九十]+)*"
    r"[^\n]{0,48}"
)
_STRUCT_CAPTION = re.compile(
    r"(?:图|表)\s*[0-9０-９一二三四五六七八九十.．]+[^\n]{0,40}"
    r"(?:功能结构|结构功能|用例图)"
)
_MODULE_LABEL = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9/与及]{2,12}(?:管理|模块))"
)
_END_IN_CAPTION = re.compile(r"([\u4e00-\u9fff]{2,8})端")
_TABLE_CAPTION = re.compile(r"表\s*[0-9０-９一二三四五六七八九十]")
_SKIP_LABEL = frozenset(
    {
        "功能模块",
        "系统模块",
        "业务模块",
        "系统功能模块",
        "各功能模块",
        "管理端",
        "用户端",
        "客户端",
        "服务端",
        "网站功能",
        "结构设计",
        "功能结构",
        "模块管理",
        "系统管理",
    }
)
# 整页 OCR 常把旁白叙述抠成「××管理/模块」；只留短模块名形态
_LABEL_NARRATIVE = re.compile(
    r"(?:了|绘制|本章|本节|简介|框架|路由|微框架|时间成本|详细描述|"
    r"Flask|Django|Spring|MySQL|Vue|React|当前|传统|现有|本系统|"
    r"分为|包含|其中|以及|定制|序列图|用例图|类图|结构设计)",
    re.I,
)

# 就绪检查禁止真 import OCR（rapidocr 冷启动约 1～2s）；引擎只在真正 OCR 时建一次。
_ready_cache: tuple[bool, str] | None = None
_ocr_fn_cache: Callable[[bytes], str] | None = None
_ocr_fn_failed = False


def _has_spec(*names: str) -> bool:
    for name in names:
        try:
            if importlib.util.find_spec(name) is not None:
                return True
        except (ImportError, ModuleNotFoundError, ValueError):
            continue
    return False


def figure_libs_ready() -> tuple[bool, str]:
    """文字主矿不依赖本函数；灰按钮文案用 hint。"""
    global _ready_cache
    if _ready_cache is not None:
        return _ready_cache
    missing: list[str] = []
    if not _has_spec("pymupdf", "fitz"):
        missing.append("pymupdf")
    if not _has_spec("pdfplumber"):
        missing.append("pdfplumber")
    if missing:
        _ready_cache = (
            False,
            "图侧库未就绪（缺 " + "、".join(missing) + "），文字终稿可照常使用",
        )
        return _ready_cache
    if ocr_libs_ready():
        _ready_cache = (
            True,
            "图侧已接 PyMuPDF + pdfplumber + OCR，结构图可对账",
        )
    else:
        _ready_cache = (
            True,
            "图侧已接 PyMuPDF + pdfplumber；未装 OCR 时结构图标签抽不出，交叉验证会告警",
        )
    return _ready_cache


def ocr_libs_ready() -> bool:
    return _has_spec("rapidocr_onnxruntime", "paddleocr", "pytesseract")


def _norm_label(raw: str) -> str | None:
    """结构图 OCR 标签钳子：只要短模块名，不要旁白叙述残片。"""
    t = re.sub(r"\s+", "", (raw or "").strip())
    if not t or len(t) < 3 or len(t) > 12:
        return None
    if t in _SKIP_LABEL:
        return None
    # 页码残渣 / 结构树叶子操作（增删改查）不当模块标签
    if re.match(r"^\d", t):
        return None
    if re.match(r"(?:增加|删除|修改|查看|新增|编辑)", t):
        return None
    if _LABEL_NARRATIVE.search(t):
        return None
    # 「时间成本与管理」类：连词拼出来的假模块
    if re.search(r"[与及和]", t):
        return None
    # 叙述里夹「的…模块」
    if "的" in t:
        return None
    # 必须是整段「短茎 + 管理/模块」，禁止从长句中截半截
    if not re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9]{2,8}(?:管理|模块)", t):
        return None
    return t


def extract_captions_from_text(text: str, *, limit: int = 24) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in _CAPTION.finditer(text or ""):
        cap = re.sub(r"\s+", " ", m.group(0)).strip()
        if not cap or cap in seen:
            continue
        seen.add(cap)
        out.append(cap[:80])
        if len(out) >= limit:
            break
    return out


def structure_captions(captions: list[str]) -> list[str]:
    """只留功能结构 / 用例图题注（交叉锚点）。"""
    out: list[str] = []
    for cap in captions or []:
        if _STRUCT_CAPTION.search(cap) or re.search(
            r"功能结构|结构功能|用例图", cap
        ):
            out.append(cap)
    return out


def ends_from_structure_captions(captions: list[str]) -> list[str]:
    """从图题「××端…功能结构」抠端名，供与角色交叉（形态，不写死岗名）。"""
    out: list[str] = []
    seen: set[str] = set()
    for cap in structure_captions(captions):
        for m in _END_IN_CAPTION.finditer(cap):
            stem = m.group(1)
            if stem in ("前", "后", "客户", "服务", "移动", "系统", "功能", "业务"):
                continue
            if stem not in seen:
                seen.add(stem)
                out.append(stem)
    return out[:8]


def _labels_from_blob(blob: str, *, limit: int = 32) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in _MODULE_LABEL.finditer(blob or ""):
        lab = _norm_label(m.group(1))
        if not lab or lab in seen:
            continue
        seen.add(lab)
        out.append(lab)
        if len(out) >= limit:
            break
    return out


def extract_tables_pdfplumber(path: Path, *, max_pages: int = 40) -> list[dict[str, Any]]:
    """层2a：现成库抽表；失败返回空，不抛。"""
    try:
        import pdfplumber
    except ImportError:
        return []
    tables: list[dict[str, Any]] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                try:
                    raw_tables = page.extract_tables() or []
                except Exception:
                    continue
                for ti, rows in enumerate(raw_tables):
                    if not rows or len(rows) < 2:
                        continue
                    clean_rows: list[list[str]] = []
                    for row in rows[:40]:
                        clean_rows.append(
                            [
                                re.sub(r"\s+", " ", str(c or "")).strip()[:64]
                                for c in (row or [])
                            ]
                        )
                    flat = " ".join(c for r in clean_rows for c in r if c)
                    if len(flat) < 4:
                        continue
                    tables.append(
                        {
                            "page": i + 1,
                            "index": ti,
                            "rows": clean_rows[:24],
                            "labels": _labels_from_blob(flat, limit=16),
                        }
                    )
                    if len(tables) >= 20:
                        return tables
    except Exception:
        return []
    return tables


def _open_pdf(path: Path):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz  # type: ignore
    return fitz.open(str(path))


def extract_embedded_image_count(path: Path, *, max_pages: int = 80) -> int:
    try:
        doc = _open_pdf(path)
    except Exception:
        return 0
    n = 0
    try:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            try:
                n += len(page.get_images(full=True) or [])
            except Exception:
                continue
    finally:
        doc.close()
    return n


def _find_structure_pages(doc: Any, *, max_pages: int = 80) -> list[int]:
    """页码 0-based：题注或正文含功能结构/用例图。"""
    pages: list[int] = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        try:
            t = page.get_text("text") or ""
        except Exception:
            continue
        if re.search(r"功能结构|结构功能|用例图", t):
            pages.append(i)
    return pages


def _make_ocr_fn() -> Callable[[bytes], str] | None:
    try:
        from rapidocr_onnxruntime import RapidOCR

        engine = RapidOCR()

        def _ocr(img_bytes: bytes) -> str:
            result, _ = engine(img_bytes)
            if not result:
                return ""
            return " ".join(str(x[1]) for x in result if len(x) > 1)

        return _ocr
    except Exception:
        pass
    try:
        import pytesseract
        from PIL import Image
        import io

        def _ocr(img_bytes: bytes) -> str:
            img = Image.open(io.BytesIO(img_bytes))
            return pytesseract.image_to_string(img, lang="chi_sim+eng") or ""

        return _ocr
    except Exception:
        return None


def _get_ocr_fn() -> Callable[[bytes], str] | None:
    """进程内单例；避免每次重抽都 import + 建引擎。"""
    global _ocr_fn_cache, _ocr_fn_failed
    if _ocr_fn_failed:
        return None
    if _ocr_fn_cache is not None:
        return _ocr_fn_cache
    if not ocr_libs_ready():
        _ocr_fn_failed = True
        return None
    fn = _make_ocr_fn()
    if fn is None:
        _ocr_fn_failed = True
        return None
    _ocr_fn_cache = fn
    return _ocr_fn_cache


def _scan_pdf_images_and_ocr(
    path: Path, *, max_pages: int = 80, want_ocr: bool = True
) -> tuple[int, list[str]]:
    """一次打开：先定位结构页再计数/OCR，禁止全本逐页扫嵌图。"""
    try:
        doc = _open_pdf(path)
    except Exception:
        return 0, []
    image_count = 0
    out: list[str] = []
    seen: set[str] = set()
    try:
        targets = _find_structure_pages(doc, max_pages=max_pages)
        # 只计结构页嵌图；无锚点则抽查前 12 页（展示用，不触发 OCR）
        count_pages = targets or list(range(min(len(doc), 12, max_pages)))
        for i in count_pages:
            try:
                image_count += len(doc[i].get_images(full=True) or [])
            except Exception:
                continue
        if not want_ocr or not targets:
            return image_count, []
        ocr_fn = _get_ocr_fn()
        if ocr_fn is None:
            return image_count, []
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz  # type: ignore
        for i in targets:
            page = doc[i]
            blobs: list[bytes] = []
            try:
                for img in page.get_images(full=True) or []:
                    xref = img[0]
                    try:
                        pix = fitz.Pixmap(doc, xref)
                        if pix.n >= 5:  # CMYK
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        blobs.append(pix.tobytes("png"))
                    except Exception:
                        continue
            except Exception:
                pass
            if not blobs:
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                    blobs.append(pix.tobytes("png"))
                except Exception:
                    continue
            for raw in blobs[:4]:
                try:
                    text = ocr_fn(raw)
                except Exception:
                    continue
                for lab in _labels_from_blob(text, limit=20):
                    if lab not in seen:
                        seen.add(lab)
                        out.append(lab)
            if len(out) >= 48:
                break
    finally:
        doc.close()
    return image_count, out[:48]


def try_ocr_structure_labels(path: Path, *, max_pages: int = 80) -> list[str]:
    """层2b：只 OCR「功能结构/用例图」所在页的嵌图与页渲，抽模块标签。"""
    _, labels = _scan_pdf_images_and_ocr(path, max_pages=max_pages, want_ocr=True)
    return labels


def extract_pdf_figure_side(path: Path | str, text: str = "") -> dict[str, Any]:
    """对一份 PDF 跑图侧管道；结构图标签供 §3.0b 交叉，不发明功能。"""
    p = Path(path)
    ready, hint = figure_libs_ready()
    empty = {
        "ready": ready,
        "hint": hint,
        "has_figure_text": False,
        "captions": [],
        "structure_captions": [],
        "structure_ends": [],
        "table_labels": [],
        "plumber_tables": [],
        "ocr_labels": [],
        "structure_labels": [],
        "image_count": 0,
        "table_count": 0,
        "section_lines": [],
        "warnings": [],
    }
    if not ready or not p.is_file() or p.suffix.lower() != ".pdf":
        return empty

    captions = extract_captions_from_text(text)
    struct_caps = structure_captions(captions)
    struct_ends = ends_from_structure_captions(captions)
    # 无表题注则跳过 pdfplumber 全页抽表（很慢）；结构图 OCR 仍走
    tables = (
        extract_tables_pdfplumber(p)
        if _TABLE_CAPTION.search(text or "")
        else []
    )
    # 保留 rows 供库表章 → draft schema.sql（不只抽 labels）
    plumber_tables: list[dict[str, Any]] = [
        {
            "page": t.get("page"),
            "index": t.get("index"),
            "rows": t.get("rows") or [],
            "labels": t.get("labels") or [],
        }
        for t in tables
        if isinstance(t, dict)
    ]
    table_labels: list[str] = []
    seen_t: set[str] = set()
    for tab in tables:
        for lab in tab.get("labels") or []:
            if lab not in seen_t:
                seen_t.add(lab)
                table_labels.append(lab)
    # 一次打开：嵌图计数 + 仅结构页 OCR（无题注页则早退，不瞎扫全文）
    image_count, ocr_labels = _scan_pdf_images_and_ocr(p, want_ocr=True)

    # 结构图标签 = OCR；表标签另列
    structure_labels = list(ocr_labels)

    section_lines: list[str] = []
    for cap in struct_caps[:12]:
        section_lines.append(cap)
    for lab in structure_labels[:20]:
        if lab not in section_lines:
            section_lines.append(lab)
    for lab in table_labels[:12]:
        if lab not in section_lines:
            section_lines.append(lab)

    has_fig = bool(struct_caps or table_labels or structure_labels)
    warnings: list[str] = []
    if struct_caps and not structure_labels:
        if not ocr_libs_ready():
            warnings.append(
                "有功能结构/用例图题注但未装 OCR，结构图标签未抽，无法与文字模块清单交叉"
            )
        else:
            warnings.append(
                "有功能结构/用例图题注但 OCR 未读出模块标签，交叉验证不完整"
            )

    return {
        "ready": True,
        "hint": hint,
        "has_figure_text": has_fig,
        "captions": captions,
        "structure_captions": struct_caps,
        "structure_ends": struct_ends,
        "table_labels": table_labels[:24],
        "plumber_tables": plumber_tables[:40],
        "ocr_labels": ocr_labels,
        "structure_labels": structure_labels[:40],
        "image_count": image_count,
        "table_count": len(tables),
        "section_lines": section_lines[:32],
        "warnings": warnings,
    }


def merge_figure_into_proposal(
    proposal: dict[str, Any],
    fig: dict[str, Any],
) -> dict[str, Any]:
    """图注/结构标签并入 sections；不改写 feature_lines（交叉在 extract 侧做）。"""
    prop = dict(proposal or {})
    lines = [str(x) for x in (fig.get("section_lines") or []) if str(x).strip()]
    if lines:
        secs = list(prop.get("sections") or [])
        if not isinstance(secs, list):
            secs = []
        heading = "图注与结构标签"
        found = False
        for s in secs:
            if isinstance(s, dict) and str(s.get("heading") or "") == heading:
                old = [x for x in (s.get("lines") or []) if isinstance(x, str)]
                merged = old[:]
                seen = set(old)
                for ln in lines:
                    if ln not in seen:
                        seen.add(ln)
                        merged.append(ln)
                s["lines"] = merged[:24]
                found = True
                break
        if not found:
            secs.append({"heading": heading, "lines": lines[:24]})
        prop["sections"] = secs
    prop["figure_labels"] = list(fig.get("structure_labels") or fig.get("ocr_labels") or [])[
        :40
    ]
    prop["table_labels"] = list(fig.get("table_labels") or [])[:24]
    prop["structure_ends"] = list(fig.get("structure_ends") or [])[:8]
    prop["structure_captions"] = list(fig.get("structure_captions") or [])[:12]
    return prop
