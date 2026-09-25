"""Phase 1–2 checks: taxonomy, schemas, examples and dataset metadata stay consistent
with each other and with the running extraction engine."""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from app.services.concepts import CONCEPTS as ENGINE_CONCEPTS

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
SCHEMAS = {p.stem.removesuffix(".schema"): p for p in (DATA / "schemas").glob("*.schema.json")}
EXAMPLES = sorted((DATA / "examples").glob("*.json"))


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registry() -> Registry:
    resources = [(load(p)["$id"], Resource.from_contents(load(p))) for p in SCHEMAS.values()]
    return Registry().with_resources(resources)


def validator(name: str, registry: Registry) -> Draft202012Validator:
    return Draft202012Validator(
        load(SCHEMAS[name]), registry=registry, format_checker=FormatChecker()
    )


def errors(name: str, instance: Any, registry: Registry) -> list[str]:
    return [
        f"{'/'.join(map(str, e.absolute_path))}: {e.message}"
        for e in validator(name, registry).iter_errors(instance)
    ]


@pytest.fixture(scope="module")
def types() -> dict[str, Any]:
    data: dict[str, Any] = load(DATA / "taxonomy" / "document_types.json")
    return data


@pytest.fixture(scope="module")
def concepts() -> dict[str, Any]:
    data: dict[str, Any] = load(DATA / "taxonomy" / "legal_concepts.json")
    return data


def test_expected_files_exist() -> None:
    assert set(SCHEMAS) == {
        "normalized_document", "document_metadata", "legal_fact", "legal_concept",
    }  # fmt: skip
    assert {p.name for p in EXAMPLES} == {
        "employment_agreement.json", "government_notice.json", "court_judgment.json",
        "company_policy.json",
    }  # fmt: skip
    for doc in [
        "Document_Taxonomy", "Training_Dataset_Schema", "Legal_Concepts", "Document_Classification",
        "Document_Normalization", "AI_Pipeline", "Data_Governance",
    ]:  # fmt: skip
        assert (ROOT / "docs" / f"{doc}.md").exists(), doc


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_schemas_are_valid(name: str) -> None:
    Draft202012Validator.check_schema(load(SCHEMAS[name]))


def test_document_types_are_consistent(types: dict[str, Any]) -> None:
    categories = {c["id"] for c in types["categories"]}
    assert len(categories) == 11
    ids = [t["id"] for t in types["document_types"]]
    assert len(ids) == len(set(ids)), "duplicate document type ids"
    for entry in types["document_types"]:
        assert entry["id"].split(".")[0] == entry["category"], entry["id"]
        assert entry["category"] in categories
        assert set(entry["secondary_categories"]) <= categories - {entry["category"]}, entry["id"]
    assert categories == {t["category"] for t in types["document_types"]}, "empty category"
    assert "other.unknown" in ids


def test_concepts_match_schema_and_aliases(concepts: dict[str, Any], registry: Registry) -> None:
    ids = [c["id"] for c in concepts["concepts"]]
    assert len(ids) == len(set(ids)), "duplicate concept ids"
    for concept in concepts["concepts"]:
        assert errors("legal_concept", concept, registry) == [], concept["id"]
    aliases = load(DATA / "taxonomy" / "concept_aliases.json")["aliases"]
    assert set(aliases) == set(ids)


def test_every_engine_concept_maps_to_exactly_one_taxonomy_concept(
    concepts: dict[str, Any],
) -> None:
    engine_keys = [c["engine_key"] for c in concepts["concepts"] if "engine_key" in c]
    assert len(engine_keys) == len(set(engine_keys))
    assert set(engine_keys) == set(ENGINE_CONCEPTS)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_examples_are_valid_normalized_documents(
    path: Path, registry: Registry, types: dict[str, Any], concepts: dict[str, Any]
) -> None:
    example = load(path)
    assert errors("normalized_document", example, registry) == []

    type_ids = {t["id"] for t in types["document_types"]}
    concept_ids = {c["id"] for c in concepts["concepts"]}
    assert example["document"]["classification"]["document_type"] in type_ids

    pages = {p["page_number"]: p["text"] for p in example["pages"]}
    fact_ids = {f["id"] for f in example["facts"]}
    for fact in example["facts"]:
        assert fact["concept"] in concept_ids, fact["concept"]
        evidence = fact["evidence"]
        text = pages[evidence["page_number"]]
        # the evidence must be the exact text at the stated position — nothing invented
        assert text[evidence["char_start"] : evidence["char_end"]] == evidence["source_text"]
    for section in example["sections"]:
        for clause in section["clauses"]:
            assert section["page_start"] <= clause["page_number"] <= section.get("page_end", 10**6)
            assert (
                pages[clause["page_number"]][clause["char_start"] : clause["char_end"]]
                == clause["text"]
            )
            assert set(clause["concepts"]) <= concept_ids
            assert set(clause["fact_ids"]) <= fact_ids


def test_dataset_metadata(registry: Registry, types: dict[str, Any]) -> None:
    index = load(ROOT / "dataset" / "metadata" / "evaluation_index.json")
    type_ids = {t["id"] for t in types["document_types"]}
    hashes: dict[str, str] = {}
    for entry in index["documents"]:
        assert errors("document_metadata", entry, registry) == [], entry["document_id"]
        assert entry["document_type"] in type_ids
        assert (ROOT / entry["file_path"]).exists()
        # the same file must never appear in two splits
        assert hashes.setdefault(entry["sha256"], entry["split"]) == entry["split"]


def test_markdown_docs_list_every_type_and_concept(
    types: dict[str, Any], concepts: dict[str, Any]
) -> None:
    taxonomy_doc = (ROOT / "docs" / "Document_Taxonomy.md").read_text(encoding="utf-8")
    concepts_doc = (ROOT / "docs" / "Legal_Concepts.md").read_text(encoding="utf-8")
    missing_types = [t["id"] for t in types["document_types"] if f"`{t['id']}`" not in taxonomy_doc]
    missing_concepts = [c["id"] for c in concepts["concepts"] if f"`{c['id']}`" not in concepts_doc]
    assert missing_types == [] and missing_concepts == []
