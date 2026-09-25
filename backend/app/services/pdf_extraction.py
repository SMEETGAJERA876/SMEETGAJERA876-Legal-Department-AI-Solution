"""Backwards-compatible helper: page texts of a PDF. New code should use app.services.parsing."""

from pathlib import Path

from app.services.parsing import DocumentParseError
from app.services.parsing.pdf import PDFParser

PdfExtractionError = DocumentParseError


def extract_pages(path: Path) -> list[str]:
    """Return the text of each page in reading order. Page N is at index N-1."""
    return PDFParser().parse(path).page_texts
