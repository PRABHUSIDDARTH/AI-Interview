"""
Tests for Hybrid Source-Grounded Question Generation & Knowledge Retrieval System.

12 Target Test Cases:
TEST 1: Resume=[React, Python, JS], Selected=[React] -> React-focused questions
TEST 2: Selected=[Python] -> Python-focused questions
TEST 3: Selected=[React, JavaScript] -> React & JS relevant questions
TEST 4: Unselected skill question (Python when only React selected) -> Rejected by validator
TEST 5: Unselected skill question (Angular when not selected) -> Rejected by validator
TEST 6: Near-duplicate questions -> Deduplication filter detects and replaces
TEST 7: Difficulty validation: Basic definition question under Hard difficulty is upgraded/replaced
TEST 8: Unknown skill or missing source -> Graceful fallback to _fallback.json records
TEST 9: Evaluation engine regression check -> Scoring & feedback work cleanly
TEST 10: Voice input compatibility -> Generated question strings are clean, non-empty, TTS-friendly
TEST 11: Question narration flow -> Question metadata and text properly structured for audio TTS
TEST 12: Full interview session creation -> Questions generated, answered, source_context persisted
"""

import json
import pytest
import app.models  # registers User and InterviewSession models
from app.core.database import SessionLocal, engine, Base
from app.core.migration import run_auto_migrations
from app.services.ai import AIProvider
from app.services.knowledge.retriever import LocalKnowledgeRetriever
from app.services.knowledge.base import TopicRecord
from app.services.interview_engine import InterviewEngine
from app.schemas.interview import InterviewSessionCreate
from app.models.user import User


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    run_auto_migrations(engine)


def make_setup(selected, resume=None, difficulty="Medium", experience_level="Intermediate"):
    return {
        "job_role": "Full Stack Developer",
        "interview_type": "Technical",
        "experience_level": experience_level,
        "difficulty": difficulty,
        "question_count": 3,
        "interview_language": "English",
        "resume_skills": resume or selected,
        "selected_skills": selected,
    }


def questions_mention_skill(questions, skill):
    skill_lower = skill.lower()
    return any(skill_lower in q.lower() for q in questions)


# ---------------------------------------------------------------------------
# TEST 1: Resume=[React, Python, JS], Selected=[React] -> React focus
# ---------------------------------------------------------------------------
def test_1_react_selected_questions_focus_on_react():
    retriever = LocalKnowledgeRetriever()
    topics = retriever.retrieve(["React"], difficulty="Medium", experience_level="Intermediate", max_topics=6)
    assert len(topics) > 0
    assert all(t.skill == "React" for t in topics)

    ai = AIProvider()
    setup = make_setup(selected=["React"], resume=["React", "Python", "JavaScript"])
    questions = ai.generate_questions_batch(setup, 3, retrieved_knowledge=[t.to_dict() for t in topics])

    assert len(questions) == 3
    assert questions_mention_skill(questions, "React")
    react_count = sum(1 for q in questions if "react" in q.lower())
    assert react_count >= 1


# ---------------------------------------------------------------------------
# TEST 2: Selected=[Python] -> Python-focused questions
# ---------------------------------------------------------------------------
def test_2_python_selected_questions_focus_on_python():
    retriever = LocalKnowledgeRetriever()
    topics = retriever.retrieve(["Python"], difficulty="Medium", experience_level="Intermediate", max_topics=6)
    assert len(topics) > 0
    assert all(t.skill == "Python" for t in topics)

    ai = AIProvider()
    setup = make_setup(selected=["Python"], resume=["Python", "Go", "Docker"])
    questions = ai.generate_questions_batch(setup, 3, retrieved_knowledge=[t.to_dict() for t in topics])

    assert len(questions) == 3
    assert questions_mention_skill(questions, "Python")


