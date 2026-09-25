"""PDF parser (PyMuPDF): page text in reading order plus positioned blocks."""

import re
from pathlib import Path
from typing import Any

import pymupdf

from app.services.chunking import detect_clause_start, is_caps_heading
from app.services.parsing import ocr
from app.services.parsing.base import (
    BlockType,
    DocumentParseError,
    ParsedBlock,
    ParsedDocument,
    ParsedPage,
)
from app.services.text_utils import normalize_whitespace

MIN_TEXT_CHARACTERS = 20
MIN_PAGE_TEXT_CHARACTERS = 5
MAX_OCR_PAGES = 60  # ~3 s per page on a laptop CPU
HORIZONTAL_TOLERANCE = 0.05
MIN_WATERMARK_CHARACTERS = 3
_FOOTER = re.compile(r"^\s*(?:page\s+)?\d+\s*(?:(?:of|/)\s*\d+)?\s*$", re.IGNORECASE)


def _block_type(text: str) -> BlockType:
    if _FOOTER.match(text):
        return "footer"
    start = detect_clause_start(text)
    if (start and start.heading and not start.has_body) or is_caps_heading(text):
        return "heading"
    if text.startswith("(") and start is not None:
        return "list_item"
    return "paragraph"


def _watermarks(page: Any) -> list[str]:
    """Text drawn at an angle — watermarks and stamps such as India Code's diagonal
    "IndiaCode" — which plain extraction would splice into the sentences it crosses."""
    marks = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            dx, dy = line["dir"]
            if abs(dy) > HORIZONTAL_TOLERANCE or dx < 0:
                text = "".join(span["text"] for span in line["spans"]).strip()
                if len(text) >= MIN_WATERMARK_CHARACTERS:
                    marks.append(text)
    return marks


def _without(text: str, marks: list[str]) -> str:
    for mark in marks:
        text = text.replace(mark, "", 1)
    return text


def _blocks(page: Any, marks: list[str]) -> list[ParsedBlock]:
    blocks: list[ParsedBlock] = []
    for x0, y0, x1, y1, text, _number, kind in page.get_text("blocks", sort=True):
        clean = normalize_whitespace(_without(text, marks))
        if kind != 0 or not clean:  # kind 1 = image block
            continue
        blocks.append(ParsedBlock(_block_type(clean), clean, (x0, y0, x1, y1)))
    return blocks


class PDFParser:
    name = "PDFParser"
    formats = frozenset({"pdf"})

    def parse(self, source: bytes | Path, ocr_enabled: bool = True) -> ParsedDocument:
        ocr_pages: list[int] = []
        skipped_ocr: list[int] = []
        try:
            opened = (
                pymupdf.open(stream=source, filetype="pdf")
                if isinstance(source, bytes)
                else pymupdf.open(source)
            )
            with opened as pdf:
                if pdf.needs_pass and not pdf.authenticate(""):
                    raise DocumentParseError(
                        "This PDF is password-protected. Remove the password and upload it again."
                    )
                pages = []
                for index, page in enumerate(pdf, start=1):
                    # sort=True reads top-to-bottom, left-to-right, like a person would
                    marks = _watermarks(page)
                    text = _without(page.get_text("text", sort=True), marks)
                    has_text_layer = len(text.strip()) >= MIN_PAGE_TEXT_CHARACTERS
                    blocks = _blocks(page, marks)
                    if not has_text_layer and ocr_enabled:
                        if len(ocr_pages) < MAX_OCR_PAGES:
                            lines = ocr.read_page(page)
                            text = "\n".join(line.text for line in lines)
                            blocks = [
                                ParsedBlock(_block_type(line.text), line.text, line.bbox)
                                for line in lines
                            ]
                            ocr_pages.append(index)
                        else:
                            skipped_ocr.append(index)
                    pages.append(
                        ParsedPage(
                            page_number=index,
                            text=text,
                            width=float(page.rect.width),
                            height=float(page.rect.height),
                            has_text_layer=has_text_layer,
                            blocks=blocks,
                            ocr=index in ocr_pages,
                        )
                    )
        except DocumentParseError:
            raise
        except (pymupdf.FileDataError, RuntimeError, ValueError, OSError) as error:
            raise DocumentParseError(
                "Unable to read this PDF. The file may be damaged. "
                "Try re-saving or re-exporting it."
            ) from error

        if not pages:
            raise DocumentParseError("This PDF has no pages.")
        if sum(len(p.text.strip()) for p in pages) < MIN_TEXT_CHARACTERS:
            raise DocumentParseError(
                "Unable to read any text in this PDF, even with text recognition (OCR). The scan "
                "may be too blurry or faint — try scanning again at a higher quality."
            )
        document = ParsedDocument("pdf", self.name, f"pymupdf-{pymupdf.VersionBind}", pages)
        if ocr_pages:
            document.warnings.append(
                f"Page(s) {_page_list(ocr_pages)} are scanned and were read with text recognition "
                "(OCR); check important details against the page."
            )
        if skipped_ocr:
            document.warnings.append(
                f"Page(s) {_page_list(skipped_ocr)} are scanned and were not read: only the first "
                f"{MAX_OCR_PAGES} scanned pages of a document are read with OCR."
            )
        blank = [p.page_number for p in pages if not p.has_text_layer]
        if blank and not ocr_enabled:
            document.warnings.append(
                f"No selectable text on page(s) {_page_list(blank)}; they may be scanned."
            )
        return document


def _page_list(pages: list[int]) -> str:
    return ", ".join(map(str, pages))
