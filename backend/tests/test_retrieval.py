"""Phase 7: retrieval quality — Recall@K, MRR and page accuracy, semantic vs hybrid."""

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from tests.evaluation_cases import SampleName
from tests.retrieval_cases import CASES, RetrievalCase, is_relevant
from tests.test_evaluation import sample_documents  # noqa: F401  (fixture)

K = 8


@dataclass
class Metrics:
    recall_at_1: float
    recall_at_3: float
    mrr: float
    page_at_1: float
    misses: list[str]


def rank_of_first_relevant(results: list[dict[str, object]], case: RetrievalCase) -> int | None:
    for rank, result in enumerate(results[:K], start=1):
        page, clause = result["page_number"], result["clause_ref"]
        assert isinstance(page, int)
        if is_relevant(case, page, clause if isinstance(clause, str) else None):
            return rank
    return None


def evaluate(client: TestClient, ids: dict[SampleName, str], mode: str) -> Metrics:
    ranks: list[int | None] = []
    first_pages_right = 0
    misses = []
    for case in CASES:
        response = client.get(
            f"/documents/{ids[case.sample]}/search", params={"q": case.query, "mode": mode}
        )
        assert response.status_code == 200, response.text
        results = response.json()["results"]
        rank = rank_of_first_relevant(results, case)
        ranks.append(rank)
        if results and results[0]["page_number"] in case.pages:
            first_pages_right += 1
        if rank != 1:
            misses.append(f"{case.query!r}: rank {rank}")
    n = len(CASES)
    return Metrics(
        recall_at_1=sum(r == 1 for r in ranks) / n,
        recall_at_3=sum(r is not None and r <= 3 for r in ranks) / n,
        mrr=sum(1 / r for r in ranks if r) / n,
        page_at_1=first_pages_right / n,
        misses=misses,
    )


@pytest.fixture(scope="module")
def metrics(
    client: TestClient,
    sample_documents: dict[SampleName, str],  # noqa: F811
) -> dict[str, Metrics]:
    return {mode: evaluate(client, sample_documents, mode) for mode in ("semantic", "hybrid")}


def test_hybrid_meets_quality_bar(metrics: dict[str, Metrics]) -> None:
    hybrid = metrics["hybrid"]
    assert hybrid.recall_at_3 >= 0.95, hybrid
    assert hybrid.mrr >= 0.9, hybrid
    assert hybrid.page_at_1 >= 0.9, hybrid


def test_hybrid_is_at_least_as_good_as_semantic(metrics: dict[str, Metrics]) -> None:
    semantic, hybrid = metrics["semantic"], metrics["hybrid"]
    print(f"\nsemantic: {semantic}\nhybrid:   {hybrid}")
    assert hybrid.mrr >= semantic.mrr
    assert hybrid.recall_at_3 >= semantic.recall_at_3
