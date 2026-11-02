"""
Unit tests for the Question-Specific + Trusted-Source-Grounded Answer Validation System.
Verifies all 12 Phase 21 evaluation test cases.
"""

import pytest
from app.services.ai import AIProvider

ai_provider = AIProvider()


def test_scenario_1_polymorphism_correct_answer():
    """TEST 1: Polymorphism in Python - Correct answer -> HIGH relevance, HIGH correctness, HIGH score."""
    question = "What is polymorphism in Python?"
    answer = (
        "Polymorphism in Python allows objects of different classes to be treated through a common interface. "
        "It can be achieved via method overriding in derived classes or using Python's duck typing."
    )
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Intermediate"
    )
    assert result.relevance >= 0.7, f"Expected high relevance, got {result.relevance}"
    assert result.correctness >= 0.7, f"Expected high correctness, got {result.correctness}"
    assert result.score >= 7, f"Expected high score >= 7, got {result.score}"


def test_scenario_2_polymorphism_irrelevant_answer():
    """TEST 2: Polymorphism in Python - Irrelevant answer ('Guido van Rossum') -> LOW relevance, LOW score."""
    question = "What is polymorphism in Python?"
    answer = "Python was created by Guido van Rossum and is a high-level programming language."
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Intermediate"
    )
    assert result.relevance <= 0.4, f"Expected low relevance <= 0.4, got {result.relevance}"
    assert result.score <= 3, f"Expected low score <= 3, got {result.score}"


def test_scenario_3_polymorphism_concise_correct_answer():
    """TEST 3: Polymorphism in Python - Short correct answer -> HIGH relevance, GOOD correctness."""
    question = "What is polymorphism in Python?"
    answer = "Polymorphism means the same interface can work with different object types."
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Intermediate"
    )
    assert result.relevance >= 0.7, f"Expected high relevance, got {result.relevance}"
    assert result.correctness >= 0.7, f"Expected good correctness, got {result.correctness}"
    assert result.score >= 6, f"Expected good score >= 6, got {result.score}"


def test_scenario_4_primary_key_correct():
    """TEST 4: Primary Key in SQL - Correct answer -> HIGH score."""
    question = "What is a primary key in SQL?"
    answer = "A primary key uniquely identifies each row in a database table and cannot contain NULL values."
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Beginner"
    )
    assert result.relevance >= 0.8
    assert result.correctness >= 0.8
    assert result.score >= 7


def test_scenario_5_primary_key_contradiction():
    """TEST 5: Primary Key in SQL - Contradictory statement -> LOW correctness, LOW score."""
    question = "What is a primary key in SQL?"
    answer = "A primary key is used in SQL database tables, but duplicate primary key values are allowed in rows."
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Intermediate"
    )
    assert result.correctness <= 0.4, f"Expected low correctness due to contradiction, got {result.correctness}"
    assert result.score <= 4, f"Expected low/capped score due to contradiction, got {result.score}"


def test_scenario_6_long_irrelevant_answer():
    """TEST 6: Long but irrelevant answer -> LOW score."""
    question = "What is polymorphism in Python?"
    answer = (
        "Python was created by Guido van Rossum in the late 1980s and released in 1991. "
        "It emphasizes code readability with its notable use of significant whitespace. "
        "Its language constructs and object-oriented approach aim to help programmers write clear, logical code for small and large-scale projects."
    )
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Intermediate"
    )
    assert result.relevance <= 0.4
    assert result.score <= 3


def test_scenario_7_short_technically_correct_answer():
    """TEST 7: Short but technically correct answer -> HIGH score."""
    question = "What is a primary key in SQL?"
    answer = "A primary key uniquely identifies each row."
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Beginner"
    )
    assert result.score >= 6
    assert result.relevance >= 0.8


def test_scenario_8_partially_correct_answer():
    """TEST 8: Partially correct answer -> MEDIUM score."""
    question = "What is REST API?"
    answer = "REST API is used for web communication using HTTP methods, but I don't remember what stateless means."
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Intermediate"
    )
    assert 4 <= result.score <= 7
    assert result.relevance >= 0.6


def test_scenario_9_empty_answer():
    """TEST 9: Empty answer -> VERY LOW score (1/10)."""
    question = "What is polymorphism in Python?"
    answer = "   "
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Intermediate"
    )
    assert result.score <= 1
    assert result.relevance == 0.0


def test_scenario_10_spam_garbage_answer():
    """TEST 10: Random/spam answer ('asdfghjkl') -> VERY LOW score."""
    question = "What is polymorphism in Python?"
    answer = "asdfghjkl python python python 12345"
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Intermediate"
    )
    assert result.score <= 2
    assert result.relevance <= 0.2


def test_scenario_11_correct_concept_missing_depth():
    """TEST 11: Correct concept but missing depth -> HIGH relevance + moderate technical depth."""
    question = "How does garbage collection work in Python?"
    answer = "Python uses reference counting and a cyclic garbage collector to clean up unused memory objects."
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Advanced"
    )
    assert result.relevance >= 0.8
    assert result.correctness >= 0.7
    assert 0.4 <= result.technical_depth <= 0.8


def test_scenario_12_correct_answer_with_one_factual_contradiction():
    """TEST 12: Correct answer containing one factual contradiction -> correctness reduced."""
    question = "What is a primary key in SQL?"
    answer = "A primary key uniquely identifies rows in a SQL table. It can have null values multiple times."
    result = ai_provider.evaluate_answer(
        question=question,
        answer=answer,
        experience_level="Intermediate"
    )
    assert result.correctness <= 0.5
    assert result.score <= 4
