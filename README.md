# ClauseLens AI

Understand what your legal document says — upload a PDF, ask questions in plain language, and jump straight to the supporting page and clause.

## Try it without signing in

**[/demo](docs/Demo.md)** opens a real 42-page Act of Parliament (Consumer Protection Act 2019,
from India Code), a sample employment contract and a rental agreement with deliberate mistakes —
no Google account, no upload. Search them, ask questions, click any answer to jump to the page and
see the exact wording highlighted, and ask something the Act *doesn't* cover to watch it say
**"not found"** instead of guessing. Uploading your own document still needs Google sign-in, and
those documents stay private to your account. Details: [docs/Demo.md](docs/Demo.md).

Specs: [Problem statement](ProblemStatement.md.txt) · [PRD](PRD.md.txt) · [Architecture](Architecture.md.txt) · [Design](Design.md.txt) · [Phases](Phases.md.txt) · [Rules](Rules.md.txt)

**Docs:** [Public demo](docs/Demo.md) · [Plain language](docs/Plain_Language.md) · [Official formats](docs/Formats.md) · [Architecture](docs/Architecture.md) · [AI pipeline](docs/AI_Pipeline.md) · [Evaluation](docs/Evaluation.md) · [API](docs/API.md) · [Database](docs/Database.md) · [Security](docs/Security.md) · [Deployment](docs/Deployment.md) · [Demo script](docs/Demo_Script.md)

## Why it matters

Employees, tenants, home buyers and citizens receiving government notices sign or act on documents they can't fully read, and a lawyer isn't always affordable. General chatbots answer confidently without showing where an answer comes from. ClauseLens answers **only from the document**, always with the **page, section and highlighted wording**, and says **"not found"** when the document doesn't cover the question.

**Measured on real Indian statutes** (8 central Acts from India Code, held-out split — [Evaluation](docs/Evaluation.md)): the right section is in the top 3 results for **100 %** of held-out questions (first result: 86 %), answers cite the right section **100 %** of the time, and questions the Act doesn't cover are refused instead of guessed. Answers take about **1 second** on a laptop CPU.

## What works

