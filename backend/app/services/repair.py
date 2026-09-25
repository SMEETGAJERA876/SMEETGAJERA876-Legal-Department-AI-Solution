"""Create a corrected copy of a PDF by rewriting the affected lines in place.

Only "fixable" issues (spelling, repeated words) are ever applied. The original file is
never modified; the result is written as a new file. Each affected line is removed and
written again with the correction, in the same position, size and weight, so the layout
is kept and the text still reads in order. Every change is verified by reading the new
PDF back.
"""

from dataclasses import dataclass, field
from typing import Any

import pymupdf

from app.services.document_check import Issue

BOLD_FLAG = 16  # PyMuPDF span flag for bold text
LINE_SHRINK = 0.2  # redact only the middle of the line box so neighbouring lines are safe
MAX_WIDTH_GROWTH = 1.03  # a corrected line may be up to 3% wider before the font shrinks
REDACT_KEEP_IMAGES = 0  # pymupdf.PDF_REDACT_IMAGE_NONE


@dataclass
class RepairResult:
    applied: list[Issue]
    failed: list[tuple[Issue, str]]


@dataclass
class _Line:
    bbox: pymupdf.Rect
    origin: tuple[float, float]
    font_size: float
    bold: bool
    chars: list[tuple[str, float]]  # (character, left x)
    replacements: list[tuple[int, int, Issue]] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(c for c, _ in self.chars)


def _page_lines(page: pymupdf.Page) -> list[_Line]:
    raw: dict[str, Any] = page.get_text("rawdict")
    lines: list[_Line] = []
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            chars = [(ch["c"], ch["bbox"][0]) for span in spans for ch in span["chars"]]
            first = spans[0]
            lines.append(
                _Line(
                    pymupdf.Rect(line["bbox"]),
                    (first["origin"][0], first["origin"][1]),
                    float(first["size"]),
                    bool(first["flags"] & BOLD_FLAG),
                    chars,
                )
            )
    return lines


def _attach(lines: list[_Line], rect: pymupdf.Rect, issue: Issue) -> bool:
    """Record the replacement on the line containing `rect`, at the matching characters."""
    centre = pymupdf.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
    for line in lines:
        if not line.bbox.contains(centre):
            continue
        text = line.text.lower()
        target = issue.original.lower()
        starts = [i for i in range(len(text)) if text.startswith(target, i)]
        if not starts:
            return False
        start = min(starts, key=lambda i: abs(line.chars[i][1] - rect.x0))
        line.replacements.append((start, len(issue.original), issue))
        return True
    return False


def _rewrite(page: pymupdf.Page, lines: list[_Line]) -> None:
    changed = [line for line in lines if line.replacements]
    for line in changed:
        box = pymupdf.Rect(line.bbox)
        inset = box.height * LINE_SHRINK
        page.add_redact_annot(pymupdf.Rect(box.x0, box.y0 + inset, box.x1, box.y1 - inset))
    page.apply_redactions(images=REDACT_KEEP_IMAGES)
    for line in changed:
        text = line.text
        for start, length, issue in sorted(line.replacements, key=lambda r: r[0], reverse=True):
            text = text[:start] + (issue.suggestion or "") + text[start + length :]
        fontname = "hebo" if line.bold else "helv"
        size = line.font_size
        width = pymupdf.get_text_length(text, fontname=fontname, fontsize=size)
        allowed = line.bbox.width * MAX_WIDTH_GROWTH
        if width > allowed > 0:
            size *= allowed / width
        page.insert_text(
            pymupdf.Point(*line.origin), text, fontname=fontname, fontsize=size, color=(0, 0, 0)
        )


def _locate(page: pymupdf.Page, issue: Issue) -> pymupdf.Rect | None:
    rects: list[pymupdf.Rect] = page.search_for(issue.original)
    if not rects:
        return None
    return rects[min(issue.occurrence, len(rects) - 1)]


def repair_pdf(source: bytes, issues: list[Issue]) -> tuple[RepairResult, bytes]:
    """Apply the fixable issues to a copy of the PDF. Returns the result and the new PDF."""
    failed: list[tuple[Issue, str]] = []
    pending: dict[int, list[Issue]] = {}
    with pymupdf.open(stream=source, filetype="pdf") as pdf:
        lines_by_page: dict[int, list[_Line]] = {}
        for issue in issues:
            if not issue.fixable:
                failed.append((issue, "Needs a person to decide; never changed automatically."))
                continue
            page = pdf[issue.page_number - 1]
            lines = lines_by_page.setdefault(issue.page_number, _page_lines(page))
            rect = _locate(page, issue)
            if rect is None or not _attach(lines, rect, issue):
                failed.append((issue, "The words couldn't be located precisely in the PDF."))
                continue
            pending.setdefault(issue.page_number, []).append(issue)

        for page_number, lines in lines_by_page.items():
            _rewrite(pdf[page_number - 1], lines)

        applied: list[Issue] = []
        for page_number, page_issues in pending.items():
            page_text = " ".join(pdf[page_number - 1].get_text().split())
            for issue in page_issues:
                if (issue.suggestion or "") in page_text:
                    applied.append(issue)
                else:
                    failed.append((issue, "The change could not be verified in the new PDF."))

        corrected = pdf.tobytes(garbage=3, deflate=True)
    return RepairResult(applied, failed), corrected
