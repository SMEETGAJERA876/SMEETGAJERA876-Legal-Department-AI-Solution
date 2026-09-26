# The public demo

Anyone can use ClauseLens on a real document without signing in: **[/demo](/demo)**. It exists
because the thing worth judging — an answer that points at the page it came from, and a refusal
when the document doesn't cover the question — cannot be shown behind a Google sign-in wall.

## What a visitor can do

| | Without signing in | Signed in with Google |
|---|---|---|
| Open the seeded demo documents | ✅ | ✅ |
| Search (exact words / best match) | ✅ | ✅ |
| Ask questions, follow-ups, refusals | ✅ | ✅ |
| Jump to the source and see it highlighted | ✅ | ✅ |
| Overview, key facts, questions for a professional | ✅ | ✅ |
| Check document (list the mistakes) | ✅ | ✅ |
| Compare with the official format ([Formats.md](Formats.md)) | ✅ | ✅ |
| See where the document came from ([Authenticity.md](Authenticity.md)) | ✅ | ✅ |
| Plain-language version of any passage ([Plain_Language.md](Plain_Language.md)) | ✅ | ✅ |
| Download the original PDF / Summary PDF | ✅ | ✅ |
| Auto-repair into a corrected PDF | ❌ read-only | ✅ on your own document |
| Change the document type | ❌ read-only | ✅ on your own document |
| Upload a document | ❌ | ✅ |
| Delete, activity log, delete-all | ❌ | ✅ |

## The three seeded documents

| Document | Why it is there |
|---|---|
| `consumer_protection_act_2019.pdf` (42 pages, real, from India Code) | The main benchmark document. "How many days do I have to appeal against the District Commission's order?" → Section 41, **page 25**, highlighted. "What is the penalty for drunk driving?" → **not found**, instead of a confident wrong answer. |
| `employment_agreement.pdf` (10 pages) | The everyday case: notice period, probation, salary, leaving early. |
| `rental_agreement_with_mistakes.pdf` (4 pages) | Deliberate mistakes, so **Check document** has something to find: `the the`, `tenent`, `ninety (60)`, an unfilled blank. It is also the best **Format** example: 6 of 11 required parts, with no stamp duty details, signatures or witnesses. |

## How the access rule works

Demo documents are ordinary rows in the `documents` table with `is_demo = true`, owned by a demo
user whose `firebase_uid` is `NULL` — so nobody can ever sign in as it.

`require_document_access` (`backend/app/core/auth.py`) is the single gate every document route
passes through. For a document flagged `is_demo` it allows GET/HEAD and `POST …/ask`, and refuses
everything else with **403 `demo_read_only`** — for signed-in users too, because the documents are
shared. For every other document nothing changed: no credentials means **401**, and someone else's
document is **404**.

Three properties this has to keep, each covered by a test in `backend/tests/test_demo.py`:

- **A missing token gives anonymous access; a bad token does not.** `get_optional_user` returns
  `None` only when no `Authorization` header was sent at all. A token that was sent but is expired
  or forged still raises, so the demo can never mask a broken sign-in.
- **The demo opens no door to anyone else's upload.** A non-demo document is 401/404 for an
  anonymous visitor exactly as before, and private documents are not listed on `/demo`.
- **Demo documents cannot be changed by anyone**, so one visitor can never alter what the next
  one sees.

`DEMO_MODE_ENABLED=false` closes it completely: the documents become unreachable without sign-in
and `/demo` reports `enabled: false`.

Retention (`RETENTION_DAYS`) skips demo documents — they are part of the deployment, not somebody's
upload.

## Setting it up on a deployment

After `alembic upgrade head`, on the machine running the API:

```
uv run python -m scripts.seed_demo            # add what is missing and process it
uv run python -m scripts.seed_demo --list     # show what is seeded
uv run python -m scripts.seed_demo --replace  # start over
```

It is safe to run again: a document already loaded is left alone, and one whose **file has gone**
— a host without a persistent disk restarted, so the database row survived but the PDF did not —
is replaced rather than left broken. Loading processes the 42-page Act, which takes a minute or two
the first time while the local models load.

**On a host with no shell** (a Hugging Face Space), set `DEMO_AUTO_SEED=true` instead. The API then
does the same work in a background thread at start-up: the port opens immediately, the demo
documents appear a minute or so later, and a failure is logged without affecting the API. Because
loading is idempotent and repairs missing files, this also fixes the demo automatically after every
restart.

The files come from the repository (`dataset/indiacode/`, `samples/`), so nothing is downloaded at
seed time. If they are missing, the script says which ones and stops:

```
uv run python -m scripts.fetch_indiacode      # the Acts
uv run python -m scripts.make_sample_pdf      # the samples
```

The source PDFs ship with the deployment: the Dockerfile copies the three demo files (about 650 KB,
not the whole 10 MB evaluation corpus) into the image, and `.github/workflows/deploy-api.yml` puts
them in the Space build context. See [Deployment.md](Deployment.md).

| Setting | Default | What it does |
|---|---|---|
| `DEMO_MODE_ENABLED` | `true` | Whether demo documents may be read without signing in at all |
| `DEMO_AUTO_SEED` | `false` | Load them in a background thread at start-up |
