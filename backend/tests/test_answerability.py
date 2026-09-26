"""The guard against answering what a document doesn't say (app/services/answerability.py)."""

from app.services.answerability import (
    MIN_RELEVANCE,
    STRONG_RELEVANCE,
    answerable,
    subject_coverage,
)

CONSUMER_ACT_WORDS = {
    "consumer", "complaint", "district", "commission", "penalty", "punishable", "imprisonment",
    "order", "appeal", "goods", "services", "value", "fine", "rupees", "within", "years",
}  # fmt: skip
WAGES_CODE_WORDS = {"wages", "employer", "employee", "punishable", "fine", "bonus", "minimum"}


def test_generic_words_are_not_the_subject() -> None:
    coverage = subject_coverage("What is the punishment for cybercrime?", WAGES_CODE_WORDS)
    assert coverage.subject_words == ["cybercrime"]
    assert coverage.covered == []
    assert not answerable("What is the punishment for cybercrime?", WAGES_CODE_WORDS, 1.0)


def test_topic_missing_from_document_is_not_answered() -> None:
    assert not answerable("What is the penalty for drunk driving?", CONSUMER_ACT_WORDS, 0.0)


def test_everyday_words_count_through_the_glossary() -> None:
    # "salary" is not in the Code on Wages, but its legal wording "wages" is.
    coverage = subject_coverage("When must my employer pay my salary?", WAGES_CODE_WORDS)
    assert coverage.sufficient, coverage


def test_irrelevant_best_passage_is_not_answered() -> None:
    question = "How do I appeal against the District Commission's order?"
    assert answerable(question, CONSUMER_ACT_WORDS, MIN_RELEVANCE + 1)
    assert not answerable(question, CONSUMER_ACT_WORDS, MIN_RELEVANCE - 1)
    assert answerable(question, CONSUMER_ACT_WORDS, None)  # re-ranker switched off


def test_confident_passage_overrides_the_word_check() -> None:
    # "cancel a gift" isn't the Act's wording, but the re-ranker is sure of the passage.
    question = "Can a parent cancel a gift of property if the child stops looking after them?"
    words = {"transfer", "property", "void", "senior", "citizen", "gift", "tribunal"}
    assert answerable(question, words, STRONG_RELEVANCE + 0.5)
    # Below that confidence the subject words must still be present.
    assert not answerable("What is the penalty for drunk driving?", CONSUMER_ACT_WORDS, 1.0)


def test_confidence_cannot_supply_a_subject_the_document_never_mentions() -> None:
    """The guard that the Transfer of Property Act needs against a question about wages.

    A high cross-encoder score means "this passage is similar to the question", not "this
    document covers the topic". When none of the subject words appear anywhere — directly or
    through the glossary — no score may override that.
    """
    property_act = {"transfer", "property", "lease", "mortgage", "gift", "immovable", "sale"}
    question = "What is the minimum wage for factory workers?"
    assert subject_coverage(question, property_act).covered == []
    for relevance in (STRONG_RELEVANCE, STRONG_RELEVANCE + 5.0, 10.0):
        assert not answerable(question, property_act, relevance), relevance


def test_confidence_still_bridges_different_wording_for_the_same_thing() -> None:
    """The bypass must keep working where it was meant to: same subject, other words."""
    senior_act = {"parent", "child", "property", "transfer", "maintenance", "void", "senior"}
    question = "Can a parent cancel a gift of property if the child stops looking after them?"
    assert subject_coverage(question, senior_act).covered, "some subject words are present"
    assert answerable(question, senior_act, STRONG_RELEVANCE + 1.0)


def test_a_stem_does_not_match_an_unrelated_shorter_word() -> None:
    """The fault behind "the minimum wage for factory workers" on the Transfer of Property Act.

    Stemming to four characters turned "factory" into "fact" and "workers" into "work" — words
    that occur in almost any statute — so a document about land looked like it covered wages.
    """
    property_act = {"transfer", "property", "lease", "fact", "facts", "work", "works", "immovable"}
    coverage = subject_coverage("What is the minimum wage for factory workers?", property_act)
    assert coverage.covered == [], coverage.covered
    assert not coverage.sufficient


def test_real_inflections_are_still_matched() -> None:
    """Tightening the stem must not stop a question finding the word the document uses."""
    vocabulary = {"child", "registration", "appeals", "tenancies", "possession"}
    # "penalty" and "fine" are deliberately absent: they are GENERIC, so they are never
    # subject words in the first place.
    for word in ("children", "register", "appeal", "tenancy", "possessions"):
        assert subject_coverage(f"What about the {word}?", vocabulary).covered == [word], word
