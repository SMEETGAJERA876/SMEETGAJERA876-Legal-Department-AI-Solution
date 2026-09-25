from app.services.chunking import chunk_pages, detect_clause_start
from app.services.concepts import detect_query_concepts, related_concepts
from app.services.extraction import detect_parties, extract_facts
from app.services.text_utils import contains_quote


def test_detects_top_level_heading() -> None:
    start = detect_clause_start("12. Termination")
    assert start is not None
    assert (start.ref, start.heading, start.is_top_level) == ("12", "Termination", True)


def test_sub_clause_sentence_is_not_a_heading() -> None:
    start = detect_clause_start("12.1 Either party may terminate this Agreement by providing")
    assert start is not None
    assert start.ref == "12.1"
    assert start.heading is None


def test_keyword_clause_heading() -> None:
    start = detect_clause_start("Section 4: Payment Terms")
    assert start is not None
    assert (start.ref, start.heading) == ("Section 4", "Payment Terms")


def test_plain_numbers_are_not_clauses() -> None:
    assert detect_clause_start("90 days after signing") is None
    assert detect_clause_start("2026 was a good year") is None


def test_chunks_keep_page_numbers_and_inherit_headings() -> None:
    pages = [
        "1. Parties\n1.1 This agreement is between A and B.",
        "Page 1 of 2",
        "12. Termination\n12.1 Either party may terminate with ninety (90) days written notice.",
    ]
    chunks, clauses = chunk_pages(pages)
    termination = [c for c in chunks if c.clause_ref == "12.1"]
    assert len(termination) == 1
    assert termination[0].page_number == 3
    assert termination[0].heading == "Termination"
    assert "Page 1 of 2" not in " ".join(c.text for c in chunks)
    assert [c.clause_ref for c in clauses] == ["1", "12"]


def test_notice_period_extracted_from_words_and_digits() -> None:
    facts = extract_facts(
        [(0, "Either party may terminate by providing ninety (90) days written notice.", None)]
    )
    notice = [f for f in facts if f.concept == "notice_period"]
    assert [f.value for f in notice] == ["90 days"]
    assert "ninety (90) days" in notice[0].source_text


def test_notice_period_of_pattern() -> None:
    facts = extract_facts([(0, "The notice period of 30 days applies to both parties.", None)])
    assert "30 days" in [f.value for f in facts if f.concept == "notice_period"]


def test_payment_amount_and_date_extraction() -> None:
    facts = extract_facts(
        [(0, "The Company shall pay a salary of INR 1,20,000 per month from March 1, 2026.", None)]
    )
    values = {(f.concept, f.value) for f in facts}
    assert ("salary", "INR 1,20,000") in values
    assert ("important_dates", "March 1, 2026") in values


def test_no_facts_invented_from_unrelated_text() -> None:
    facts = extract_facts([(0, "The sky is blue and the office has a nice view.", None)])
    assert facts == []


def test_parties() -> None:
    text = "This Employment Agreement is made between Acme Corp (the Company) and Jane Doe."
    assert detect_parties(text) == ["Acme Corp", "Jane Doe"]


def test_query_concepts_understand_everyday_words() -> None:
    concepts = detect_query_concepts("What happens if I leave early?")
    assert "termination" in concepts
    assert "notice_period" in related_concepts(["termination"])


def test_quote_matching_ignores_whitespace_and_case() -> None:
    assert contains_quote("Either party may\nterminate this", "either party may terminate")
    assert not contains_quote("Either party may terminate", "the employee must pay")
