# API

Interactive documentation (OpenAPI) is served by the running API at
`http://localhost:8000/docs`; the machine-readable schema at `/openapi.json`.

## Authentication

Every endpoint except `/health` needs `Authorization: Bearer <Firebase ID token>` from a Google
sign-in. Without it: `401 not_signed_in`; invalid or expired: `401 session_expired`; another
sign-in method: `401 google_required`. A document that belongs to someone else answers
`404 not_found` on every route.

## Errors

Always `{"error": "<code>", "message": "<plain-language sentence>"}` — never a stack trace.

| Status | Codes |
|---|---|
| 400 | `unknown_document_type`, `empty_file`, `nothing_to_fix`, `issues_changed` |
| 401 | `not_signed_in`, `session_expired`, `google_required`, `email_required`, `invalid_token` |
| 404 | `not_found` |
| 409 | `document_not_ready` |
| 413 / 415 | `file_too_large`, `unsupported_file_type` |
| 422 | `invalid_request`, `repair_failed` |
| 429 | `too_many_requests` (with `Retry-After`) |
| 503 | `auth_not_configured` |

## Rate limits (per client)

Uploads and corrected copies: 20 per 10 minutes · questions: 30 per minute · everything else:
300 per minute. `/health` is never limited.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness and database reachability (public) |
| POST | `/documents` | Upload a PDF (multipart `file`); processing starts in the background |
| GET | `/documents` | The signed-in user's documents, newest first |
| GET | `/documents/types` | Document types for the type picker |
| GET | `/documents/concepts` | Legal concepts and their labels |
| GET | `/documents/{id}` | Status, type, classification, parties |
| DELETE | `/documents/{id}` | Delete the document, its file and all extracted data |
| PUT | `/documents/{id}/classification` | The user confirms or corrects the document type |
| GET | `/documents/{id}/file` | The original PDF (`?download=true` to save it) |
| GET | `/documents/{id}/overview` | Key facts grouped by concept, with sources |
| GET | `/documents/{id}/search?q=…&mode=hybrid\|exact\|semantic` | Search with highlighted snippets |
| POST | `/documents/{id}/ask` | `{"question", "conversation_id"?}` → answer, citations, related concepts |
| GET | `/documents/{id}/questions` | Questions to discuss with a legal professional |
| GET | `/documents/{id}/issues` | Spelling/format mistakes with page and suggestion |
| POST | `/documents/{id}/repair` | `{"issue_ids": […]}` → a corrected copy (the original is kept) |
| GET | `/documents/{id}/summary` | One-file PDF summary: dates, notices, deadlines, money, questions |
| GET | `/documents/{id}/normalized` | The document in the normalized JSON schema (`data/schemas`) |
| GET | `/account/activity` | The user's audit log, newest first |
| DELETE | `/account/documents` | Delete every document of the user ("right to erasure") |

### Example: ask

```http
POST /documents/3f…/ask
Authorization: Bearer eyJhbGciOi…
Content-Type: application/json

{"question": "How many days do I have to appeal against the District Commission's order?"}
```

```json
{
  "found": true,
  "answer": "The most relevant part of the document (Page 25, Clause 41) says: “Any person aggrieved by an order made by the District Commission may prefer an appeal … within a period of forty-five days …”",
  "citations": [{"page_number": 25, "clause_ref": "41", "heading": "Appeal against order of District Commission", "quote": "…"}],
  "generated_by": "none",
  "kind": "document"
}
```