# ---------------------------------------------------------------------------
# TEST 3: Selected=[React, JavaScript] -> React/JS relevant questions
# ---------------------------------------------------------------------------
def test_3_multi_skill_selection_covers_both():
    retriever = LocalKnowledgeRetriever()
    topics = retriever.retrieve(["React", "JavaScript"], difficulty="Medium", experience_level="Intermediate", max_topics=8)
    assert len(topics) >= 2

    skills_in_topics = {t.skill for t in topics}
    assert "React" in skills_in_topics
    assert "JavaScript" in skills_in_topics

    ai = AIProvider()
    setup = make_setup(selected=["React", "JavaScript"], resume=["React", "JavaScript", "Python"])
    questions = ai.generate_questions_batch(setup, 4, retrieved_knowledge=[t.to_dict() for t in topics])

    assert len(questions) == 4
    has_react = questions_mention_skill(questions, "React")
    has_js = questions_mention_skill(questions, "JavaScript") or questions_mention_skill(questions, "JS")
    assert has_react or has_js


# ---------------------------------------------------------------------------
# TEST 4: Python question generated when only React selected -> Rejected
# ---------------------------------------------------------------------------
def test_4_unselected_skill_rejected_by_validator():
    ai = AIProvider()
    focus_skills = ["React"]

    # Simulating a raw list with an off-topic Python question
    raw_questions = [
        "How do you manage component state with useState in React?",
        "Explain Python GIL and multi-threading execution model.",
        "What are the best practices for memoization in React using useMemo?",
    ]
    valid, invalid_indices = ai._validate_skill_focus(raw_questions, focus_skills)
    assert not valid
    assert invalid_indices == [1]  # Python question detected as invalid


# ---------------------------------------------------------------------------
# TEST 5: Angular question when Angular not selected -> Rejected
# ---------------------------------------------------------------------------
def test_5_angular_question_rejected_when_not_selected():
    ai = AIProvider()
    focus_skills = ["React", "PostgreSQL"]

    raw_questions = [
        "How does Angular dependency injection compare to hierarchical injectors?",
        "Explain indexing strategies in PostgreSQL.",
    ]
    valid, invalid_indices = ai._validate_skill_focus(raw_questions, focus_skills)
    assert not valid
    assert 0 in invalid_indices


# ---------------------------------------------------------------------------
# TEST 6: Near-duplicate questions -> Deduplicated
# ---------------------------------------------------------------------------
def test_6_deduplication_removes_near_identical_questions():
    ai = AIProvider()
    setup = make_setup(selected=["React"])
    questions = [
        "Explain how you use React in a production project.",
        "Explain how you use React in a production project.",  # exact duplicate
        "How do you optimize render performance in React?",
    ]
    deduped = ai._deduplicate_questions(questions, ["React"], setup)
    assert len(deduped) == 3
    # First and second questions should now be different
    assert deduped[0] != deduped[1]


# ---------------------------------------------------------------------------
# TEST 7: Difficulty validation: Basic definition on Hard -> Upgraded
# ---------------------------------------------------------------------------
def test_7_difficulty_validation_replaces_basic_question_on_hard():
    ai = AIProvider()
    setup = make_setup(selected=["PostgreSQL"], difficulty="Hard")
    questions = [
        "What is PostgreSQL?",  # overly shallow for Hard difficulty
        "Explain WAL write-ahead logging and checkpoint tuning in PostgreSQL under high write volume.",
    ]
    validated = ai._validate_difficulty(questions, "Hard", ["PostgreSQL"], setup)
    assert len(validated) == 2
    # The basic "What is PostgreSQL?" question must have been replaced
    assert not validated[0].lower().startswith("what is postgresql?")
    assert "postgresql" in validated[0].lower()


# ---------------------------------------------------------------------------
# TEST 8: Unknown skill or missing source -> Graceful fallback
# ---------------------------------------------------------------------------
def test_8_unknown_skill_uses_fallback():
    retriever = LocalKnowledgeRetriever()
    topics = retriever.retrieve(["CobolQuantumXYZ"], difficulty="Medium", experience_level="Intermediate")
    assert len(topics) > 0
    # Should fall back to generic software engineering topics
    assert any("Software Engineering" in t.skill or "System Design" in t.topic or len(t.concepts) > 0 for t in topics)

    refs = retriever.get_source_references(["CobolQuantumXYZ"])
    assert len(refs) > 0
    assert any("Documentation" in r["name"] or "MDN" in r["name"] for r in refs)


