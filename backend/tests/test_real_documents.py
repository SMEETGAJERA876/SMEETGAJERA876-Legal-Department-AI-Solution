"""Quality on real Indian statutes from India Code: document type, retrieval, grounded answers,
and refusing to answer what the document doesn't say. Metrics are reported per split
(dev = used while tuning, test = held out); see tests/real_document_cases.py.

Run with -s to see the numbers:  uv run pytest tests/test_real_documents.py -s
"""

import re
import statistics
import time
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from tests.real_document_cases import ACTS, DATASET, QUESTIONS, UNANSWERABLE, Question, Split

K = 5


def section_of(clause_ref: object) -> str | None:
    """'34(1)(a)' → '34'; 'Section 12' → '12'; None for contents/footnotes."""
    if not isinstance(clause_ref, str):
        return None
    match = re.match(r"(?:[A-Za-z]+\s+)?(\d+[A-Z]*)", clause_ref)
    return match.group(1) if match else None


@dataclass
class SplitMetrics:
    questions: int = 0
    ranks: list[int | None] = field(default_factory=list)
    page_at_1: int = 0
    answered_correctly: int = 0
    answered_wrong_source: int = 0
    unanswerable: int = 0
    refused_unanswerable: int = 0
    misses: list[str] = field(default_factory=list)

    @property
    def recall_at_1(self) -> float:
        return sum(r == 1 for r in self.ranks) / len(self.ranks)

    @property
    def recall_at_3(self) -> float:
        return sum(r is not None and r <= 3 for r in self.ranks) / len(self.ranks)

    @property
    def mrr(self) -> float:
        return sum(1 / r for r in self.ranks if r) / len(self.ranks)

    @property
    def answer_accuracy(self) -> float:
        return self.answered_correctly / self.questions

    @property
    def refusal_rate(self) -> float:
        return self.refused_unanswerable / self.unanswerable

    def summary(self) -> str:
        return (
            f"R@1 {self.recall_at_1:.2f}  R@3 {self.recall_at_3:.2f}  MRR {self.mrr:.3f}  "
            f"page@1 {self.page_at_1 / self.questions:.2f}  "
            f"answer correct {self.answer_accuracy:.2f} "
            f"(wrong source {self.answered_wrong_source})  "
            f"unanswerable refused {self.refused_unanswerable}/{self.unanswerable}"
        )


@pytest.fixture(scope="module")
def acts(database: None, client: TestClient) -> Iterator[dict[str, dict[str, object]]]:
    if not all((DATASET / f"{name}.pdf").exists() for name in ACTS):
        pytest.skip("India Code dataset missing. Run: uv run python -m scripts.fetch_indiacode")
    uploaded: dict[str, dict[str, object]] = {}
    for name in ACTS:
        pdf = (DATASET / f"{name}.pdf").read_bytes()
        response = client.post(
            "/documents", files={"file": (f"{name}.pdf", pdf, "application/pdf")}
        )
        assert response.status_code == 201, response.text
        document = client.get(f"/documents/{response.json()['id']}").json()
        assert document["status"] == "ready", document
        uploaded[name] = document
    yield uploaded
    for document in uploaded.values():
        client.delete(f"/documents/{document['id']}")


@pytest.fixture(scope="module")
def metrics(client: TestClient, acts: dict[str, dict[str, object]]) -> dict[Split, SplitMetrics]:
    results: dict[Split, SplitMetrics] = {"dev": SplitMetrics(), "test": SplitMetrics()}
    search_ms: list[float] = []
    ask_ms: list[float] = []
    for q in QUESTIONS:
        m = results[q.split]
        m.questions += 1
        document_id = acts[q.act]["id"]
        started = time.perf_counter()
        response = client.get(
            f"/documents/{document_id}/search", params={"q": q.question, "mode": "hybrid"}
        )
        search_ms.append((time.perf_counter() - started) * 1000)
        assert response.status_code == 200, response.text
        hits = response.json()["results"][:K]
        rank = next(
            (i for i, hit in enumerate(hits, 1) if section_of(hit["clause_ref"]) == q.section), None
        )
        m.ranks.append(rank)
        if hits and hits[0]["page_number"] in (q.page, q.page + 1):
            m.page_at_1 += 1
        if rank != 1:
            m.misses.append(f"search {q.act[:12]} s{q.section} rank={rank}: {q.question}")

        started = time.perf_counter()
        answer = client.post(f"/documents/{document_id}/ask", json={"question": q.question}).json()
        ask_ms.append((time.perf_counter() - started) * 1000)
        cited = {section_of(c["clause_ref"]) for c in answer["citations"]}
        if answer["found"] and q.section in cited:
            m.answered_correctly += 1
        else:
            if answer["found"]:
                m.answered_wrong_source += 1
            m.misses.append(_answer_miss(q, answer["found"], cited))

    for u in UNANSWERABLE:
        m = results[u.split]
        m.unanswerable += 1
        answer = client.post(f"/documents/{acts[u.act]['id']}/ask", json={"question": u.question})
        if not answer.json()["found"]:
            m.refused_unanswerable += 1
        else:
            m.misses.append(f"answered unanswerable {u.act[:12]}: {u.question}")

    for split, m in results.items():
        print(f"\n[{split}] {m.summary()}")
        for miss in m.misses:
            print("   ", miss)
    print(
        f"\nlatency  search p50 {statistics.median(search_ms):.0f} ms  "
        f"p95 {sorted(search_ms)[int(0.95 * len(search_ms)) - 1]:.0f} ms   "
        f"ask p50 {statistics.median(ask_ms):.0f} ms  "
        f"p95 {sorted(ask_ms)[int(0.95 * len(ask_ms)) - 1]:.0f} ms"
    )
    return results


def _answer_miss(q: Question, found: bool, cited: set[str | None]) -> str:
    sections = sorted(map(str, cited))
    return f"answer {q.act[:12]} s{q.section} found={found} cited={sections}: {q.question}"


def test_every_act_is_recognised_as_an_act(acts: dict[str, dict[str, object]]) -> None:
    for name, document in acts.items():
        classification = document["classification"]
        assert isinstance(classification, dict)
        assert document["document_type_id"] == "policy.act", (name, classification)
        assert classification["confidence_level"] == "high", (name, classification)


def test_retrieval_on_real_acts(metrics: dict[Split, SplitMetrics]) -> None:
    for split in ("dev", "test"):
        m = metrics[split]
        assert m.recall_at_3 >= 0.85, (split, m.summary())
        assert m.mrr >= 0.75, (split, m.summary())


def test_answers_cite_the_right_section(metrics: dict[Split, SplitMetrics]) -> None:
    for split in ("dev", "test"):
        assert metrics[split].answer_accuracy >= 0.8, (split, metrics[split].summary())


def test_does_not_answer_what_the_act_does_not_say(metrics: dict[Split, SplitMetrics]) -> None:
    for split in ("dev", "test"):
        assert metrics[split].refusal_rate == 1.0, (split, metrics[split].summary())
