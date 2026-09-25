"""Evaluation report against a running ClauseLens server.

Uploads the sample documents, asks every evaluation question, and prints whether each
answer points to the right page. Usage (from backend/, with the API running):

    uv run python -m scripts.evaluate [--api http://localhost:8000]
"""

import argparse
import sys
import time
from pathlib import Path

import httpx

from tests.evaluation_cases import CASES, SAMPLE_FILES, SampleName, check

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"
PROCESSING_TIMEOUT_SECONDS = 120
POLL_SECONDS = 1.0


def upload(client: httpx.Client, filename: str) -> str:
    content = (SAMPLES_DIR / filename).read_bytes()
    response = client.post("/documents", files={"file": (filename, content, "application/pdf")})
    response.raise_for_status()
    document_id: str = response.json()["id"]
    deadline = time.monotonic() + PROCESSING_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        status = client.get(f"/documents/{document_id}").json()
        if status["status"] == "ready":
            return document_id
        if status["status"] == "failed":
            raise RuntimeError(f"{filename} failed: {status['error_message']}")
        time.sleep(POLL_SECONDS)
    raise TimeoutError(f"{filename} was not processed within {PROCESSING_TIMEOUT_SECONDS}s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000")
    args = parser.parse_args()

    with httpx.Client(base_url=args.api, timeout=120) as client:
        ids: dict[SampleName, str] = {
            sample: upload(client, filename) for sample, filename in SAMPLE_FILES.items()
        }
        passed = 0
        for case in CASES:
            if case.action == "ask":
                response = client.post(
                    f"/documents/{ids[case.sample]}/ask", json={"question": case.query}
                )
            else:
                response = client.get(
                    f"/documents/{ids[case.sample]}/search",
                    params={"q": case.query, "mode": case.action},
                )
            problems = check(case, response.json()) if response.is_success else [response.text]
            passed += not problems
            mark = "PASS" if not problems else "FAIL"
            print(f"{mark}  [{case.sample}] {case.action:8} {case.query}")
            for problem in problems:
                print(f"        - {problem}")
        print(f"\n{passed}/{len(CASES)} checks passed")
        for document_id in ids.values():  # keep the server tidy
            client.delete(f"/documents/{document_id}")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
