---
title: ClauseLens AI API
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
short_description: API for ClauseLens AI — legal document understanding with sources
---

# ClauseLens AI — API

The backend of [ClauseLens AI](https://github.com/SMEETGAJERA876/SMEETGAJERA876-Legal-Department-AI-Solution):
upload a legal or government PDF, ask questions in plain language, get answers with the page
and section. This Space is published automatically from the GitHub repository
(`.github/workflows/deploy-api.yml`); do not edit it here.

Health check: `/health` · API documentation: `/docs`

Required Space **secrets** (Settings → Variables and secrets):

| Name | Value |
|---|---|
| `DATABASE_URL` | Neon/Supabase PostgreSQL URL, as `postgresql+psycopg://…?sslmode=require` |
| `FIREBASE_PROJECT_ID` | `legal-department-f5b74` |
| `FILE_ENCRYPTION_KEY` | output of `uv run python -m scripts.new_encryption_key` |
| `CORS_ORIGINS` | `["https://smeetgajera-876-legal-department-ai.vercel.app"]` |
| `ENVIRONMENT` | `production` |
| `TRUST_PROXY_HEADERS` | `true` |
| `DEMO_AUTO_SEED` | `true` (loads the public demo documents — see below) |

Free Spaces have no persistent disk: uploaded files are lost when the Space restarts, while
everything extracted from them stays in the database. Add persistent storage (Settings →
Persistent storage, mounted at `/data`) to keep files.

## The public demo

`/demo` lists the documents anyone may open without signing in. Add the Space **variable**
`DEMO_AUTO_SEED` = `true` and the API loads them in the background a minute after each start —
which also repairs them after a restart, since a free Space loses its uploads directory but keeps
the database. `DEMO_MODE_ENABLED` = `false` turns the demo off.
