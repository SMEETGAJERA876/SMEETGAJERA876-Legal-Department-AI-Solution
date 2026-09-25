# Document Classification

**Status:** implemented (Phase 5) as an explainable rule-based classifier: `backend/app/services/classification.py`. Language detection and a trained model are still future work. Results are stored on the document (`document_type_id`, `category`, `classification`) and users can confirm or correct them (`PUT /documents/{id}/classification`, picker from `GET /documents/types`).

Classification answers *"What is this document?"* so the rest of the pipeline knows which structure and which concepts to expect. It produces the `document.classification` object in the [normalized document](../data/schemas/normalized_document.schema.json).

## 1. Pipeline

```text
File format detection      (bytes → pdf / docx / jpg ...)       deterministic
        ↓
Language detection         (en, hi, gu ...)                     per page, then document
        ↓
Category classification    (government, court, employment ...)  11 categories
        ↓
Document type classification (court.judgment, legal.nda ...)    within / near the category
        ↓
Structure classification   (sections found vs expected)         confirms or weakens the type
        ↓
Confidence + status        (high / medium / low → confirmed / needs_review / unknown)
```

### 1.1 File format detection

- By **content (magic bytes)**, never by file extension alone: `%PDF-` → pdf; `PK\x03\x04` + `word/document.xml` → docx; `\xFF\xD8\xFF` → jpeg; `\x89PNG` → png; `II*\0`/`MM\0*` → tiff.
- Extension and declared MIME type are recorded but untrusted ([Rules §14](../Rules.md.txt)).
- Output: `document.format`, `document.mime_type`, `document.is_scanned` (no text layer on ≥ 50% of pages).

### 1.2 Language detection

- Script detection first (Devanagari → hi/mr, Gujarati → gu, Tamil → ta …), then a language identifier on text.
- MVP processes English only. Documents detected as another language are stored and viewable, and the user is told that search and extraction are English-only for now.

### 1.3 Category and type

Signals, in order of strength:

| Signal | Example | Weight |
|---|---|---|
| Title / heading keywords (first page, first ~400 chars) | "EMPLOYMENT AGREEMENT", "PUBLIC NOTICE", "IN THE HIGH COURT OF" | high |
| Structural markers | "CORAM", "Petitioner … versus … Respondent", "Rules, 2026", "these rules may be called" | high |
| Party / role vocabulary | Employer/Employee, Landlord/Tenant, Borrower/Lender | medium |
| Section headings present | Probation + Salary + Termination; Eligibility + Last date + Documents required | medium |
| Issuer | "Government of …", "Ministry of …", company letterhead | medium |
| Body keywords | title_keywords of each type in [document_types.json](../data/taxonomy/document_types.json) | low |

**MVP method (rules):** score every type from its `title_keywords` (title area × 3, first page × 1), add structure and role bonuses, normalise scores to a probability-like confidence, keep the top 3 as `alternatives`, and record human-readable `signals`.

**Later (model):** a small text classifier (e.g. logistic regression or a fine-tuned small encoder over the first pages' text + headings) trained on the licensed dataset ([Training_Dataset_Schema.md](Training_Dataset_Schema.md)). An LLM can be used as a tie-breaker only between the top alternatives, with the evidence it relied on — never as the only signal.

### 1.4 Structure classification

After section detection, compare the sections found with the type's `typical_structure`. A judgment with no parties, no case number and no order is probably not a judgment; lower the confidence and promote the next alternative.

## 2. Confidence and status

| Confidence | Level | Status | What the user sees |
|---|---|---|---|
| ≥ 0.80 | high | `confirmed` | "Employment agreement" |
| 0.50 – 0.79 | medium | `confirmed` | "Looks like an employment agreement" + "Change" link |
| < 0.50 | low | `needs_review` | "We're not sure what kind of document this is." + top 3 choices + "Other" |
| no usable signal | low | `unknown`, `document_type: null` | "Document type: Unknown" (everything else still works) |
| user picked | — | `user_verified` | The user's choice, used from then on |

The schema enforces that a **low-confidence classification can never be `confirmed`**.

## 3. Fallbacks

- **Unknown** — `document_type: null`, `status: unknown`. Generic extraction (dates, amounts, notices, deadlines, parties) still runs.
- **Other** — `other.letter`, `other.certificate`, … when the document is clearly an official document of a known kind that has no specific type.
- **Needs review** — shown to the user as a question, not an error.

Never force a low-confidence classification: a wrong type is worse than "unknown", because it makes the app look for the wrong things.

## 4. Examples

| Input | Category | Type | Format | Confidence | Notes |
|---|---|---|---|---|---|
| `appointment_letter.pdf` | Employment | `employment.appointment_letter` | PDF | High | "pleased to appoint" in title area |
| `government_notification.pdf` | Government | `government.notification` | PDF | High | "Notification", "it is hereby notified" |
| `judgment.jpg` | Court / Judicial | `court.judgment` | JPG | High after OCR | **OCR required**; classification waits for OCR text |
| `scan_0012.pdf` (blurry, 1 page) | — | `null` | PDF | Low | `needs_review`: user asked to choose |

## 5. Implemented scoring (rules)

| Signal | Weight |
|---|---|
| Type keyword in a heading-style line at the top (mostly capitals, first 10 lines) | 4.5 × specificity |
| Type keyword elsewhere in the first 400 characters | 3.0 × specificity |
| Type keyword elsewhere on the first page | 1.0 × specificity |
| Specificity | 1.0 for phrases ("employment agreement"), 0.5 for single words ("tender") |
| Structural markers ("CORAM", "these rules may be called", "solemnly affirm" …) | +1 to +3 to a type |
| Section headings (≥ 2 of probation / salary / termination …) | +1 to +1.5 to a type |
| Party roles and issuer (employer + employee, landlord + tenant, petitioner + respondent, Government of …) | +1 to +2 to a category; shared with types that already have evidence (secondary categories get half) |

`confidence = 0.35 + 0.6 × min(1, best / 4.5) × (0.5 + 0.5 × (best − second) / best)`, capped at 0.97; alternatives share the remainder in proportion to their scores. Below a score of 1.5 nothing is suggested; a generic title word ("AGREEMENT", "NOTICE") then gives a category only, with `needs_review`.

Documents classified before a rule change can be re-classified with `uv run python -m scripts.reclassify` (user-verified types are kept unless `--all`).

## 6. Evaluation

Metrics (see [Training_Dataset_Schema.md §8](Training_Dataset_Schema.md)): type accuracy, category accuracy, macro-F1 across types, and **confidence calibration** (of the documents labelled "high", ≥ 90% must be correct; expected calibration error reported per release).

Today: `backend/tests/classification_cases.py` — 34 invented first pages across government, court, employment, contract, property, financial, corporate, policy and education documents, including tricky ones (a judgment that discusses an employment agreement, a circular that mentions tenders, a bare "AGREEMENT" title). All pass; every "high" answer is correct; low confidence never names a type. **Caveat:** these cases were written by the developers who wrote the rules, so they measure coverage, not real-world accuracy. A held-out set of real (licensed, anonymised) documents is needed before quoting an accuracy figure.
