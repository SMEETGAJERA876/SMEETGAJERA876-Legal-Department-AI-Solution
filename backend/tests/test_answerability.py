"""The guard against answering what a document doesn't say (app/services/answerability.py)."""

from app.services.answerability import MIN_RELEVANCE, answerable, subject_coverage

CONSUMER_ACT_WORDS = {
    "consumer", "complaint", "district", "commission", "penalty", "punishable", "imprisonment",
    "order", "appeal", "goods", "services", "value", "fine", "rupees", "within", "years",
}  # fmt: skip
WAGES_CODE_WORDS = {"wages", "employer", "employee", "punishable", "fine", "bonus", "minimum"}


def test_generic_words_are_not_the_subject() -> None:
    coverage = subject_coverage("What is the punishment for cybercrime?", WAGES_CODE_WORDS)
    assert coverage.subject_words == ["cybercrime"]
    assert coverage.covered == []
    assert not answerable("What is the punishment for cybercrime?", WAGES_CODE_WORDS, 5.0)


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
