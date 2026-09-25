"""Common document-parser interface (docs/Document_Normalization.md §2).

Every parser turns a file into a ParsedDocument: pages in reading order, each with blocks.
The rest of the pipeline only sees ParsedDocument, never a specific file format.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

BlockType = Literal["heading", "paragraph", "list_item", "table", "header", "footer", "other"]


class DocumentParseError(Exception):
    """A user-facing explanation of why a file could not be read."""


@dataclass
class ParsedBlock:
    type: BlockType
    text: str
    bbox: tuple[float, float, float, float] | None = None  # PDF points on the page


@dataclass
class ParsedPage:
    page_number: int
    text: str  # reading order
    width: float | None = None
    height: float | None = None
    has_text_layer: bool = True
    blocks: list[ParsedBlock] = field(default_factory=list)
    ocr: bool = False  # the text was recognised from the page image (scanned page)


@dataclass
class ParsedDocument:
    format: str
    parser: str
    parser_version: str
    pages: list[ParsedPage]
    warnings: list[str] = field(default_factory=list)

    @property
    def is_scanned(self) -> bool:
        """Most pages have no text layer (an image of text)."""
        return sum(not p.has_text_layer for p in self.pages) * 2 >= len(self.pages)

    @property
    def page_texts(self) -> list[str]:
        return [p.text for p in self.pages]


class DocumentParser(Protocol):
    name: str
    formats: frozenset[str]

    def parse(self, source: bytes | Path, ocr_enabled: bool = True) -> ParsedDocument: ...
