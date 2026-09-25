# Deployment

Three ways to run ClauseLens, from quickest to production.

## 1. Local development (no Docker)

See the README's *Running locally*. The database runs from `backend/scripts/dev_db.py`
(bundled PostgreSQL + pgvector); API and website run with `uvicorn` and `npm run dev`.

## 2. Full stack with Docker Compose

```bash
cp .env.production.example .env.production      # fill in every value
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

| Service | Image | Notes |
|---|---|---|
| `db` | `pgvector/pgvector:pg17` | not published outside the stack; generated password |
| `api` | `backend/Dockerfile` | runs `alembic upgrade head`, then 2 uvicorn workers; models (embeddings, re-ranker, OCR) baked into the image; runs as a non-root user; health check on `/health` |
| `web` | `frontend/Dockerfile` | Next.js standalone server; `NEXT_PUBLIC_*` values are build arguments |

Required values (the stack refuses to start without them): `POSTGRES_PASSWORD`,
`FILE_ENCRYPTION_KEY`, `FIREBASE_PROJECT_ID` and the Firebase web-app values, `PUBLIC_WEB_URL`,
`PUBLIC_API_URL`. With `ENVIRONMENT=production` the API additionally refuses to start without
sign-in, the encryption key, a specific CORS origin and rate limits.

> These Dockerfiles have not been run on the development laptop (Docker is not installed
> there). The Next.js standalone server they use was built and smoke-tested locally
> (`node .next/standalone/server.js` served the pages and the PDF worker), and the API's
> start-up sequence is the one used in development. Run the stack once and check `/health`
> before relying on it.

## 3. Cloud

Any container platform works (Google Cloud Run, Render, Railway, Fly.io, a VM):

1. **Database:** a managed PostgreSQL with the `vector` extension (Cloud SQL, Neon, Supabase,
   RDS). Set `DATABASE_URL`.
2. **API container:** from `backend/Dockerfile` (build context = repository root). Give it
   ≥ 1.5 GB RAM (models). Mount persistent storage for `/data/uploads`, or move uploads to
   object storage behind `services/storage.py`. Set the variables above plus
   `ENVIRONMENT=production`, `TRUST_PROXY_HEADERS=true`.
3. **Website:** from `frontend/Dockerfile`, or deploy the `frontend` folder to Vercel with the
   same `NEXT_PUBLIC_*` variables.
4. **Firebase:** add the website's domain under Authentication → Settings → Authorized domains.
5. **HTTPS:** the platform's load balancer terminates TLS; HSTS is sent in production.

## Backups

- Database: the platform's automated backups (point-in-time recovery if available).
- Uploads: back up the volume/bucket — files are encrypted, so backups are safe to store.
- **`FILE_ENCRYPTION_KEY`:** store it in a secret manager and keep an offline copy. Without it
  the uploaded files cannot be decrypted.

## Scaling

The API is stateless apart from per-process rate-limit counters and caches: run more replicas
behind the load balancer (and move rate-limit counters to Redis). Measured single-process
throughput and latency are in [Evaluation.md](Evaluation.md#performance).
