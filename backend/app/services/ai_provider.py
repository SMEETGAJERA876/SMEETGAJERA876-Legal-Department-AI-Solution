"""Chat provider abstraction for grounded answers.

Providers only ever see retrieved excerpts of the document. Their output is validated by
the Q&A service: citations must point at a real excerpt and quotes must appear in it.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.text_utils import format_clause

logger = logging.getLogger("clauselens.ai")


@dataclass(frozen=True)
class SourceExcerpt:
    source_id: int
    page_number: int
    clause_ref: str | None
    heading: str | None
    text: str


class ProviderCitation(BaseModel):
    source_id: int = Field(description="The number of the excerpt, e.g. 2 for [S2].")
    quote: str = Field(description="An exact, short quote copied word-for-word from that excerpt.")


class ProviderAnswer(BaseModel):
    found: bool = Field(description="False if the excerpts do not contain the answer.")
    answer: str = Field(description="A short, direct answer (one or two sentences).")
    simple_explanation: str = Field(description="What it means, in everyday language.")
    why_it_matters: str = Field(description="One or two sentences of practical context.")
    citations: list[ProviderCitation]


class ChatProvider(Protocol):
    name: str

    def answer(
        self, question: str, excerpts: list[SourceExcerpt], history: list[tuple[str, str]]
    ) -> ProviderAnswer | None:
        """Return a grounded answer, or None if this provider cannot generate one."""
        ...


class ExtractiveProvider:
    """No generative model: the Q&A service answers with quotes from the document."""

    name = "none"

    def answer(
        self, question: str, excerpts: list[SourceExcerpt], history: list[tuple[str, str]]
    ) -> ProviderAnswer | None:
        return None


SYSTEM_PROMPT = """You help people who are not lawyers understand a legal document they \
uploaded. You answer ONLY from the numbered document excerpts provided in each message.

Rules:
- Use only the excerpts. Never use outside legal knowledge to fill gaps, and never invent \
clauses, dates, amounts, notice periods, parties or obligations.
- If the excerpts do not answer the question, set found=false and explain briefly what the \
document does not say. Do not guess.
- Every factual statement must be supported by at least one citation. Each citation's quote \
must be copied exactly, word-for-word, from the excerpt it cites. Keep quotes short (one \
sentence or less).
- Write in plain, friendly language. Avoid legal jargon; if a legal term is unavoidable, \
explain it.
- Phrase answers as information, not advice: "According to the document...", "The document \
states...", "This clause appears to...". Do not predict legal outcomes, do not say whether \
anything is legal or illegal, and do not tell the user what legal action to take. Where it \
helps, suggest discussing it with a qualified legal professional."""


def _format_excerpts(excerpts: list[SourceExcerpt]) -> str:
    blocks = []
    for e in excerpts:
        location = f"Page {e.page_number}"
        if e.clause_ref:
            location += f", {format_clause(e.clause_ref)}"
        if e.heading:
            location += f" ({e.heading})"
        blocks.append(f"[S{e.source_id}] {location}\n{e.text}")
    return "\n\n".join(blocks)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, effort: Literal["low", "medium", "high"]) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key or None, max_retries=2, timeout=90)
        self._model = model
        self._effort = effort

    def answer(
        self, question: str, excerpts: list[SourceExcerpt], history: list[tuple[str, str]]
    ) -> ProviderAnswer | None:
        import anthropic

        messages: list[anthropic.types.beta.BetaMessageParam] = [
            {"role": "user" if role == "user" else "assistant", "content": content}
            for role, content in history
        ]
        messages.append(
            {
                "role": "user",
                "content": f"Document excerpts:\n\n{_format_excerpts(excerpts)}\n\n"
                f"Question: {question}",
            }
        )
        try:
            response = self._client.beta.messages.parse(
                model=self._model,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=messages,
                output_format=ProviderAnswer,
                output_config={"effort": self._effort},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError:
            logger.error("Anthropic API key was rejected; answering with document quotes only.")
            return None
        except anthropic.APIError as error:
            logger.warning("Anthropic request failed (%s); using document quotes.", error)
            return None

        if response.stop_reason in ("refusal", "max_tokens") or response.parsed_output is None:
            logger.warning("No usable model answer (stop_reason=%s)", response.stop_reason)
            return None
        return response.parsed_output


@lru_cache
def get_chat_provider() -> ChatProvider:
    settings = get_settings()
    if settings.ai_provider == "anthropic":
        return AnthropicProvider(settings.ai_api_key, settings.ai_chat_model, settings.ai_effort)
    return ExtractiveProvider()
