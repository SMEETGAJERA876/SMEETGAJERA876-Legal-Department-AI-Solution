"""Read-only access to data/taxonomy (the source of truth for document types and concepts)."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _taxonomy_dir() -> Path:
    configured = get_settings().taxonomy_dir
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "data" / "taxonomy"


@lru_cache
def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((_taxonomy_dir() / name).read_text(encoding="utf-8"))
    return data


def load(name: str) -> dict[str, Any]:
    """A taxonomy data file by name, e.g. "plain_language.json" (cached)."""
    return _load(name)


def taxonomy_version() -> str:
    return str(_load("document_types.json")["version"])


@lru_cache
def document_type_ids() -> frozenset[str]:
    return frozenset(t["id"] for t in _load("document_types.json")["document_types"])


@lru_cache
def concept_id_for_engine_key() -> dict[str, str]:
    """Engine key (e.g. "notice_period") → taxonomy concept id ("contract.notice_period")."""
    return {
        c["engine_key"]: c["id"]
        for c in _load("legal_concepts.json")["concepts"]
        if "engine_key" in c
    }


@lru_cache
def document_types() -> tuple[dict[str, Any], ...]:
    return tuple(_load("document_types.json")["document_types"])


@lru_cache
def category_names() -> dict[str, str]:
    return {c["id"]: c["name"] for c in _load("document_types.json")["categories"]}


@lru_cache
def document_type(type_id: str) -> dict[str, Any] | None:
    return next((t for t in document_types() if t["id"] == type_id), None)
