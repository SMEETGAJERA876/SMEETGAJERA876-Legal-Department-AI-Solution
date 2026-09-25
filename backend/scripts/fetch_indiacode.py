"""Download real central Acts from India Code (https://indiacode.gov.in) for evaluation.

India Code runs DSpace; its public REST API is used read-only, one request at a time, with a
pause between requests. Each Act is saved as dataset/indiacode/<slug>.pdf together with
<slug>.json (title, Act number, year, ministry, source URL, retrieval date).

These are public statutes (the Copyright Act, 1957, s. 52(1)(q) permits reproducing Acts).
They are used only to evaluate ClauseLens — never to train a model.

    uv run python -m scripts.fetch_indiacode
"""

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

API = "https://indiacode.gov.in/server/api"
OUT_DIR = Path(__file__).resolve().parents[2] / "dataset" / "indiacode"
PAUSE_SECONDS = 1.0
RETRIES = 4
MAX_PDF_BYTES = 8 * 1024 * 1024

# Everyday Acts that citizens, employees, tenants and consumers actually run into.
ACTS = [
    "The Consumer Protection Act, 2019",
    "The Right to Information Act, 2005",
    "The Payment of Gratuity Act, 1972",
    "The Maternity Benefit Act, 1961",
    "The Real Estate (Regulation and Development) Act, 2016",
    "The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
    "The Protection of Women from Domestic Violence Act, 2005",
    "The Payment of Bonus Act, 1965",
    "The Rights of Persons with Disabilities Act, 2016",
    "The Legal Services Authorities Act, 1987",
    "The Indian Contract Act, 1872",
    "The Code on Wages, 2019",
]


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower().removeprefix("the ")).strip("_")[:60]


def get_json(client: httpx.Client, url: str, **params: str) -> Any:
    for attempt in range(RETRIES):
        try:
            response = client.get(url, params=params or None)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            if attempt == RETRIES - 1:
                raise
            time.sleep(2 * (attempt + 1))
        finally:
            time.sleep(PAUSE_SECONDS)
    raise AssertionError("unreachable")


def first(metadata: dict[str, Any], key: str) -> str | None:
    values = metadata.get(key) or []
    return values[0]["value"] if values else None


def comparable(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower().removeprefix("the ")).strip()


def find_central_act(client: httpx.Client, title: str) -> dict[str, Any] | None:
    data = get_json(
        client,
        f"{API}/discover/search/objects",
        query=comparable(title),
        dsoType="ITEM",
        size="40",
    )
    for result in data["_embedded"]["searchResult"]["_embedded"]["objects"]:
        item = result["_embedded"]["indexableObject"]
        metadata = item["metadata"]
        if (
            comparable(item["name"]) == comparable(title)
            and first(metadata, "dc.identifier.state_name") == "CENTRAL"
            and first(metadata, "dc.identifier.collection") == "ACT"
        ):
            return item  # type: ignore[no-any-return]
    return None


def english_pdf(client: httpx.Client, item_uuid: str) -> dict[str, Any] | None:
    bundles = get_json(client, f"{API}/core/items/{item_uuid}/bundles")["_embedded"]["bundles"]
    original = next((b for b in bundles if b["name"] == "ORIGINAL"), None)
    if original is None:
        return None
    streams = get_json(client, original["_links"]["bitstreams"]["href"])["_embedded"]["bitstreams"]
    pdfs = [s for s in streams if s["name"].lower().endswith(".pdf")]
    # Prefer the English text; India Code usually also has a Hindi PDF.
    english = [
        s for s in pdfs if "hindi" not in s["name"].lower() and not s["name"].startswith("H")
    ]
    candidates = english or pdfs
    return min(candidates, key=lambda s: s["sizeBytes"]) if candidates else None


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=90, headers={"Accept": "application/json"}) as client:
        for title in ACTS:
            name = slug(title)
            if (OUT_DIR / f"{name}.pdf").exists():
                print(f"= {title} (already downloaded)")
                continue
            item = find_central_act(client, title)
            if item is None:
                print(f"! {title}: central Act not found")
                continue
            stream = english_pdf(client, item["uuid"])
            if stream is None or stream["sizeBytes"] > MAX_PDF_BYTES:
                print(f"! {title}: no suitable PDF")
                continue
            pdf = client.get(stream["_links"]["content"]["href"], headers={"Accept": "*/*"})
            pdf.raise_for_status()
            if not pdf.content.startswith(b"%PDF"):
                print(f"! {title}: download was not a PDF")
                continue
            (OUT_DIR / f"{name}.pdf").write_bytes(pdf.content)
            metadata = item["metadata"]
            (OUT_DIR / f"{name}.json").write_text(
                json.dumps(
                    {
                        "title": item["name"],
                        "act_number": first(metadata, "dc.identifier.act_number"),
                        "year": first(metadata, "dc.date.act_year"),
                        "enactment_date": first(metadata, "dc.date.enact_date"),
                        "ministry": first(metadata, "dc.identifier.ministry_name"),
                        "source": f"https://indiacode.gov.in/handle/{item['handle']}",
                        "file_name": stream["name"],
                        "retrieved": datetime.now(UTC).date().isoformat(),
                        "use": "evaluation only; public statute",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"+ {title}: {len(pdf.content) // 1024} KB")
            time.sleep(PAUSE_SECONDS)


if __name__ == "__main__":
    main()
