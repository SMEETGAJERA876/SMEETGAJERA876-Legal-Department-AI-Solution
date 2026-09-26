"""Evidence about how a document was made (app/services/authenticity.py).

The property that matters most here is the one about *not* firing. Wrongly refusing a citizen's
genuine government notice is a worse failure than missing a forged one, so the first test runs
every real document in the repository — 20 Acts downloaded from India Code and the project's
samples — and requires that none of them is flagged, let alone rejected.
"""

import glob
from pathlib import Path

import pymupdf
import pytest
from fpdf import FPDF

from app.services import authenticity

ROOT = Path(__file__).resolve().parents[2]

AI_DRAFTED = [
    "Sure! Here is a draft rent agreement for your use.",
    "RENT AGREEMENT",
    "This agreement is made on [Insert Date] between [Your Name] (Lessor) and",
    "John Doe (Lessee) for the property at [Insert Address].",
    "The monthly rent shall be Rs. XXXX payable in advance.",
    "Note: This is a template. Feel free to modify it as needed.",
    "I cannot provide legal advice - please consult a qualified lawyer.",
]

GENUINE = [
    "GOVERNMENT OF MAHARASHTRA",
    "Office of the Municipal Commissioner",
    "No. MC/2026/114/A dated 14 March 2026",
    "Notice is hereby given that the water supply will be interrupted on 20 March 2026",
    "between 10:00 and 16:00 for maintenance of the main pipeline.",
    "Sd/- Commissioner, seal of the Corporation",
]


def _pdf(lines: list[str], producer: str | None = None) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=11)
    for line in lines:
        pdf.cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")
    if producer:
        pdf.set_producer(producer)
    return bytes(pdf.output())


def _pages(data: bytes) -> list[tuple[int, str]]:
    with pymupdf.open(stream=data, filetype="pdf") as document:
        return [(i + 1, page.get_text()) for i, page in enumerate(document)]


def _real_documents() -> list[str]:
    return sorted(glob.glob(str(ROOT / "dataset" / "indiacode" / "*.pdf"))) + sorted(
        glob.glob(str(ROOT / "samples" / "*.pdf"))
    )


@pytest.mark.parametrize("path", _real_documents(), ids=lambda p: Path(p).stem[:40])
def test_a_real_document_is_never_refused(path: str) -> None:
    """The false-positive test. A genuine document must not be flagged or refused."""
    data = Path(path).read_bytes()
    category = "policy" if "indiacode" in path else "property"
    report = authenticity.inspect(data, _pages(data), category)
    assert authenticity.rejection_reason(report) is None, [s.label for s in report.high]
    assert report.verdict == "ordinary", [
        (s.severity, s.id, s.evidence) for s in report.signals
    ]


def test_an_ai_drafted_document_is_caught_and_refused() -> None:
    data = _pdf(AI_DRAFTED, producer="ChatGPT PDF Export 1.2")
    report = authenticity.inspect(data, _pages(data), "property")
    assert report.verdict == "concerns"
    found = {s.id for s in report.signals}
    assert "ai_tool_metadata" in found, "the PDF names the tool that wrote it"
    assert "assistant_text" in found, "the assistant's own words were left in"
    reason = authenticity.rejection_reason(report)
    assert reason is not None and "not accepted" in reason


def test_the_tool_in_the_metadata_is_enough_on_its_own() -> None:
    """Even clean-looking text is refused when the file records an AI tool as its producer."""
    data = _pdf(GENUINE, producer="Claude by Anthropic")
    report = authenticity.inspect(data, _pages(data), "government")
    assert {s.id for s in report.signals} >= {"ai_tool_metadata"}
    assert authenticity.rejection_reason(report) is not None


def test_an_ordinary_word_processor_is_not_suspicious() -> None:
    data = _pdf(GENUINE, producer="Microsoft® Word 2021")
    report = authenticity.inspect(data, _pages(data), "government")
    assert report.verdict == "ordinary", [s.id for s in report.signals]


def test_placeholders_are_flagged_but_never_refused() -> None:
    """A template is a legitimate thing to want explained, so it is flagged, not refused."""
    data = _pdf(
        ["LEASE DEED", "Between [Your Name] and the tenant.", "Rent: Rs. XXXX per month."],
        producer="Microsoft® Word 2021",
    )
    report = authenticity.inspect(data, _pages(data), "property")
    assert "placeholder_text" in {s.id for s in report.signals}
    assert report.verdict == "check"
    assert authenticity.rejection_reason(report) is None


def test_an_official_notice_missing_its_markings_is_flagged() -> None:
    data = _pdf(
        ["NOTICE", "The road will be closed next week.", "Please cooperate."],
        producer="Microsoft® Word 2021",
    )
    report = authenticity.inspect(data, _pages(data), "public_notice")
    signal = next(s for s in report.signals if s.id == "missing_official_markers")
    assert "reference number" in signal.detail
    assert authenticity.rejection_reason(report) is None, "absence is never grounds to refuse"


def test_writing_style_is_never_used_to_refuse() -> None:
    """Formal, repetitive, machine-sounding prose from a real office must pass untouched.

    This is the guarantee that ClauseLens does not run a stylometric AI detector: the text
    below is exactly what such a detector scores as machine-written.
    """
    uniform = [
        "The applicant shall submit the prescribed form to the competent authority.",
        "The competent authority shall verify the particulars furnished by the applicant.",
        "The applicant shall be informed of the decision within thirty days.",
        "The applicant may prefer an appeal against the decision within thirty days.",
    ] * 4
    data = _pdf(
        ["GOVERNMENT OF INDIA", "Ministry of Housing", "F. No. 11/2026/HS dated 3 January 2026"]
        + uniform
        + ["Sd/- Under Secretary"],
        producer="Microsoft® Word 2021",
    )
    report = authenticity.inspect(data, _pages(data), "government")
    assert report.verdict == "ordinary", [s.id for s in report.signals]
    assert authenticity.rejection_reason(report) is None


def test_a_report_can_always_be_checked_by_the_reader() -> None:
    data = _pdf(AI_DRAFTED, producer="ChatGPT PDF Export 1.2")
    report = authenticity.inspect(data, _pages(data), "property")
    for signal in report.signals:
        assert signal.label and signal.detail
        # A signal about something present must show it; one about absence explains in `detail`.
        if signal.id not in {"missing_official_markers", "image_only"}:
            assert signal.evidence, signal.id


def test_a_damaged_file_never_breaks_processing() -> None:
    report = authenticity.inspect(b"not a pdf at all", [(1, "some text")], None)
    assert isinstance(report.verdict, str)


def test_the_verdict_is_never_a_claim_of_fake_or_genuine() -> None:
    data = _pdf(AI_DRAFTED, producer="ChatGPT PDF Export 1.2")
    report = authenticity.inspect(data, _pages(data), "property")
    assert report.verdict in {"concerns", "check", "ordinary"}
    words = " ".join(f"{s.label} {s.detail}" for s in report.signals).casefold()
    for claim in ("is fake", "is forged", "is genuine", "is authentic"):
        assert claim not in words, f"the report must not assert {claim!r}"
