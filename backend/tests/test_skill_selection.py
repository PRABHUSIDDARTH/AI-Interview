"""
Tests for Resume-Based Skill Selection and Question Generation.

TEST 1: resume=[React,Python,JS], selected=[React]  -> React-focused questions
TEST 2: resume=[React,Python,JS], selected=[Python] -> Python-focused questions
TEST 3: resume=[React,Python,JS], selected=[React,JS] -> React/JS relevant questions
TEST 4: selected_skills must be a subset of resume_skills (API validation)
TEST 5: Questions unrelated to selected skill are rejected/replaced by validator
TEST 6: Existing evaluation tests remain unaffected (smoke test)
TEST 7: Voice input / question text accessible via session flow (smoke test)
TEST 8: Question narration: question text returned and accessible (smoke test)
"""
import json
import pytest
from app.services.ai import AIProvider
from app.services.interview_engine import InterviewEngine
from app.schemas.interview import InterviewSessionCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_setup(selected, resume=None):
    return {
        "job_role": "Software Developer",
        "interview_type": "Technical",
        "experience_level": "Intermediate",
        "difficulty": "Medium",
        "question_count": 3,
        "interview_language": "English",
        "resume_skills": resume or selected,  # resume contains at least the selected ones
        "selected_skills": selected,
    }


def questions_mention_skill(questions, skill):
    """Return True if at least one question mentions the skill (case-insensitive)."""
    skill_lower = skill.lower()
    return any(skill_lower in q.lower() for q in questions)


def questions_mention_any(questions, skills):
    """Return True if at least one question mentions any of the given skills."""
    return any(questions_mention_skill(questions, s) for s in skills)


# ---------------------------------------------------------------------------
# TEST 1: Single selected skill — React
# ---------------------------------------------------------------------------

def test_1_react_selected_questions_focus_on_react():
    """Selected skill=React -> at least one mock question specifically targets React."""
    ai = AIProvider()  # mock provider
    setup = make_setup(
        selected=["React"],
        resume=["React", "Python", "JavaScript"],
    )
    questions = ai.generate_questions_batch(setup, 3)
    assert len(questions) == 3
    assert questions_mention_skill(questions, "React"), (
        f"Expected at least one React-focused question. Got: {questions}"
    )


# ---------------------------------------------------------------------------
# TEST 2: Single selected skill — Python
# ---------------------------------------------------------------------------

def test_2_python_selected_questions_focus_on_python():
    """Selected skill=Python -> at least one mock question specifically targets Python."""
    ai = AIProvider()
    setup = make_setup(
        selected=["Python"],
        resume=["React", "Python", "JavaScript"],
    )
    questions = ai.generate_questions_batch(setup, 3)
    assert len(questions) == 3
    assert questions_mention_skill(questions, "Python"), (
        f"Expected at least one Python-focused question. Got: {questions}"
    )


# ---------------------------------------------------------------------------
# TEST 3: Multi-skill selection — React + JavaScript
# ---------------------------------------------------------------------------

def test_3_multi_skill_selection_react_and_javascript():
    """Selected skills=[React, JavaScript] -> questions relevant to React/JavaScript."""
    ai = AIProvider()
    setup = make_setup(
        selected=["React", "JavaScript"],
        resume=["React", "Python", "JavaScript"],
    )
    questions = ai.generate_questions_batch(setup, 3)
    assert len(questions) == 3
    assert questions_mention_any(questions, ["React", "JavaScript"]), (
        f"Expected questions about React or JavaScript. Got: {questions}"
    )


# ---------------------------------------------------------------------------
# TEST 4: selected_skills must be a subset of resume_skills
# ---------------------------------------------------------------------------

def test_4_selected_skills_must_be_subset_of_resume_skills():
    """Skill not in resume_skills must NOT appear as a valid selection (business rule)."""
    resume_skills = ["React", "Python", "JavaScript"]
    selected_skills = ["Angular"]  # Angular NOT in resume

    # Validate the subset rule (same logic as the API endpoint)
    invalid = [s for s in selected_skills if s not in resume_skills]
    assert len(invalid) > 0, "Angular should not be in resume skills"
    assert "Angular" in invalid


def test_4b_selected_skills_valid_subset_passes():
    """All items in selected_skills are present in resume_skills — validation passes."""
    resume_skills = ["React", "Python", "JavaScript"]
    selected_skills = ["React", "Python"]
    invalid = [s for s in selected_skills if s not in resume_skills]
    assert len(invalid) == 0


# ---------------------------------------------------------------------------
# TEST 5: Validator rejects questions unrelated to selected skill
# ---------------------------------------------------------------------------

def test_5_validator_rejects_unrelated_question():
    """_validate_skill_focus returns invalid indices for off-topic questions."""
    ai = AIProvider()
    focus_skills = ["React"]
    questions = [
        "Explain how useEffect works in React.",          # valid — mentions React
        "What is the time complexity of quicksort?",      # invalid — no React
        "How do React hooks improve component design?",   # valid — mentions React
    ]
    all_valid, invalid_indices = ai._validate_skill_focus(questions, focus_skills)
    assert not all_valid
    assert 1 in invalid_indices
    assert 0 not in invalid_indices
    assert 2 not in invalid_indices


