# Data Governance

Legal and official documents are sensitive: contracts, salaries, court cases, ID numbers. ClauseLens treats every upload as private by default.

## 1. What happens to an uploaded document

| Question | Answer today |
|---|---|
| **Stored?** | Yes. The file is saved on the server under a random name (`backend/storage/uploads/`), **encrypted with AES-256-GCM**, and its text, chunks and extracted facts in PostgreSQL, linked to the owner's Google account. |
| **Processed?** | Yes, on the server: text extraction (OCR for scanned pages), clause detection, fact extraction, local embeddings and re-ranking. No model sees documents of other users. |
| **Indexed?** | Yes, for this document only (vector + keyword search). Documents are never mixed in search. |
| **Sent to a third party?** | Only when the optional AI provider is enabled (`AI_PROVIDER=anthropic`): the few retrieved excerpts for a question are sent, never the whole file. With `AI_PROVIDER=none`, nothing leaves the server. Embeddings run locally. |
| **Used for training?** | **No.** Never automatically. |
| **Deleted?** | Yes, on request: "Delete" removes the file, pages, chunks, facts, conversations and citations (cascading deletes); "Delete all my documents" does it for everything; `RETENTION_DAYS` does it automatically. Each deletion is recorded in the user's activity log. |

The sign-in page and *Privacy & activity* (account menu) show this summary to users.

## 2. Controls

| Control | Status |
|---|---|
| Safe file names (random), no user-controlled paths | ✅ |
| File type validation by content, size limit | ✅ |
| Uploaded files are never executed | ✅ |
| Document deletion with cascade | ✅ |
| Corrected copies never overwrite originals | ✅ |
| No automatic model training on uploads | ✅ (no training pipeline reads user tables) |
| User accounts: Google sign-in (Firebase Authentication) | ✅ `app/core/auth.py`: the Firebase ID token is verified on every request (Google's signature, our project as audience and issuer, not expired) and the sign-in method must be Google with a verified email. The server stores only the Firebase user id, email and name. |
| Per-user document isolation | ✅ every document has an owner; the list shows only your documents |
| Access control on every document endpoint | ✅ router-level guard on all `/documents/{id}…` routes (view, file, download, search, ask, check, repair, summary, classification, delete): another user's document answers **404**, so it's not even revealed that it exists. Corrected copies belong to the original's owner. Tested in `tests/test_auth.py`. |
| Sign-in off for local development | `AUTH_MODE=disabled` (backend) + `NEXT_PUBLIC_AUTH_MODE=disabled` (frontend): everything belongs to one "local user". **Never deploy with sign-in disabled.** Move those documents to your account with `uv run python -m scripts.assign_documents you@gmail.com`. |
| Encryption at rest | ✅ uploaded files are AES-256-GCM encrypted by the app (`FILE_ENCRYPTION_KEY`, required in production); tampering is detected. Database disk encryption remains a deployment setting of the managed database. |
| Retention controls | ✅ `RETENTION_DAYS` deletes documents automatically (checked at start-up and every 6 h); users can delete one or **all** of their documents at any time (`DELETE /account/documents`) |
| Audit log (upload, view, download, delete, repair) | ✅ `audit_events`; users see their own log in *Privacy & activity* (`GET /account/activity`) |
| Rate limiting and security headers | ✅ `core/security.py` — see [Security.md](Security.md) |
| Safe production configuration | ✅ the API refuses to start in production without sign-in, encryption key, specific CORS origin and rate limits |

## 3. Training data consent

If user documents are ever collected for training or evaluation:

1. **Explicit opt-in per document**, separate from uploading, never pre-ticked, with a plain explanation of what is kept and why.
2. Consent is recorded (who, when, which document, which purpose) and can be withdrawn; withdrawal removes the document from future dataset versions.
3. The document is **copied** into the dataset area after anonymisation; the user's copy stays under the user's control.
4. Dataset metadata records `source_type: user_contributed_with_consent`, `permission_status: consent_given`, `privacy_status: anonymised`.

## 4. Dataset sources

Only documents we have the right to use ([Training_Dataset_Schema.md §4](Training_Dataset_Schema.md)): project-created synthetic documents, public-domain or openly licensed government publications (with the licence recorded), licensed collections, or consented contributions. No indiscriminate scraping of the internet.

**India Code (evaluation set).** Eight central Acts were downloaded from https://indiacode.gov.in through its public DSpace REST API (`backend/scripts/fetch_indiacode.py`: read-only, one request at a time, with pauses). Each PDF is stored with its source URL, Act number, ministry and retrieval date (`dataset/indiacode/*.json`). Acts are statutes; the Copyright Act, 1957, s. 52(1)(q) permits reproducing them. They are used **only to evaluate** ClauseLens — no model is trained on them.

## 5. Indian context

- Aadhaar, PAN, bank account and phone numbers must be masked before any document enters a dataset.
- Treat personal data in line with India's Digital Personal Data Protection Act, 2023 (purpose limitation, consent, erasure on request). This is a design requirement, not legal advice; a compliance review is needed before a public launch.

## 6. Safety of answers

ClauseLens provides information about documents, not legal advice. It never invents clauses, dates, amounts, obligations or rights; never predicts court outcomes; and says so when the document does not contain the answer.
