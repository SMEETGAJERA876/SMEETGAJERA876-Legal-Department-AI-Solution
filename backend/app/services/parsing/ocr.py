"""OCR for scanned pages (an image of text, no selectable text layer).

RapidOCR (PP-OCR models on ONNX Runtime) runs locally — no API key, nothing leaves the server.
Pages are rendered at OCR_DPI, recognised line by line and put back in reading order. Box
positions are converted to PDF points so they fit the same structure as ordinary text blocks.
"""

import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rapidocr import RapidOCR

OCR_DPI = 200
POINTS_PER_INCH = 72
MIN_CONFIDENCE = 0.5
SAME_LINE_OVERLAP = 0.5  # boxes overlapping this much vertically are on the same line

_engine: "RapidOCR | None" = None
_lock = threading.Lock()


@dataclass(frozen=True)
class OcrLine:
    text: str
    bbox: tuple[float, float, float, float]  # PDF points
    confidence: float


def _get_engine() -> "RapidOCR":
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                logging.getLogger("RapidOCR").setLevel(logging.WARNING)
                from rapidocr import RapidOCR

                _engine = RapidOCR(params={"Global.log_level": "warning"})
    return _engine


def _vertical_overlap(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    top, bottom = max(a[1], b[1]), min(a[3], b[3])
    shortest = min(a[3] - a[1], b[3] - b[1]) or 1.0
    return max(0.0, bottom - top) / shortest


def read_page(page: Any) -> list[OcrLine]:
    """Recognised text lines of one PDF page (a pymupdf.Page), in reading order."""
    pixmap = page.get_pixmap(dpi=OCR_DPI)
    # RapidOCROutput: parallel lists of boxes (4 corner points), texts and scores.
    result: Any = _get_engine()(pixmap.tobytes("png"))
    if result.boxes is None or result.txts is None:
        return []
    scale = POINTS_PER_INCH / OCR_DPI
    pieces = []
    for box, text, score in zip(result.boxes, result.txts, result.scores, strict=True):
        if float(score) < MIN_CONFIDENCE or not text.strip():
            continue
        xs, ys = [p[0] * scale for p in box], [p[1] * scale for p in box]
        pieces.append((text.strip(), (min(xs), min(ys), max(xs), max(ys)), float(score)))

    # Group pieces into lines (same height on the page), then read each line left to right.
    pieces.sort(key=lambda p: (p[1][1], p[1][0]))
    lines: list[list[tuple[str, tuple[float, float, float, float], float]]] = []
    for piece in pieces:
        if lines and _vertical_overlap(lines[-1][-1][1], piece[1]) >= SAME_LINE_OVERLAP:
            lines[-1].append(piece)
        else:
            lines.append([piece])
    ocr_lines = []
    for line in lines:
        line.sort(key=lambda p: p[1][0])
        x0 = min(p[1][0] for p in line)
        y0 = min(p[1][1] for p in line)
        x1 = max(p[1][2] for p in line)
        y1 = max(p[1][3] for p in line)
        confidence = min(p[2] for p in line)
        ocr_lines.append(OcrLine(" ".join(p[0] for p in line), (x0, y0, x1, y1), confidence))
    return ocr_lines