- **Upload** a PDF (drag & drop or file picker, progress bar, validation with clear error messages). **Scanned PDFs** are read with local OCR.
- **Processing** with live status: pages → clauses → embeddings → key facts. Page numbers are always preserved (Document → Page → Chunk → Clause → Source).
- **Overview**: document type, parties, counts, and key facts (notice periods, dates, amounts, termination, renewal, penalties, disputes, confidentiality, liability) — each linked to its page and clause.
- **Search** by exact words or **best match** (meaning + keywords + clause numbers) ("What notice do I need before leaving?" finds "ninety (90) days written notice").
- **Ask your document**: grounded answers with citations; follow-up questions; says so when the document doesn't answer. A local **re-ranker** and a **plain-language glossary** ("builder" → promoter, "salary" → wages) find the right section; an **answerability guard** refuses questions the document doesn't cover.
- **Real statutes**: understands Indian Acts as published on India Code — `12. Heading.—(1) …` sections, chapters, tables of contents, amendment footnotes, schedules, watermarks.
- **Source navigation**: "View in document" opens the page and highlights the exact wording (and says so if the wording can't be pinpointed).
- **Related topics** and **questions for a legal professional**, each with a source.
- **Works across document types**: contracts, agreements, leases, NDAs, and government documents — public notices, circulars, orders, notifications, schemes, Acts/Rules, tenders, court orders, affidavits, and more. Understands numbering like `12.1`, `Section 5(1)(a)`, `Rule 7`, `Chapter II`, `Para 4` and ALL-CAPS headings.
- **Finds a whole "type" at once**: searching "notice period" also lists every deadline/time limit ("within 15 days", "on or before 30 April 2026") and every important note, each with its page.
- **Typo-tolerant**: "notice pperiod" → "Showing results for notice period".
- **Exact-word search marks the exact word** on the page, not just the paragraph.
- **Questions about the tool itself** ("Why should I use this?", "Why not a general-purpose assistant?") get a clearly labelled "About ClauseLens" answer — never presented as document content.

### Plain language, both ways

Official documents are written in a language most of the people bound by them do not speak, so
ClauseLens translates in both directions ([docs/Plain_Language.md](docs/Plain_Language.md)):

- **Your words → the document's words**, to *find* the passage: you ask about a "builder"; the Act
  says **promoter**, and the answer tells you so.
- **The document's words → your words**, to *understand* it: "person aggrieved" becomes **person
  affected**, "forty-five days" becomes **45 days**. Every answer carries an *In simple words*
  section and any quoted passage has a **Simple words** button that also explains each formal term.

The plain version always sits **beside** the original, never instead of it, and is labelled as a
simplification. The rewriter is a reviewable dictionary plus a few changes that cannot alter
meaning — it never drops a number, date, amount, party or negation, and tests hold it to that. It
needs **no AI key**.

### Compare with the official format

The **Format** tab compares the document against the form the law or the issuing authority asks
for ([docs/Formats.md](docs/Formats.md)) — rent and lease agreements, employment letters,
affidavits, RTI applications, legal notices, sale deeds, and Acts as published. Each expected part
is reported as **found** (with its page and wording), **left blank** (`Date: ______`) or
**missing**, with one sentence saying what it is for and which provision asks for it. On the
demo's rental agreement: 6 of 11 required parts, no stamp duty details, no signatures, no
witnesses.

It is a checklist, not a ruling: a part written in unusual words can be reported missing, so every
finding shows the page and the exact words, and the panel says so.

### Check document and auto-repair

The **Check document** tab lists likely mistakes, each with its page, the exact words (click to see them marked on the page) and a suggestion:

- **Can be fixed automatically** — spelling mistakes (`tenent` → `tenant`) and repeated words (`the the` → `the`). Tick the ones you want, click **Auto-repair**, confirm in the pop-up, and a new **corrected PDF** is created (same layout, only those words changed) that you can **download** or open. The original file is never changed, and the corrected copy lists every change made.
- **Needs your review** — never changed automatically because they can change the meaning: numbers in words and digits that disagree (`ninety (60) days`), references to clauses that don't exist, missing or duplicated clause numbers, unclosed brackets, unfilled blanks (`______`).

A corrected copy of a signed or officially issued document is not a replacement for it — the app says so before making changes.

### Summary PDF

**Summary PDF** (top of every document, and in the overview) downloads one short, formatted PDF with: an *At a glance* box (notice periods, deadlines, duration, amounts), tables of dates / notice periods / deadlines, money / fees / penalties, process / rights / responsibilities and important notes — every line with the original wording and its page and clause — plus the *Needs your attention* items from the document check and *Questions to ask a legal professional*. It only contains what the document says. (Built-in PDF fonts: non-Latin scripts are not rendered yet.)

### Answers with or without an AI key

Semantic search uses a small local embedding model (downloaded once, ~70 MB) — no API key needed.

- `AI_PROVIDER=none` (default): answers quote the document directly, with sources.
- `AI_PROVIDER=anthropic` + `AI_API_KEY=...` in `backend/.env`: Claude (`claude-opus-5` by default) adds plain-language explanations and "why it matters". The model only sees retrieved excerpts; every citation is checked against the document, and uncited answers are shown as "not found". Server-side refusal fallbacks are enabled.

### Google sign-in (Firebase)

Documents are private to the Google account that uploaded them. Sign-in is off until you add your Firebase project:

1. [Firebase console](https://console.firebase.google.com) → **Add project**.
2. **Build → Authentication → Get started → Sign-in method → Google → Enable** (pick a support email) → Save.
3. **Authentication → Settings → Authorized domains**: `localhost` is there by default; add your deployed domain later.
4. **Project settings (⚙) → Your apps → Web (`</>`)** → register an app → copy `apiKey`, `authDomain`, `projectId`, `appId`.
5. `frontend/.env.local`: `NEXT_PUBLIC_AUTH_MODE=firebase` and the four `NEXT_PUBLIC_FIREBASE_*` values.
   `backend/.env`: `AUTH_MODE=firebase` and `FIREBASE_PROJECT_ID=<projectId>`. Restart both servers.
6. Sign in once, then move documents uploaded before sign-in to your account:
   `cd backend && uv run python -m scripts.assign_documents you@gmail.com`

No service-account key is needed: the backend verifies tokens with Google's public keys.

### Security & privacy

Private to the uploading Google account (others get "not found") · files **encrypted at rest** (AES-256-GCM, `FILE_ENCRYPTION_KEY`) · rate limits and security headers · **audit log** and a *Privacy & activity* view in the account menu · **delete all my documents** · optional automatic retention (`RETENTION_DAYS`) · the API refuses to start an insecure production configuration. Details: [docs/Security.md](docs/Security.md).

## Documentation (document intelligence system)

| Document | What it defines |
|---|---|
| [docs/Document_Taxonomy.md](docs/Document_Taxonomy.md) | 11 categories, 178 document types with stable ids (`court.judgment`, `legal.nda`…), structures, OCR needs; file format ≠ document type |
| [docs/Legal_Concepts.md](docs/Legal_Concepts.md) | 92 legal concepts (id, aliases, value type, examples) and how they map to the running engine |
| [docs/Document_Classification.md](docs/Document_Classification.md) | Format → language → category → type → structure → confidence; never force a low-confidence type |
| [docs/Document_Normalization.md](docs/Document_Normalization.md) | The one internal structure every parser produces; `DocumentParser` interface |
| [docs/AI_Pipeline.md](docs/AI_Pipeline.md) | Ingestion and Q&A pipeline, hybrid search, answer structure, **implementation status per phase** |
| [docs/Training_Dataset_Schema.md](docs/Training_Dataset_Schema.md) | Dataset layout, metadata, annotations, splits without leakage, metrics |
| [docs/Data_Governance.md](docs/Data_Governance.md) | What happens to uploads; no training on user documents without explicit consent |
| [docs/Evaluation.md](docs/Evaluation.md) | Every evaluation set, method, before/after results, held-out split, latency |
| [docs/Architecture.md](docs/Architecture.md) · [docs/API.md](docs/API.md) · [docs/Database.md](docs/Database.md) | System design, endpoints, schema |
| [docs/Security.md](docs/Security.md) · [docs/Deployment.md](docs/Deployment.md) | Threats and controls; Docker / cloud deployment, backups, scaling |
| [docs/Demo.md](docs/Demo.md) | The public read-only demo: what a visitor may do, how the access rule works, how to seed it |
| [docs/Plain_Language.md](docs/Plain_Language.md) | Translating both ways, and the rule that keeps a simplification safe |
| [docs/Formats.md](docs/Formats.md) | The official formats documents are compared against, and how to add one |

Machine-readable: `data/schemas/` (JSON Schema 2020-12), `data/taxonomy/`, `data/formats/`, `data/examples/`, `dataset/`. `backend/tests/test_taxonomy_data.py` keeps them consistent with each other, with the docs, and with the extraction engine.

## Structure

```
frontend/   Next.js + TypeScript + Tailwind + shadcn/ui + TanStack Query + react-pdf
  src/app/                     home (upload + documents), /documents/[id] workspace,
                               /demo (public, no sign-in)
  src/components/workspace/    PDF viewer, search, overview, ask panels
  src/lib/                     API client (zod-validated), highlight matching
backend/    FastAPI + SQLAlchemy + Alembic + pgvector (Python, managed with uv)
  app/
    api/routes/   HTTP endpoints (/health, /documents/...)
    core/         settings (.env), error types
    models/       users, documents, document_pages, document_chunks, clauses,
                  legal_facts, conversations, messages, citations
    services/     pdf_extraction, chunking, concepts, embeddings, search,
                  ai_provider, qa, questions, processing, storage,
                  simplify (formal → everyday wording), formats (official formats)
  migrations/     Alembic migrations
  scripts/        dev_db.py (local PostgreSQL + pgvector, no Docker), make_sample_pdf.py,
                  fetch_indiacode.py (real Acts), benchmark.py, new_encryption_key.py
  tests/          unit, API, auth, security, OCR and evaluation tests
dataset/indiacode/  8 central Acts from India Code with source metadata (evaluation only)
samples/    demo documents (fictional): employment_agreement.pdf (notice period on Page 7,
            Clause 12), government_public_notice.pdf, tenancy_rules.pdf,
            rental_agreement_with_mistakes.pdf (for Check document / auto-repair)
            regenerate with: cd backend && uv run python -m scripts.make_sample_pdf
docker-compose.yml       PostgreSQL + pgvector for development (alternative to scripts/dev_db.py)
docker-compose.prod.yml  full stack: database + API + website (see docs/Deployment.md)
.github/workflows/ci.yml lint, type checks, tests and build on every push
```

## Running locally

1. **Database** — PostgreSQL + pgvector on `localhost:5433`. Pick one:
   - No Docker needed (bundled PostgreSQL 16 + pgvector, data kept in `backend/.pgdata/`):
     ```
     cd backend
     uv run scripts/dev_db.py start     # also: stop, status
     ```
   - Or with Docker: `docker compose up -d db`
2. **Backend**
   ```
   cd backend
   cp .env.example .env
   uv run python -m scripts.new_encryption_key >> .env   # encrypt uploaded files at rest
   uv sync
   uv run alembic upgrade head
   uv run uvicorn app.main:app --port 8000
   ```
   The first start downloads the local AI models once (embeddings ~70 MB, re-ranker ~80 MB, OCR ~15 MB).
   Check: `curl http://localhost:8000/health` returns `status: ok`. API docs: http://localhost:8000/docs.
   On Windows, `--reload` can hang after a code change (the embedding model's threads keep the old worker alive) — restart the server instead.
3. **Frontend**
   ```
   cd frontend
   cp .env.example .env.local
   npm install
   npm run dev
   ```
   Open http://localhost:3000 and upload `samples/employment_agreement.pdf` to try it.
4. **Public demo** (optional) — load the three documents that http://localhost:3000/demo shows
   without sign-in:
   ```
   cd backend
   uv run python -m scripts.seed_demo
   ```

## Evaluation

**Real statutes (India Code).** `uv run python -m scripts.fetch_indiacode` downloads 8 central Acts; `tests/test_real_documents.py` asks 44 citizen-style questions (checked by hand against the Acts), plus 8 questions the Acts don't answer, with a **dev/held-out split**. Results and method: [docs/Evaluation.md](docs/Evaluation.md). Performance: `uv run python -m scripts.benchmark`.

**Synthetic samples.** `backend/tests/evaluation_cases.py` lists 25 real questions across the three sample documents (contract, government notice, Act/Rules) with the page each answer must point to — including typos, "notice period" type searches, missing information, and "why use this?". They run as part of `uv run pytest`, and as a readable report against the running server:

```
cd backend
uv run python -m scripts.evaluate      # prints PASS/FAIL per question; currently 25/25
```

## Checks

- Backend: `uv run pytest` (202 tests; integration tests use the `clauselens_test` database created by `dev_db.py`), `uv run ruff check app tests scripts`, `uv run mypy app scripts`
- Frontend: `npm run typecheck`, `npm run lint`, `npm run build`

## Progress

- [x] Phase 0–1 — Project structure, Next.js, FastAPI, config, `/health`
- [x] Phase 2 — Database schema + migrations
- [x] Phase 3 — Document upload
- [x] Phase 4 — PDF processing
- [x] Phase 5 — Exact search
- [x] Phase 6 — PDF viewer
- [x] Phase 7 — Semantic search
- [x] Phase 8 — Legal concept extraction
- [x] Phase 9 — Document Q&A
- [x] Phase 10 — Source navigation + highlighting (**MVP complete**)
- [x] Phase 11 — Related clauses
- [x] Phase 12 — Questions for a legal professional
- [x] Multi-document-type support (government documents), typo tolerance, evaluation suite
- [x] Check document: mistakes with page + suggestion, auto-repair into a downloadable corrected PDF
- [x] Summary PDF download
- [x] Google sign-in (Firebase Authentication) with per-user private documents
- [x] Real-document evaluation on 8 India Code Acts with a held-out split; statute structure (sections, contents, footnotes, schedules, watermarks)
- [x] Cross-encoder re-ranking, plain-language glossary, answerability guard (refuses questions the document doesn't cover)
- [x] OCR for scanned PDFs (local RapidOCR)
- [x] Encryption at rest, rate limits, security headers, audit log, *Privacy & activity*, delete all my data, retention, crash recovery, safe production start-up
- [x] Docker images, production compose file, CI workflow, benchmark, architecture / API / database / security / deployment docs
- [x] Intelligence system Phase 7: hybrid search (PostgreSQL full-text + meaning + concepts + clause references) as the default "Best match" and for Q&A; retrieval metrics vs meaning-only in `tests/test_retrieval.py`
- [x] Intelligence system Phase 6: 44 extracted concepts (salary, probation, rent, deposit, working hours, leave, governing law, arbitration, reference numbers, court/case numbers …) with confidence, normalized values, party roles and clean evidence; precision/recall tests. Re-run on stored documents: `uv run python -m scripts.reprocess`
- [x] Intelligence system Phase 5: document classification (taxonomy type + confidence + reasons; "We're not sure — choose the type" flow; user-verified types)
- [x] Intelligence system Phase 3: `DocumentParser` interface + `PDFParser`, content-based format detection (DOCX/images recognised and refused with a clear message), `GET /documents/{id}/normalized`
- [x] Intelligence system Phase 1–2: document taxonomy, legal concepts, normalized document schema, dataset layout, design docs (see docs/AI_Pipeline.md §6 for the next phases)
- [x] Public read-only demo: three seeded documents anyone can use without signing in, writes refused for everyone ([docs/Demo.md](docs/Demo.md))
- [x] Plain-language translation both ways (everyday ↔ formal), local and with no AI key, always shown beside the original ([docs/Plain_Language.md](docs/Plain_Language.md))
- [x] Comparison against the official format for seven kinds of Indian legal and government document, with page-level evidence ([docs/Formats.md](docs/Formats.md))
- [x] Site footer on every page
- [ ] Phase 13 — Contract comparison
- [ ] Live deployment (needs a hosting account) and a recorded demo video
