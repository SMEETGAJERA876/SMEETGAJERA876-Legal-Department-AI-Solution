"""Parser registry. Adding a format = adding one parser to PARSERS; nothing else changes."""

from pathlib import Path

from app.services.parsing.base import (
    DocumentParseError,
    DocumentParser,
    ParsedBlock,
    ParsedDocument,
    ParsedPage,
)
from app.services.parsing.formats import FORMAT_LABELS, HEADER_BYTES, detect_format
from app.services.parsing.pdf import PDFParser

PARSERS: list[DocumentParser] = [PDFParser()]
SUPPORTED_FORMATS = frozenset(fmt for parser in PARSERS for fmt in parser.formats)

__all__ = [
    "DocumentParseError",
    "DocumentParser",
    "FORMAT_LABELS",
    "HEADER_BYTES",
    "ParsedBlock",
    "ParsedDocument",
    "ParsedPage",
    "SUPPORTED_FORMATS",
    "detect_format",
    "get_parser",
    "parse_file",
]


def get_parser(fmt: str) -> DocumentParser:
    for parser in PARSERS:
        if fmt in parser.formats:
            return parser
    label = FORMAT_LABELS.get(fmt, fmt.upper())
    raise DocumentParseError(
        f"{label} files are not supported yet. Please upload the document as a PDF."
    )


def parse_file(source: bytes | Path, fmt: str, ocr: bool = True) -> ParsedDocument:
    """Parse a document from its bytes (as read through storage) or a local path.
    ocr=False skips text recognition of scanned pages (e.g. when only layout is needed)."""
    return get_parser(fmt).parse(source, ocr_enabled=ocr)
