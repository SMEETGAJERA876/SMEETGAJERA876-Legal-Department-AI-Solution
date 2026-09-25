"""File format detection from content (magic bytes). File names and MIME types are untrusted."""

import zipfile
from io import BytesIO

HEADER_BYTES = 8192

FORMAT_LABELS = {
    "pdf": "PDF",
    "docx": "Word (DOCX)",
    "xlsx": "Excel (XLSX)",
    "pptx": "PowerPoint (PPTX)",
    "doc": "Word 97-2003 (DOC)",
    "jpg": "JPEG image",
    "png": "PNG image",
    "tiff": "TIFF image",
}

_OOXML_PARTS = {
    "word/document.xml": "docx",
    "xl/workbook.xml": "xlsx",
    "ppt/presentation.xml": "pptx",
}


def detect_format(header: bytes, full: bytes | None = None) -> str | None:
    """Return a format id ("pdf", "docx", "jpg", ...) or None if unrecognised.

    `full` (the whole file) is only needed to tell DOCX/XLSX/PPTX apart, which are all ZIPs.
    """
    if header.startswith(b"%PDF-"):
        return "pdf"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith((b"II*\x00", b"MM\x00*")):
        return "tiff"
    if header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "doc"
    if header.startswith(b"PK\x03\x04") and full is not None:
        try:
            with zipfile.ZipFile(BytesIO(full)) as archive:
                names = set(archive.namelist())
        except zipfile.BadZipFile:
            return None
        for part, fmt in _OOXML_PARTS.items():
            if part in names:
                return fmt
    return None
