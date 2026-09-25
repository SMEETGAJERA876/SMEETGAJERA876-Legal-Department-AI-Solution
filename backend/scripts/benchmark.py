"""Measure processing speed and question latency on the real India Code Acts.

Runs the API in-process against a separate database (BENCHMARK_DATABASE_URL, default
clauselens_eval — create it once with scripts/dev_db.py or `createdb`). Needs the dataset:
`uv run python -m scripts.fetch_indiacode`.

    uv run python -m scripts.benchmark [--users 10] [--questions 5]
"""

import argparse
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

os.environ["DATABASE_URL"] = os.environ.get(
    "BENCHMARK_DATABASE_URL",
    "postgresql+psycopg://clauselens:clauselens@localhost:5433/clauselens_eval",
)
os.environ["AUTH_MODE"] = "disabled"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ.setdefault("AI_PROVIDER", "none")

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402, F401
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from tests.real_document_cases import ACTS, DATASET, QUESTIONS  # noqa: E402


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(p * len(ordered)))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--questions", type=int, default=5)
    args = parser.parse_args()

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    client = TestClient(app)

    print("Processing (upload → ready), one document at a time:")
    ids: dict[str, str] = {}
    total_pages, total_seconds = 0, 0.0
    for name in ACTS:
        pdf = (DATASET / f"{name}.pdf").read_bytes()
        started = time.perf_counter()
        response = client.post(
            "/documents", files={"file": (f"{name}.pdf", pdf, "application/pdf")}
        )
        document = client.get(f"/documents/{response.json()['id']}").json()
        seconds = time.perf_counter() - started
        assert document["status"] == "ready", document
        ids[name] = document["id"]
        total_pages += document["page_count"]
        total_seconds += seconds
        print(f"  {name[:48]:48} {document['page_count']:3} pages  {seconds:5.1f} s")
    print(f"  → {total_pages / total_seconds:.1f} pages/s ({total_pages} pages)")

    def ask(question: str, act: str) -> float:
        started = time.perf_counter()
        response = client.post(f"/documents/{ids[act]}/ask", json={"question": question})
        assert response.status_code == 200, response.text
        return (time.perf_counter() - started) * 1000

    ask(QUESTIONS[0].question, QUESTIONS[0].act)  # warm the models
    sequential = [ask(q.question, q.act) for q in QUESTIONS]
    print(
        f"\nQuestion latency, one user ({len(sequential)} questions): "
        f"p50 {statistics.median(sequential):.0f} ms, p95 {percentile(sequential, 0.95):.0f} ms"
    )

    jobs = [QUESTIONS[i % len(QUESTIONS)] for i in range(args.users * args.questions)]
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.users) as pool:
        concurrent = list(pool.map(lambda q: ask(q.question, q.act), jobs))
    elapsed = time.perf_counter() - started
    print(
        f"{args.users} users at once ({len(jobs)} questions): "
        f"p50 {statistics.median(concurrent):.0f} ms, p95 {percentile(concurrent, 0.95):.0f} ms, "
        f"throughput {len(jobs) / elapsed:.1f} questions/s"
    )


if __name__ == "__main__":
    main()
