import pytest
from app.services.ai import AIProvider


@pytest.fixture
def provider():
    return AIProvider()


def test_1_fully_relevant_and_correct_answer(provider):
    """Scenario 1: Fully relevant and correct answer -> high score (8-10)."""
    question = "What is polymorphism in Python?"
    answer = (
        "Polymorphism allows objects of different classes to be accessed through a uniform interface. "
        "In Python, this is achieved through method overriding in subclasses or duck typing, "
        "where objects respond to the same method names regardless of their underlying type."
    )
    eval_result = provider.evaluate_answer(question, answer, [], experience_level="Intermediate")
    assert eval_result.relevance >= 0.8
    assert eval_result.correctness >= 0.8
    assert eval_result.score >= 8


def test_2_relevant_but_incomplete_answer(provider):
    """Scenario 2: Relevant but incomplete answer -> medium/partial score (4-6)."""
    question = "What are the differences between processes and threads?"
    answer = "Threads are lightweight and share memory space."
    eval_result = provider.evaluate_answer(question, answer, [], experience_level="Intermediate")
    assert eval_result.relevance >= 0.7
    assert 4 <= eval_result.score <= 6


def test_3_factually_correct_but_irrelevant_answer(provider):
    """Scenario 3: Factually correct but irrelevant answer -> low score (0-2).
    E.g. Answering Guido van Rossum created Python for a polymorphism question.
    """
    question = "What is polymorphism in Python?"
    answer = "Python was created by Guido van Rossum and is a dynamically typed programming language."
    eval_result = provider.evaluate_answer(question, answer, [], experience_level="Intermediate")

    # RELEVANCE GATE: Must NOT be high score!
    assert eval_result.relevance < 0.4
    assert eval_result.score <= 2
    assert "factually correct" in eval_result.feedback.lower() or "does not address" in eval_result.feedback.lower()


def test_4_completely_unrelated_answer(provider):
    """Scenario 4: Completely unrelated answer -> very low score (0-1)."""
    question = "What is a database index and why is it useful?"
    answer = "The quick brown fox jumps over the lazy dog in the forest."
    eval_result = provider.evaluate_answer(question, answer, [], experience_level="Intermediate")
    assert eval_result.relevance < 0.2
    assert eval_result.score <= 1


def test_5_partially_relevant_answer(provider):
    """Scenario 5: Partially relevant answer -> partial score (3-5)."""
    question = "How do you handle performance bottleneck issues in a database?"
    answer = "I would check database logs and restart the server."
    eval_result = provider.evaluate_answer(question, answer, [], experience_level="Intermediate")
    assert eval_result.relevance >= 0.5
    assert 3 <= eval_result.score <= 6


def test_6_keyword_heavy_spam_answer(provider):
    """Scenario 6: Keyword-heavy but conceptually incorrect / repetitive answer -> low/moderate score (2-4)."""
    question = "Explain REST API design principles."
    answer = "REST API REST API REST API endpoints HTTP GET POST PUT DELETE REST API REST API endpoints HTTP."
    eval_result = provider.evaluate_answer(question, answer, [], experience_level="Intermediate")
    assert eval_result.score <= 4


def test_7_beginner_level_correct_answer(provider):
    """Scenario 7: Beginner-level correct answer -> should not be unfairly penalized."""
    question = "What is a database index and why is it useful?"
    answer = "A database index speeds up searching for rows in a table."
    eval_result = provider.evaluate_answer(question, answer, [], experience_level="Beginner")
    assert eval_result.relevance >= 0.8
    assert eval_result.score >= 6


def test_8_advanced_answer_with_strong_reasoning(provider):
    """Scenario 8: Advanced answer with strong reasoning -> high score (8-10)."""
    question = "Explain the trade-offs of microservices vs monolithic architecture."
    answer = (
        "Monoliths offer simple deployment and ACID transactions across domain models, but can bottleneck build times. "
        "Microservices enable independent scaling and isolation, but introduce network latency, distributed consensus, "
        "and trade-offs around eventual consistency and operational complexity."
    )
    eval_result = provider.evaluate_answer(question, answer, [], experience_level="Advanced")
    assert eval_result.relevance >= 0.8
    assert eval_result.score >= 8


def test_9_empty_answer(provider):
    """Scenario 9: Empty answer -> score 0."""
    question = "What is polymorphism in Python?"
    answer = "   "
    eval_result = provider.evaluate_answer(question, answer, [], experience_level="Intermediate")
    assert eval_result.score == 0
    assert eval_result.relevance == 0.0


def test_10_cross_user_evaluation_isolation():
    """Scenario 10: Verify evaluation scoring logic is purely function of Q&A & context, independent of other user data."""
    provider_inst = AIProvider()
    q = "What is polymorphism in Python?"
    a_irrelevant = "Python was created by Guido van Rossum and is a dynamically typed programming language."

    res1 = provider_inst.evaluate_answer(q, a_irrelevant, [], experience_level="Intermediate")
    res2 = provider_inst.evaluate_answer(q, a_irrelevant, [], experience_level="Intermediate")

    assert res1.score == res2.score == 1
    assert res1.relevance == res2.relevance == 0.1
