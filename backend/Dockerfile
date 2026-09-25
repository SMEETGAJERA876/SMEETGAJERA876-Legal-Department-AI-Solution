# ClauseLens API (FastAPI). The AI models run inside this container (CPU); they are
# downloaded at build time so a new container starts serving immediately.

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    EMBEDDING_CACHE_DIR=/app/models UPLOAD_DIR=/data/uploads TAXONOMY_DIR=/app/data/taxonomy
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend ./
COPY data /app/data
RUN uv sync --frozen --no-dev

# Download the embedding, re-ranking and OCR models into the image.
RUN uv run python -c "from app.services import embeddings, reranker; from app.services.parsing import ocr; embeddings.embed_query('warm up'); reranker.scores('warm up', ['warm up']); ocr._get_engine()"

RUN useradd --system --uid 1001 api && mkdir -p /data/uploads && chown -R api /data /app/models
USER api
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
# Apply database migrations, then serve. Two workers share the load (each loads the models).
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_WORKERS:-2} --proxy-headers"]
