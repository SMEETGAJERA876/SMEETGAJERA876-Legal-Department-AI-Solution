"""Runs every evaluation case against freshly processed sample documents."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.evaluation_cases import CASES, SAMPLE_FILES, Case, SampleName, check

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"


@pytest.fixture(scope="session")
def sample_documents(database: None, client: TestClient) -> dict[SampleName, str]:
    from scripts.make_sample_pdf import build_all_samples

    if not all((SAMPLES_DIR / name).exists() for name in SAMPLE_FILES.values()):
        build_all_samples()
    ids: dict[SampleName, str] = {}
    for sample, filename in SAMPLE_FILES.items():
        content = (SAMPLES_DIR / filename).read_bytes()
        response = client.post("/documents", files={"file": (filename, content, "application/pdf")})
        assert response.status_code == 201, response.text
        ids[sample] = response.json()["id"]
        assert client.get(f"/documents/{ids[sample]}").json()["status"] == "ready"
    return ids


def run_case(client: TestClient, document_id: str, case: Case) -> dict[str, object]:
    if case.action == "ask":
        response = client.post(f"/documents/{document_id}/ask", json={"question": case.query})
    else:
        response = client.get(
            f"/documents/{document_id}/search", params={"q": case.query, "mode": case.action}
        )
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c.sample}:{c.action}:{c.query}")
def test_evaluation_case(
    client: TestClient, sample_documents: dict[SampleName, str], case: Case
) -> None:
    body = run_case(client, sample_documents[case.sample], case)
    assert check(case, body) == []
