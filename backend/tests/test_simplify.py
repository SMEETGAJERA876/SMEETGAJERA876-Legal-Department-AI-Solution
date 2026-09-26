"""Plain-language rewriting (app/services/simplify.py).

The rewriter is deliberately dumb: a dictionary plus a few safe changes. What these tests hold
is the safety property — it may make wording easier, but it must never change what the wording
*says*. Every case below checks that the facts survive: numbers, amounts, dates, parties and
negations come through untouched.
"""

import re

import pytest

from app.services import glossary
from app.services.simplify import simplified

APPEAL = (
    "41. Appeal against order of District Commission.—Any person aggrieved by an order made "
    "by the District Commission may prefer an appeal against such order to the State Commission "
    "on the grounds of facts or law within a period of forty-five days from the date of the "
    "order, in such form and manner, as may be prescribed:"
)
RENT = (
    "(2) The Lessee shall pay to the Lessor a monthly rent of Rs. 15,000/- on or before the "
    "fifth day of each calendar month, and shall not sublet the premises without the prior "
    "written consent of the Lessor."
)


def test_formal_wording_becomes_everyday_wording() -> None:
    result = simplified(APPEAL)
    assert "aggrieved" not in result.simple.lower()
    assert "as may be prescribed" not in result.simple.lower()
    assert "person affected" in result.simple.lower()
    # The terms it replaced are reported, so the reader can see what was swapped.
    assert ("person aggrieved", "person affected") in result.terms


def test_numbers_written_as_words_are_also_written_as_digits() -> None:
    assert "45 days" in simplified(APPEAL).simple
    # ...but a number already followed by its digits is left alone, not doubled.
    notice = "Either party may terminate by giving ninety (90) days' written notice."
    assert "ninety (90) days" in simplified(notice).simple
    assert "90 (90)" not in simplified(notice).simple


@pytest.mark.parametrize(
    "text, must_survive",
    [
        (RENT, ["Rs. 15,000/-", "Lessee", "Lessor"]),
        (APPEAL, ["District Commission", "State Commission"]),
        ("The Employee shall not disclose any Confidential Information.", ["not"]),
        ("Rent shall not exceed Rs. 20,000 per month from 1 April 2026.", ["not", "1 April 2026"]),
    ],
)
def test_facts_are_never_lost(text: str, must_survive: list[str]) -> None:
    """A simplification that drops a number, a party or a negation would be dangerous."""
    result = simplified(text)
    for fact in must_survive:
        # Parties may be renamed by the glossary (Lessee → Tenant); the *value* must survive.
        renamed = {"Lessee": "Tenant", "Lessor": "Landlord"}.get(fact, fact)
        assert fact in result.simple or renamed in result.simple, (fact, result.simple)


def test_every_amount_and_date_survives() -> None:
    text = (
        "The Tenant shall pay Rs. 15,000 on or before the 5th day of each month, a deposit of "
        "Rs. 90,000, and shall vacate on 31 March 2027 after giving 2 months' notice."
    )
    result = simplified(text)
    for number in re.findall(r"[\d,]+", text):
        assert number in result.simple, (number, result.simple)


def test_the_original_is_always_kept() -> None:
    result = simplified(RENT)
    assert result.original.startswith("(2) The Lessee shall pay")
    assert result.simple != result.original


def test_tidying_alone_is_not_worth_showing() -> None:
    """Stripping "(b) " is not a translation; the website should not show two identical lines."""
    assert not simplified("(b) the product is defective in design; or").worth_showing
    assert simplified(APPEAL).worth_showing


def test_a_short_fragment_is_not_split_into_stubs() -> None:
    assert "or." not in simplified("(b) the product is defective in design; or").simple.split()


def test_plain_words_map_to_the_formal_ones_the_document_uses() -> None:
    """The glossary bridges the two directions: "builder" ↔ "promoter"."""
    assert "promoter" in glossary.legal_terms("will the builder refund my money")
    assert "builder" in glossary.plain_phrases("will the builder refund my money")
    # ...and the formal term comes back as the everyday one when it appears in a quote.
    assert ("promoter", "builder") in simplified("The promoter shall refund the amount.").terms


@pytest.mark.parametrize(
    "plain, legal, expected",
    [
        ("builder", "promoter", True),
        ("money back", "return of amount", True),
        ("boss", "employer", True),
        ("complain", "complaint", False),
        ("appeal", "appeals", False),
        ("notice", "notice", False),
    ],
)
def test_only_a_real_change_of_word_is_worth_showing(
    plain: str, legal: str, expected: bool
) -> None:
    """"complain" → "complaint" is the same word; showing it would be padding."""
    from app.services.qa import _worth_bridging

    assert _worth_bridging(plain, legal) is expected
