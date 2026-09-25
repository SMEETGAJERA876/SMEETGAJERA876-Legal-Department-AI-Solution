# AI Pipeline

ClauseLens does **not** train a language model. Its intelligence is:

```text
Document structure + Legal concept taxonomy + Retrieval + Evidence + Grounded generation
```

built from an existing LLM (optional, via the provider abstraction), a document parser, local OCR, a document classifier, concept extraction, local embeddings, pgvector, keyword search, a local cross-encoder re-ranker, a plain-language glossary, an answerability guard and a citation checker. All models run locally on CPU; none is trained or tuned on user documents.

Legend: ✅ implemented · 🟡 partial · ⬜ designed, not implemented

## 1. Ingestion

| Step | Status | Where / how |
|---|---|---|
| Upload | ✅ | `POST /documents`; drag & drop, progress, 25 MB limit |
| File validation | ✅ | content type + `%PDF-` magic bytes, safe random file names, never executed (`services/storage.py`) |
| Format detection | ✅ | by content (magic bytes): PDF, DOCX, XLSX, PPTX, DOC, JPG, PNG, TIFF recognised; unsupported ones are refused with "<format> files are not supported yet" (`services/parsing/formats.py`); stored in `documents.format` |
| Document type classification | ✅ | explainable rules over title lines, structure markers, party roles, issuer and headings → taxonomy id, confidence, reasons, alternatives; low confidence never names a type; users confirm / correct (`services/classification.py`) |
| OCR if required | ✅ | pages without a text layer are rendered at 200 dpi and read with RapidOCR (PP-OCR models on ONNX Runtime, local); lines regrouped in reading order with positions; a warning says which pages were OCR'd; up to 60 scanned pages per document (`services/parsing/ocr.py`, `tests/test_ocr.py`) |
| Page-aware text extraction | ✅ | `DocumentParser` interface + registry (`services/parsing/`); `PDFParser` (PyMuPDF, reading order, positioned blocks typed heading / paragraph / list item / footer); diagonal watermarks and stamps (e.g. India Code's "IndiaCode") are removed so they don't split sentences |
| Section detection | ✅ | numbered / keyword / ALL-CAPS headings; statute style `12. Heading.—(1) …` (heading and body on one line), sections ≥ 100 and inserted sections (`4A.`); the table of contents ("Arrangement of Sections"), amendment footnotes (`1. Subs. by Act …`) and Schedules / Statement of Objects and Reasons are kept apart so they never pose as sections (`services/chunking.py`) |
| Clause detection | ✅ | `12.1`, `Section 5(1)(a)`, `Rule 7`, `Chapter II`, `(a)`; sequential-numbering guard |
| Legal concept extraction | ✅ | 44 engine concepts (see [Legal_Concepts.md §5](Legal_Concepts.md)) of 92 in the taxonomy; `services/extraction.py` |
| Fact extraction | ✅ | rule-based; every fact stored with page, clause, exact sentence (leading heading/number clutter removed), rule confidence and normalized value; party roles detected |
| Chunking | ✅ | clause-aware chunks ≤ 900 chars, page preserved |
| Embeddings | ✅ | local `BAAI/bge-small-en-v1.5` (384-d), no API key needed |
| Vector database | ✅ | PostgreSQL + pgvector (`document_chunks.embedding`) |
| Keyword index | ✅ | PostgreSQL full-text index: generated `document_chunks.search_vector` (heading weight A, text weight B) with a GIN index; exact search still uses `ILIKE` |
| Document check (mistakes) | ✅ | spelling, repeated words, number mismatches, missing references, numbering gaps, unclosed brackets, blanks |
| Ready | ✅ | status `ready`; progress shown step by step |

## 2. Question answering

```text
USER QUESTION
  ↓ question understanding     typo correction against document vocabulary ✅
  ↓ concept detection          everyday words → concepts ("leave early" → termination, penalty) ✅
  ↓ plain-language glossary    "builder" → promoter, "salary" → wages, "RTI" → right to information ✅
  ↓ keyword + semantic search  pgvector cosine + PostgreSQL full-text (concept aliases + glossary wording) ✅
  ↓ hybrid retrieval           fused score with concept, fact, heading and clause-structure evidence (§3) ✅
  ↓ cross-encoder re-ranking   MiniLM-L-6 reads question (+ legal wording) and each of the top 12 together ✅
  ↓ answerability guard        subject in the document? best passage relevant? otherwise "not found" ✅
  ↓ relevant clauses           top 6 chunks with page, clause, heading ✅
  ↓ source validation          only retrieved excerpts go to the LLM ✅
  ↓ LLM response               Claude via provider abstraction (optional); extractive answer without a key ✅
  ↓ citation validation        cited excerpt must exist; quote must appear in it; uncited ⇒ "not found" ✅
  ↓ ANSWER + PAGE + CLAUSE + SOURCE TEXT + highlight in the PDF ✅
```

Questions about the tool itself ("Why should I use this?") get a labelled *About ClauseLens* answer, never presented as document content.

## 3. Hybrid search

| Mode | Good for | Status | UI label |
|---|---|---|---|
| Exact | "notice period", "90 days", "salary" | ✅ typo-tolerant fallback | Exact words |
| Semantic | meaning only (kept for comparison) | ✅ | — |
| **Hybrid (default, used by Q&A)** | natural-language questions, exact terms, clause numbers | ✅ | Best match |

`backend/app/services/search.py::hybrid_search`

1. **Candidates** = top 24 by meaning (pgvector cosine) ∪ top 24 by full-text relevance ∪ every chunk of a clause the question names ("Clause 13", "Section 5", "Rule 7").
2. **Keyword query** = the question's words as PostgreSQL's English parser indexes them (so "REV/2026/114" and "1800-000-0000" tokenize exactly like the document), OR-ed with the aliases of the concept the question names first; multi-word aliases become phrase queries built with `phraseto_tsquery` (word order matters).
3. **Score** (kept on the cosine scale, so the "not found" threshold keeps its meaning):

```text
score = cosine_similarity
      + 0.08 × full-text rank / best rank among candidates
      + 0.06 if the chunk contains the query text itself
      + 0.03 × concept keyword hits (max 0.09)
      + 0.06 if the chunk holds a fact of a concept in the question (+0.04 for the primary concept)
      + 0.03 if the clause heading fits the topic
      + 0.30 if it is the clause the question names
```

We chose this weighted fusion over reciprocal rank fusion (considered earlier) because the extractive answer path compares scores with an absolute threshold; RRF scores have no absolute meaning.

4. **Re-ranking** (`services/reranker.py`): a local cross-encoder, `Xenova/ms-marco-MiniLM-L-6-v2` (~80 MB), re-orders the top 12 candidates. It reads the question *together with* each passage, and also sees the legal wording of the question's everyday words from the glossary (`data/taxonomy/plain_language.json`). A clause the question names stays first. Chosen on the dev split of the real-statute set: `BAAI/bge-reranker-base` was slower (~3 s/question) and less accurate. Candidate pool 12 vs 20: same accuracy, faster.
5. **Answerability** (`services/answerability.py`): the question's *subject words* (not question words or generic legal words such as "penalty" or "time limit") must occur in the document — directly or through the glossary — and the best passage's cross-encoder score must be above a calibrated threshold. Otherwise the answer is "not found". This is what stops "What is the penalty for drunk driving?" being answered from the Consumer Protection Act's penalty section.

**Measured on real statutes** — see [Evaluation.md](Evaluation.md) for the India Code set (8 Acts, 44 questions, held-out split) and the before/after numbers of every step.

**Measured on the synthetic samples** (`backend/tests/test_retrieval.py`, 27 labelled queries over a contract, a government notice and an Act/Rules document; before re-ranking):

| | Recall@1 | Recall@3 | MRR | Right page first |
|---|---|---|---|---|
| Semantic only | 0.81 | 0.89 | 0.866 | 0.85 |
| **Hybrid** | **0.93** | **1.00** | **0.963** | **0.96** |

Hybrid fixes clause references ("Clause 13": not found → 1st; "Rule 7": 7th → 1st) and exact identifiers (phone number: 4th → 1st). The test requires hybrid ≥ semantic and Recall@3 ≥ 0.95, MRR ≥ 0.9. As with the other evaluation sets, the queries were written by the developers.

## 4. Answer structure

Answers keep document facts and AI explanation visibly separate:

| Block | Content | UI label |
|---|---|---|
| DOCUMENT SAYS | Only what is supported by cited text | "What the document says" |
| AI EXPLAINS | Plain-language explanation (only with an LLM provider) | "In simple language" / "Why it matters" |
| SOURCE | Page · clause · exact text · View in document | "Source" |

Without an LLM the app never generates explanations; it quotes the document. If nothing relevant is found: *"I couldn't find enough information in the uploaded document to answer this."*

## 5. Confidence

- **Rule-based facts:** fixed confidence per rule, stored with each fact (`legal_facts.confidence`): explicit values 0.85–0.9 (e.g. "ninety (90) days written notice" 0.9, "Laws of India" 0.9), generic amounts 0.8, notes 0.7, keyword-only topic labels 0.6. See `CONFIDENCE` in `services/extraction.py`.
- **Classification:** see [Document_Classification.md §2](Document_Classification.md).
- **Answers:** the answer is shown as found only when the answerability guard passes and at least one citation survives validation.

## 6. Implementation phases (from the brief) and status

| Phase | Scope | Status |
|---|---|---|
| 1 | Document taxonomy | ✅ this change: `data/taxonomy/`, [Document_Taxonomy.md](Document_Taxonomy.md) |
| 2 | Normalized document schema | ✅ this change: `data/schemas/`, `data/examples/`, [Document_Normalization.md](Document_Normalization.md) |
| 3 | PDF parser | ✅ `DocumentParser` interface, `PDFParser`, content-based format detection, `GET /documents/{id}/normalized` (validated against the schema) |
| 4 | Page-aware extraction | ✅ |
| 5 | Document classification | ✅ rule-based classifier with calibrated levels, needs-review flow and user verification; language detection and a trained model remain future work |
| 6 | Legal concept extraction | ✅ 44 of 92 concepts with values (probation, salary, rent, deposit, late fee, interest rate, working hours, leave, job title, area, governing law, jurisdiction, arbitration, cure period, reference number, effective date, contact, court, case number …); confidence + normalized value stored per fact; clean evidence; precision/recall measured (`tests/extraction_cases.py`) |
| 7 | Hybrid search | ✅ full-text index + meaning + concept + structure; default for search and Q&A; Recall@3 1.00, MRR 0.963 on the retrieval set |
| 8 | RAG | ✅ grounded Q&A with optional Claude |
| 9 | Citation system | ✅ validated citations |
| 10 | PDF source navigation and highlighting | ✅ exact words highlighted, honest when not found |
| 11 | DOCX, JPG, JPEG, PNG | ⬜ |
| 12 | Advanced document types (court structure, financial, property) | ⬜ |

## 7. Quality metrics

Measured by `backend/tests/evaluation_cases.py` today (25 questions, 3 document types, all passing) and extended as described in [Training_Dataset_Schema.md §8](Training_Dataset_Schema.md): classification accuracy and calibration; concept precision/recall; date and amount accuracy; Recall@K, Precision@K, MRR and relevant-page accuracy; groundedness, citation correctness and unsupported-claim rate; OCR text quality and page preservation.