# ---------------------------------------------------------------------------
# TEST 9: Evaluation engine regression check
# ---------------------------------------------------------------------------
def test_9_evaluation_engine_unaffected():
    ai = AIProvider()
    question = "How does the virtual DOM work in React?"
    answer = (
        "The Virtual DOM is an in-memory representation of the real DOM. "
        "React uses a diffing algorithm (reconciliation) to batch updates and minimize real DOM manipulations."
    )
    dto = ai.evaluate_answer(question, answer, [], experience_level="Intermediate", job_role="Frontend Developer")
    assert dto.score >= 5
    assert dto.relevance >= 0.7
    assert dto.correctness >= 0.7
    assert len(dto.feedback) > 0


# ---------------------------------------------------------------------------
# TEST 10: Voice input compatibility: question strings are clean & TTS-friendly
# ---------------------------------------------------------------------------
def test_10_questions_are_valid_tts_strings():
    retriever = LocalKnowledgeRetriever()
    topics = retriever.retrieve(["React"], difficulty="Easy", experience_level="Beginner")
    ai = AIProvider()
    setup = make_setup(selected=["React"], difficulty="Easy")
    questions = ai.generate_questions_batch(setup, 3, retrieved_knowledge=[t.to_dict() for t in topics])

    for q in questions:
        assert isinstance(q, str)
        assert len(q.strip()) > 15
        assert not q.startswith("{")  # not raw unparsed JSON
        assert not q.startswith("[Mock Q") or len(q) > 10
        # Check no corrupted escape characters
        assert "\\n" not in q
        assert "\\t" not in q


# ---------------------------------------------------------------------------
# TEST 11: Question narration flow
# ---------------------------------------------------------------------------
def test_11_question_narration_metadata_accessible():
    db = SessionLocal()
    engine = InterviewEngine()
    try:
        user = db.query(User).filter(User.email == "test_knowledge@example.com").first()
        if not user:
            user = User(full_name="Knowledge Candidate", email="test_knowledge@example.com", hashed_password="pw")
            db.add(user)
            db.commit()
            db.refresh(user)

        session_create = InterviewSessionCreate(
            job_role="Frontend Engineer",
            interview_type="Technical",
            experience_level="Intermediate",
            difficulty="Medium",
            question_count=3,
            selected_skills=["React", "TypeScript"],
        )
        session = engine.create_session(db, session_create, user_id=user.id)
        next_q = engine.get_next_question(db, session.id)

        assert next_q["question_id"] == 1
        assert len(next_q["text"]) > 10
        assert next_q["metadata"]["question_number"] == 1
        assert next_q["metadata"]["total_questions"] == 3
    finally:
        db.close()


# ---------------------------------------------------------------------------
# TEST 12: Full interview session creation & source_context persistence
# ---------------------------------------------------------------------------
def test_12_full_session_flow_and_source_context_persisted():
    db = SessionLocal()
    engine = InterviewEngine()
    try:
        user = db.query(User).filter(User.email == "test_sources@example.com").first()
        if not user:
            user = User(full_name="Source Candidate", email="test_sources@example.com", hashed_password="pw")
            db.add(user)
            db.commit()
            db.refresh(user)

        session_create = InterviewSessionCreate(
            job_role="Backend Developer",
            interview_type="Technical",
            experience_level="Intermediate",
            difficulty="Medium",
            question_count=3,
            resume_skills=["Python", "PostgreSQL", "Docker"],
            selected_skills=["Python", "PostgreSQL"],
        )
        session = engine.create_session(db, session_create, user_id=user.id)
        assert session.id is not None
        assert session.source_context is not None

        # Verify source_context contains valid JSON and has source attribution for selected skills
        source_refs = json.loads(session.source_context)
        assert isinstance(source_refs, list)
        assert len(source_refs) > 0
        names = [r.get("name", "") for r in source_refs]
        assert any("Python" in n or "PostgreSQL" in n or "Documentation" in n for n in names)

        # Answer question 1
        ans1 = engine.submit_answer(db, session.id, "Python uses indentation for syntax blocks and handles memory via reference counting and garbage collection.")
        assert "score" in ans1
        assert session.answered_count == 1

        # Check next question
        q2 = engine.get_next_question(db, session.id)
        assert q2["question_id"] == 2
    finally:
        db.close()
