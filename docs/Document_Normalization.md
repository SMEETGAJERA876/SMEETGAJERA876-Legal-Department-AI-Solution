# Document Normalization

**Status:** implemented for PDF (Phase 3). `GET /documents/{id}/normalized` returns this structure for any processed document (`backend/app/services/normalize.py`); the parser interface lives in `backend/app/services/parsing/`. Tests validate the output of all sample documents against the schema and check every evidence offset.

Every file — PDF, DOCX, image, spreadsheet — is converted into **one internal structure** so that search, extraction, Q&A, citations and highlighting never depend on the file format.

Schema: [`data/schemas/normalized_document.schema.json`](../data/schemas/normalized_document.schema.json) · Examples: [`data/examples/`](../data/examples)

```text
NormalizedDocument
 ├── document        id, title, format, language, page_count, classification
 ├── parties         name + role (employer, tenant, petitioner, issuing_authority …)
 ├── pages[]         page_number, text (reading order), blocks[], ocr info
 ├── sections[]      number, heading, role, level, page_start..page_end
 │     └── clauses[] clause_number, page_number, text, char_start/char_end, concepts, fact_ids
 ├── facts[]         legal_fact: concept, value, normalized_value, evidence, confidence
 ├── entities[]      people, organisations, authorities, courts, statutes, references
 ├── court           court metadata (only for court.* types)
 └── processing      parser, versions, OCR used, warnings
```

## 1. Design decisions

1. **Sections are document-level, with a page range.** The idea in the brief nests sections inside pages, but real sections often cross page breaks ("Termination" starting at the bottom of page 6). Nesting would split them in two or duplicate them. Every clause and fact still records its exact `page_number` (and `page_end` when it crosses pages), so *Document → Page → Section → Clause → Concept → Fact → Evidence* is preserved.
2. **Evidence offsets refer to `pages[].text`.** `char_start`/`char_end` are end-exclusive offsets into that page's text, which is stored in reading order. `pages[n].text[char_start:char_end] == source_text` is checked for every fact and clause in the examples (see `backend/tests/test_taxonomy_data.py`).
3. **Clause numbers are kept as printed.** `12.1`, `Section 5(1)(a)`, `Rule 7(2)`, `Chapter II` — no renumbering.
4. **Section `role` records structural meaning** so different parts are never merged — especially in judgments: `facts`, `arguments`, `issues`, `evidence`, `law`, `reasoning`, `findings`, `final_order`.
5. **Format ≠ type.** `document.format` is how the file is stored; `document.classification` is what it is.
6. **Low-confidence classifications cannot be marked `confirmed`** (enforced by the schema).

## 2. Parser interface (Phase 3 / 11)

```python
class DocumentParser(Protocol):
    formats: frozenset[str]            # e.g. {"pdf"}

    def can_parse(self, header: bytes, filename: str) -> bool: ...
    def parse(self, path: Path) -> ParsedDocument: ...   # pages + blocks, with OCR info

# Implementations (one module each, registered in a single table):
#   PDFParser        pdf         PyMuPDF text in reading order; per-page OCR when a page has no text
#   DOCXParser       docx        python-docx; paragraphs/tables → blocks; pages from explicit breaks
#                                 or a fixed words-per-page estimate (flagged in processing.warnings)
#   ImageOCRParser   jpg/png/tiff OCR engine; one page per image / TIFF frame
#   TXTParser        txt         form-feed or length-based pages
#   SpreadsheetParser xlsx/csv   one page per sheet; rows → table blocks
#   HTMLParser       html/htm    readable text → blocks
```

The rest of the pipeline (section detection, clause detection, concept extraction, chunking, embeddings) only ever sees `ParsedDocument` → `NormalizedDocument`. Adding a format means adding one parser; nothing else changes.

**Where page numbers come from:** PDF and image formats have real pages. DOCX, TXT, HTML and spreadsheets don't; their "pages" are explicit page breaks or estimates, and this is recorded in `processing.warnings` so the UI can say "section 4 of the document" instead of pretending an exact page.

## 3. Mapping to today's database

| Normalized JSON | Database table (today) | Notes |
|---|---|---|
| `document` | `documents` | `format` column ✅ (detected from content); structured `classification` columns in Phase 5 |
| `pages[]` | `document_pages` | text per page |
| `sections[]` | `clauses` (top-level clauses) | a `document_sections` table is planned |
| `sections[].clauses[]` | `document_chunks.clause_ref` | chunks carry the clause number and heading |
| `facts[]` | `legal_facts` | `normalized_value`, `char_start/char_end` and `confidence` are computed when the normalized document is built; stored columns planned |
| `entities[]` | `documents.parties` (JSON) | a `document_entities` table is planned |
| `court` | — | planned with court-document support |

Planned additions (spec §32): `document_sections`, `document_entities`, `document_concepts`, `document_classifications`, plus `format`, `language`, `confidence`, `normalized_value`, `char_start`, `char_end` columns, with indexes on `(document_id, page_number)`, `(document_id, concept)` and pgvector on chunk embeddings. These will be added with migrations in the phases that need them — not all at once.