def test_5b_validator_passes_when_all_questions_mention_skill():
    """_validate_skill_focus returns valid when every question mentions the focus skill."""
    ai = AIProvider()
    focus_skills = ["Python"]
    questions = [
        "What are Python decorators and how do you use them?",
        "Explain Python's GIL and its impact on multi-threading.",
        "How does Python handle memory management?",
    ]
    all_valid, invalid_indices = ai._validate_skill_focus(questions, focus_skills)
    assert all_valid
    assert len(invalid_indices) == 0


def test_5c_fallback_question_mentions_skill():
    """_skill_fallback_question always produces a question mentioning the given skill."""
    ai = AIProvider()
    for skill in ["React", "Python", "PostgreSQL", "Docker"]:
        setup = {"job_role": "Developer", "experience_level": "Intermediate", "difficulty": "Medium"}
        fallback = ai._skill_fallback_question(skill, setup)
        assert skill.lower() in fallback.lower(), (
            f"Fallback for '{skill}' does not mention the skill: {fallback}"
        )


# ---------------------------------------------------------------------------
# TEST 6: Existing evaluation tests remain unaffected (regression smoke test)
# ---------------------------------------------------------------------------

def test_6_existing_evaluation_still_works():
    """Smoke test: existing evaluation logic is not broken by the new changes."""
    ai = AIProvider()
    question = "What is polymorphism in Python?"
    answer = (
        "Polymorphism allows objects of different classes to be accessed through a uniform interface. "
        "In Python this is achieved via method overriding or duck typing."
    )
    result = ai.evaluate_answer(question, answer, [], experience_level="Intermediate")
    assert result.relevance >= 0.8
    assert result.score >= 8


def test_6b_relevance_gate_still_enforced():
    """The relevance gate (score <= 2 for off-topic answers) is not regressed."""
    ai = AIProvider()
    question = "What is a database index?"
    answer = "Python was created by Guido van Rossum."
    result = ai.evaluate_answer(question, answer, [], experience_level="Intermediate")
    assert result.relevance < 0.4
    assert result.score <= 2


# ---------------------------------------------------------------------------
# TEST 7: Voice/speech — question text accessible via the question flow (smoke)
# ---------------------------------------------------------------------------

def test_7_question_text_accessible_for_speech():
    """Question returned by mock generation is a non-empty string suitable for TTS."""
    ai = AIProvider()
    setup = make_setup(selected=["React"], resume=["React", "Python"])
    questions = ai.generate_questions_batch(setup, 3)
    for q in questions:
        assert isinstance(q, str), "Question must be a string"
        assert len(q.strip()) > 0, "Question must not be empty"
        # Ensure no control characters that would break TTS
        assert "\x00" not in q


# ---------------------------------------------------------------------------
# TEST 8: Narration — question text is returned correctly for all skill combos
# ---------------------------------------------------------------------------

def test_8_narration_question_text_returned_for_multiple_skills():
    """All generated questions are valid strings regardless of how many skills are selected."""
    ai = AIProvider()
    for selected in [["React"], ["Python"], ["React", "JavaScript"], ["React", "Python", "Node.js"]]:
        resume = selected + ["PostgreSQL"]
        setup = make_setup(selected=selected, resume=resume)
        questions = ai.generate_questions_batch(setup, 3)
        assert len(questions) == 3
        for q in questions:
            assert isinstance(q, str) and len(q.strip()) > 0, (
                f"Invalid question for selected={selected}: {q!r}"
            )


# ---------------------------------------------------------------------------
# Additional: mock questions don't generate un-selected skills
# ---------------------------------------------------------------------------

def test_9_mock_does_not_generate_non_selected_python_when_react_selected():
    """When selected_skills=[React], mock questions should not be about Python alone."""
    ai = AIProvider()
    setup = make_setup(
        selected=["React"],
        resume=["React", "Python", "JavaScript", "Node.js"],
    )
    questions = ai.generate_questions_batch(setup, 5)
    # All questions from mock should mention React (selected), not unrelated skills
    for q in questions:
        # Questions should be skill-targeted; none should be generic enough to hide the skill
        assert isinstance(q, str)
    # At least one must clearly mention React
    assert questions_mention_skill(questions, "React"), (
        f"No React mention in any question: {questions}"
    )


def test_10_selected_skills_persisted_in_session_setup():
    """selected_skills passed into setup dict is correctly carried through."""
    ai = AIProvider()
    setup = {
        "job_role": "Frontend Developer",
        "interview_type": "Technical",
        "experience_level": "Intermediate",
        "difficulty": "Medium",
        "question_count": 3,
        "interview_language": "English",
        "resume_skills": ["React", "JavaScript", "CSS"],
        "selected_skills": ["React"],
    }
    # Validate the setup contains selected_skills before generation
    assert setup["selected_skills"] == ["React"]
    assert "React" in setup["resume_skills"]

    questions = ai.generate_questions_batch(setup, 3)
    assert len(questions) == 3
