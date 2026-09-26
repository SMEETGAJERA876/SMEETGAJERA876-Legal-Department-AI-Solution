# Security & privacy

Legal and official documents are personal. Every control below is implemented and covered by
automated tests (`backend/tests/test_auth.py`, `test_security.py`, `test_demo.py`).

| Threat | Control | Where |
|---|---|---|
| Someone else opens my document | Google sign-in verified server-side (signature, issuer, audience, expiry, Google provider, verified email); ownership check on every `/documents/{id}` route; others get **404** | `core/auth.py` |
| The public demo weakening all of the above | Only documents flagged `is_demo` — seeded by `scripts.seed_demo`, owned by a user with no Firebase uid — are readable without a token, and only for reads plus `…/ask`; every write answers **403**. A token that is *sent* but invalid still fails, so demo access cannot mask a broken sign-in. `DEMO_MODE_ENABLED=false` closes it | `core/auth.py`, [Demo.md](Demo.md) |
| A stolen disk, backup or uploads folder | Files encrypted with **AES-256-GCM** (authenticated: tampering is detected); the key is outside the database | `services/storage.py` |
| Brute force / flooding / abuse of the AI | Per-client rate limits (uploads 20/10 min, questions 30/min, other 300/min) with friendly `429` + `Retry-After` | `core/security.py` |
| Clickjacking, MIME sniffing, leaking URLs | `X-Frame-Options: DENY`, CSP `default-src 'none'; frame-ancestors 'none'`, `nosniff`, `Referrer-Policy: no-referrer`, HSTS in production, `Cache-Control: no-store` | `core/security.py` |
| Malicious uploads | Type from file content (not name), size limit, random stored names, never executed, parsed by PyMuPDF only | `services/storage.py`, `parsing/` |
| Hidden access to data | Audit log of uploads, views, downloads, repairs, type changes, deletions; users see their own log | `services/audit.py`, `GET /account/activity` |
| Keeping data forever | "Delete all my documents" (right to erasure); optional automatic retention (`RETENTION_DAYS`) | `DELETE /account/documents`, `services/lifecycle.py` |
| Insecure deployment | With `ENVIRONMENT=production` the API refuses to start without sign-in, an encryption key, a specific CORS origin and rate limits | `core/security.py::check_production_settings` |
| Leaking internals | Uniform error format, no stack traces to clients | `main.py` |
| AI making things up | Answers only from the document, with citations checked against it; "not found" when the subject isn't in the document | `services/answerability.py`, [Evaluation.md](Evaluation.md) |
| Training on user data | Uploads are never used to train or tune models; evaluation uses public statutes and synthetic samples only | [Data_Governance.md](Data_Governance.md) |

## Secrets

- `backend/.env`, `frontend/.env.local`, `.env.production` are git-ignored; only `*.example`
  files are committed.
- The Firebase web config (`NEXT_PUBLIC_FIREBASE_*`) is public by design; the server verifies
  tokens with Google's public keys and needs no service-account key.
- **Back up `FILE_ENCRYPTION_KEY`.** Without it stored files cannot be read.

## Known limits

- Rate-limit counters are per API process (use Redis when running several replicas).
- HTTPS is terminated by the reverse proxy in front of the containers (not by the app itself).
- The optional Claude provider sends the retrieved excerpts (not the whole file) to Anthropic's
  API; it is off by default (`AI_PROVIDER=none`).
