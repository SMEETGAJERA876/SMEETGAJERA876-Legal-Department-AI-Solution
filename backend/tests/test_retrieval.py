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


# --- the diversity pass itself -------------------------------------------------------------
# A regression guard, not a quality measure: the one-passage-per-section reordering used to
# push a section's second passage behind every other section's first, however relevant it was.
# On the employment agreement that dropped the clause holding "ninety (90) days written notice"
# from rank 5 to rank 11, and the answer came from the probation clause instead.


class _FakeChunk:
    def __init__(self, chunk_id: str, clause_ref: str) -> None:
        self.id = chunk_id
        self.clause_ref = clause_ref


def _ranked(*refs: str) -> list[tuple[float, int, object]]:
    """Passages in relevance order, named by their clause reference."""
    return [(0.0, 0, _FakeChunk(ref, ref)) for ref in refs]


def _order(items: list[tuple[float, int, object]]) -> list[str]:
    return [item[2].id for item in items]


def test_diversity_puts_one_passage_of_each_section_first() -> None:
    from app.services.search import _one_per_section_first

    ranked = _ranked("12.1", "12.2", "13.1", "14.1", "15.1", "16.1")
    assert _order(_one_per_section_first(ranked, 6))[:5] == ["12.1", "13.1", "14.1", "15.1", "16.1"]


def test_diversity_never_evicts_a_passage_relevance_would_have_returned() -> None:
    from app.services.search import _one_per_section_first

    # "12.2" is 2nd by relevance but a sibling of the top hit; with a window of 4 it must stay.
    ranked = _ranked("12.1", "12.2", "13.1", "14.1", "15.1", "16.1", "17.1")
    window = _order(_one_per_section_first(ranked, 4))[:4]
    assert set(window) == {"12.1", "12.2", "13.1", "14.1"}
    # Diversity still decides the order inside that window: other sections come before the
    # sibling, so the reader sees a spread before a second helping of section 12.
    assert window.index("12.2") > window.index("13.1")


def test_diversity_is_unchanged_when_nothing_would_be_evicted() -> None:
    from app.services.search import _one_per_section_first

    ranked = _ranked("1.1", "2.1", "3.1", "4.1")
    assert _order(_one_per_section_first(ranked, 4)) == ["1.1", "2.1", "3.1", "4.1"]
