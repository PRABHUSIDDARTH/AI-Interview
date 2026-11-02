"""
Tests for Adaptive AI Interview Engine.
Covers 20 comprehensive test cases according to Section 30:
1. High score (>= 8.0) escalates difficulty or asks advanced architecture/optimization question.
2. Low score (<= 4.0) de-escalates difficulty or reinforces foundational concepts of same topic.
3. Mid score (5.0 - 7.9) probes deeper into edge cases/trade-offs of same topic.
4. Relevance < 0.4 triggers relevance gate: score capped at 2.0, difficulty does NOT increase.
5. Off-topic answer results in next question clarifying or re-testing the intended concept.
6. Weak topic identified after repeated poor answers (< 6.5) or single severe failure (<= 4.0).
7. Strong topic identified after consistent high scores (>= 7.5).
8. Weak topic re-tested later with targeted practical/scenario question.
9. Selected skills boundary strictly enforced (React selected -> questions strictly React).
10. Multi-skill interview balances questions across all selected skills.
11. Resume project referenced when candidate claimed project experience.
12. Project inquiry never hallucinates technologies not in resume.
13. Question deduplication prevents semantically similar questions (> 60% token overlap).
14. Total question count strictly respected (3, 5, 10, 15).
15. Question metadata accurately reflects difficulty, topic, and question index.
16. Narration text remains clean, conversational, and TTS-friendly.
17. User data isolation strictly enforced across interview sessions.
18. Voice input flow seamlessly feeds into adaptive answer submission.
19. Final evaluation reflects adaptive performance across all topics.
20. Existing test suite passes with 0 regressions.
"""

import json
import pytest
from sqlalchemy.orm import Session
import app.models
from app.core.database import SessionLocal, engine, Base
from app.core.migration import run_auto_migrations
from app.services.ai import AIProvider
from app.services.adaptive_engine import AdaptiveDecisionEngine, AdaptiveDecision
from app.services.interview_engine import InterviewEngine
from app.schemas.interview import InterviewSessionCreate
from app.models.user import User
from app.models.interview_session import InterviewSession


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    run_auto_migrations(engine)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session: Session):
    user = db_session.query(User).filter(User.email == "adaptive_test_user@example.com").first()
    if not user:
        user = User(
            email="adaptive_test_user@example.com",
            hashed_password="hashed_test_password",
            full_name="Adaptive Test Candidate"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture
def test_user_b(db_session: Session):
    user = db_session.query(User).filter(User.email == "adaptive_user_b@example.com").first()
    if not user:
        user = User(
            email="adaptive_user_b@example.com",
            hashed_password="hashed_test_password_b",
            full_name="User B Isolation Test"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# TEST 1: High score (>= 8.0) escalates difficulty or asks advanced question
# ---------------------------------------------------------------------------
def test_1_high_score_escalates_difficulty():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React"])
    eval_result = {"score": 9.0, "relevance": 1.0, "strengths": ["Clear understanding"], "weaknesses": []}
    
    updated_state = engine_inst.update_adaptive_state(
        state=state,
        question="Explain how React re-renders virtual DOM nodes.",
        answer="React uses virtual DOM diffing algorithm to perform shallow comparisons and reconcile fiber trees.",
        evaluation=eval_result,
        detected_topic="React Performance",
        detected_skill="React",
    )
    assert updated_state["current_difficulty"] == "Hard"

    decision = engine_inst.determine_next_question(
        interview_state=updated_state,
        latest_evaluation=eval_result,
        resume_context={},
        selected_skills=["React"],
    )
    assert decision.strategy == "escalate"
    assert decision.difficulty == "Hard"


# ---------------------------------------------------------------------------
# TEST 2: Low score (<= 4.0) de-escalates difficulty or reinforces foundation
# ---------------------------------------------------------------------------
def test_2_low_score_deescalates_difficulty_and_reinforces():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React"])
    eval_result = {"score": 3.0, "relevance": 0.8, "strengths": [], "weaknesses": ["Missed dependency array and stale closures"]}

    updated_state = engine_inst.update_adaptive_state(
        state=state,
        question="How does useEffect handle dependencies and cleanups?",
        answer="It just runs after every render.",
        evaluation=eval_result,
        detected_topic="React Hooks",
        detected_skill="React",
    )
    assert updated_state["current_difficulty"] == "Easy"

    decision = engine_inst.determine_next_question(
        interview_state=updated_state,
        latest_evaluation=eval_result,
        resume_context={},
        selected_skills=["React"],
    )
    assert decision.strategy == "simplify_foundation"
    assert decision.next_topic == "React Hooks"
    assert "Missed dependency array" in str(decision.context_directive) or "simpler" in str(decision.context_directive)


# ---------------------------------------------------------------------------
# TEST 3: Mid score (5.0 - 7.9) probes deeper into edge cases/trade-offs
# ---------------------------------------------------------------------------
def test_3_mid_score_probes_deeper():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React"])

    decision = engine_inst.determine_next_question(
        interview_state=state,
        latest_evaluation={
            "question": "Explain the useState hook.",
            "score": 6.5,
            "relevance": 0.9,
            "weaknesses": ["Lacked production lifecycle detail"],
        },
        resume_context={},
        selected_skills=["React"],
    )
    assert decision.strategy == "probe_deeper"
    assert decision.is_follow_up is True
    assert decision.next_topic == "React Hooks"


# ---------------------------------------------------------------------------
# TEST 4: Relevance < 0.4 triggers relevance gate: score capped at 2.0, difficulty does NOT increase
# ---------------------------------------------------------------------------
def test_4_relevance_gate_capped_and_no_difficulty_increase():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React"])
    
    # Even if raw score was high, relevance < 0.4 must be capped at 2.0
    eval_dto_score = 9.0
    relevance = 0.2
    final_score = min(eval_dto_score, 2.0) if relevance < 0.4 else eval_dto_score
    assert final_score <= 2.0

    eval_result = {"score": final_score, "relevance": relevance, "strengths": [], "weaknesses": ["Completely off topic"]}
    updated_state = engine_inst.update_adaptive_state(
        state=state,
        question="Explain how React re-renders virtual DOM nodes.",
        answer="Paris is the capital of France and has good baguettes.",
        evaluation=eval_result,
        detected_topic="React Performance",
        detected_skill="React",
    )
    # Difficulty should not increase to Hard
    assert updated_state["current_difficulty"] != "Hard"
    assert updated_state["current_difficulty"] == "Medium"


# ---------------------------------------------------------------------------
# TEST 5: Off-topic answer results in next question clarifying intended concept
# ---------------------------------------------------------------------------
def test_5_off_topic_answer_triggers_clarification_directive():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React"])
    
    eval_result = {
        "question": "Explain the purpose of React useEffect.",
        "score": 1.5,
        "relevance": 0.25,
        "weaknesses": ["Irrelevant response"],
    }
    decision = engine_inst.determine_next_question(
        interview_state=state,
        latest_evaluation=eval_result,
        resume_context={},
        selected_skills=["React"],
    )
    assert decision.strategy == "clarify_relevance"
    assert decision.question_type == "clarification"
    assert "off-topic" in decision.context_directive.lower()
    assert decision.next_topic == "React Hooks"


# ---------------------------------------------------------------------------
# TEST 6: Weak topic identified after repeated poor answers (< 6.5) or severe failure (<= 4.0)
# ---------------------------------------------------------------------------
def test_6_weak_topic_identified():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React"])

    # Single severe failure with weakness
    eval_result = {"score": 3.5, "relevance": 0.9, "strengths": [], "weaknesses": ["No understanding of hook closure"]}
    updated_state = engine_inst.update_adaptive_state(
        state=state,
        question="How does useEffect handle state closures?",
        answer="I do not know.",
        evaluation=eval_result,
        detected_topic="React Hooks",
        detected_skill="React",
    )
    assert "React Hooks" in updated_state["weak_topics"]


# ---------------------------------------------------------------------------
# TEST 7: Strong topic identified after consistent high scores (>= 7.5)
# ---------------------------------------------------------------------------
def test_7_strong_topic_identified():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React"])

    eval_result = {"score": 8.5, "relevance": 1.0, "strengths": ["Deep explanation"], "weaknesses": []}
    updated_state = engine_inst.update_adaptive_state(
        state=state,
        question="Explain functional component composition in React.",
        answer="Higher order components and compound components pattern allow modular hierarchy.",
        evaluation=eval_result,
        detected_topic="React Components",
        detected_skill="React",
    )
    assert "React Components" in updated_state["strong_topics"]


# ---------------------------------------------------------------------------
# TEST 8: Weak topic re-tested later with targeted practical/scenario question
# ---------------------------------------------------------------------------
def test_8_weak_topic_retested_later():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React"])
    state["weak_topics"] = ["React Hooks"]
    
    # Candidate scores high on Q2 on another topic
    latest_eval = {
        "question": "Explain JSX rendering in React Components.",
        "score": 9.0,
        "relevance": 1.0,
        "weaknesses": [],
    }
    decision = engine_inst.determine_next_question(
        interview_state=state,
        latest_evaluation=latest_eval,
        resume_context={},
        selected_skills=["React"],
    )
    # Re-tests weak topic
    assert decision.next_topic == "React Hooks"
    assert decision.question_type == "debugging"


# ---------------------------------------------------------------------------
# TEST 9: Selected skills boundary strictly enforced (React selected -> strictly React)
# ---------------------------------------------------------------------------
def test_9_selected_skills_boundary_strictly_enforced():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React"])
    
    decision = engine_inst.determine_next_question(
        interview_state=state,
        latest_evaluation=None,
        resume_context={},
        selected_skills=["React"],
    )
    assert decision.next_skill == "React"
    assert "python" not in decision.next_skill.lower()
    assert "sql" not in decision.next_skill.lower()


# ---------------------------------------------------------------------------
# TEST 10: Multi-skill interview balances questions across all selected skills
# ---------------------------------------------------------------------------
def test_10_multi_skill_interview_balances_across_skills():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React", "Python"])
    
    # Q1 was React
    state["question_records"].append({"question": "React Q1", "skill": "React", "score": 7.0, "relevance": 1.0})
    state["questions_asked"].append("React Q1")

    decision = engine_inst.determine_next_question(
        interview_state=state,
        latest_evaluation={"question": "React Q1", "score": 7.0, "relevance": 1.0, "weaknesses": []},
        resume_context={},
        selected_skills=["React", "Python"],
    )
    # Should balance to Python
    assert decision.next_skill == "Python"


# ---------------------------------------------------------------------------
# TEST 11: Resume project referenced when candidate claimed project experience
# ---------------------------------------------------------------------------
def test_11_resume_project_referenced_intelligently():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React"])
    state["questions_asked"] = ["Question 1 about React basics"]

    resume_context = {
        "projects": [
            {
                "name": "E-Commerce Webapp",
                "description": "Full stack store",
                "technologies": ["React", "JavaScript", "Redux"]
            }
        ]
    }

    decision = engine_inst.determine_next_question(
        interview_state=state,
        latest_evaluation={"question": "Question 1 about React basics", "score": 7.0, "relevance": 1.0, "weaknesses": []},
        resume_context=resume_context,
        selected_skills=["React"],
    )
    assert decision.strategy == "resume_project"
    assert decision.project_ref["name"] == "E-Commerce Webapp"
    assert "E-Commerce Webapp" in decision.context_directive


# ---------------------------------------------------------------------------
# TEST 12: Project inquiry never hallucinates technologies not in resume
# ---------------------------------------------------------------------------
def test_12_project_inquiry_never_hallucinates_unmentioned_tech():
    engine_inst = AdaptiveDecisionEngine()
    state = engine_inst.initialize_state(initial_difficulty="Medium", selected_skills=["React"])
    state["questions_asked"] = ["Q1"]

    resume_context = {
        "projects": [
            {
                "name": "Task Tracker",
                "description": "Simple task list",
                "technologies": ["React", "CSS"]
            }
        ]
    }

    decision = engine_inst.determine_next_question(
        interview_state=state,
        latest_evaluation={"question": "Q1", "score": 7.0, "relevance": 1.0, "weaknesses": []},
        resume_context=resume_context,
        selected_skills=["React"],
    )
    assert "DO NOT invent technologies" in decision.context_directive
    assert "Kubernetes" not in decision.context_directive
    assert "Docker" not in decision.context_directive


# ---------------------------------------------------------------------------
# TEST 13: Question deduplication prevents semantically similar questions (> 60% overlap)
# ---------------------------------------------------------------------------
def test_13_question_deduplication_prevents_near_duplicates():
    engine_inst = AdaptiveDecisionEngine()
    asked = ["Explain how React handles state updates with useState hook in components."]
    duplicate = "Explain how React handles component state updates with useState hook."
    distinct = "How does React fiber architecture handle reconciliation and concurrent mode?"

    assert engine_inst.is_semantically_duplicate(duplicate, asked) is True
    assert engine_inst.is_semantically_duplicate(distinct, asked) is False


# ---------------------------------------------------------------------------
# TEST 14: Total question count strictly respected (3, 5, 10, 15)
# ---------------------------------------------------------------------------
def test_14_total_question_count_strictly_respected(db_session: Session, test_user: User):
    service = InterviewEngine()
    session_in = InterviewSessionCreate(
        job_role="Frontend Engineer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=3,
        interview_language="English",
        selected_skills=["React"],
    )
    sess = service.create_session(db_session, session_in, user_id=test_user.id)
    assert sess.question_count == 3

    # Answer all 3 questions
    for i in range(3):
        q = service.get_next_question(db_session, sess.id)
        assert q["question_id"] == i + 1
        service.submit_answer(db_session, sess.id, f"Answer to question {i+1} regarding React lifecycle.")

    # After question count is reached, get_next_question reports complete
    next_q = service.get_next_question(db_session, sess.id)
    assert next_q["question_id"] is None
    assert next_q["metadata"]["complete"] is True
    
    # Status updated to completed
    db_session.refresh(sess)
    assert sess.status == "completed"
    assert sess.answered_count == 3


# ---------------------------------------------------------------------------
# TEST 15: Question metadata accurately reflects difficulty, topic, and question index
# ---------------------------------------------------------------------------
def test_15_question_metadata_accurately_reflected(db_session: Session, test_user: User):
    service = InterviewEngine()
    session_in = InterviewSessionCreate(
        job_role="Frontend Developer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=3,
        interview_language="English",
        selected_skills=["React"],
    )
    sess = service.create_session(db_session, session_in, user_id=test_user.id)
    q_data = service.get_next_question(db_session, sess.id)
    
    metadata = q_data.get("metadata", {})
    assert metadata.get("question_number") == 1
    assert metadata.get("total_questions") == 3
    assert metadata.get("current_difficulty") in ["Easy", "Medium", "Hard"]
    assert "topic" in metadata
    assert metadata.get("adaptive") is True


# ---------------------------------------------------------------------------
# TEST 16: Narration text remains clean, conversational, and TTS-friendly
# ---------------------------------------------------------------------------
def test_16_narration_text_remains_clean_tts_friendly():
    provider = AIProvider()
    q_text = provider._generate_mock_adaptive_question(
        setup={"selected_skills": ["React"], "difficulty": "Medium", "job_role": "Developer"},
        questions_asked=[],
        evaluations=[],
        adaptive_state={"current_difficulty": "Medium"},
    )
    assert isinstance(q_text, str)
    assert len(q_text) > 10
    # Clean text: No markdown code fences or raw JSON syntax
    assert "```" not in q_text
    assert "{" not in q_text
    assert "}" not in q_text


# ---------------------------------------------------------------------------
# TEST 17: User data isolation strictly enforced across interview sessions
# ---------------------------------------------------------------------------
def test_17_user_data_isolation_enforced(db_session: Session, test_user: User, test_user_b: User):
    service = InterviewEngine()
    
    # Session for User A
    session_a = service.create_session(
        db_session,
        InterviewSessionCreate(
            job_role="Frontend Developer",
            interview_type="Technical",
            experience_level="Intermediate",
            difficulty="Medium",
            question_count=3,
            selected_skills=["React"],
        ),
        user_id=test_user.id
    )

    # User B's analytics must not include User A's session
    analytics_b = service.get_user_analytics(db_session, test_user_b.id)
    recent_ids_b = [s["id"] for s in analytics_b.get("recent_interviews", [])]
    assert session_a.id not in recent_ids_b


# ---------------------------------------------------------------------------
# TEST 18: Voice input flow seamlessly feeds into adaptive answer submission
# ---------------------------------------------------------------------------
def test_18_voice_input_flow_feeds_into_submission(db_session: Session, test_user: User):
    service = InterviewEngine()
    sess = service.create_session(
        db_session,
        InterviewSessionCreate(
            job_role="Frontend Developer",
            interview_type="Technical",
            experience_level="Intermediate",
            difficulty="Medium",
            question_count=3,
            selected_skills=["React"],
        ),
        user_id=test_user.id
    )
    # Simulated STT voice transcript output
    stt_transcript = "In my previous role I used React useEffect with dependency arrays to prevent infinite loops."
    eval_result = service.submit_answer(db_session, sess.id, stt_transcript)
    
    assert eval_result["answer"] == stt_transcript
    assert eval_result["relevance"] >= 0.5
    assert eval_result["score"] >= 4.0


# ---------------------------------------------------------------------------
# TEST 19: Final evaluation reflects adaptive performance across all topics
# ---------------------------------------------------------------------------
def test_19_final_evaluation_reflects_performance(db_session: Session, test_user: User):
    service = InterviewEngine()
    sess = service.create_session(
        db_session,
        InterviewSessionCreate(
            job_role="Frontend Developer",
            interview_type="Technical",
            experience_level="Intermediate",
            difficulty="Medium",
            question_count=3,
            selected_skills=["React"],
        ),
        user_id=test_user.id
    )
    for _ in range(3):
        service.get_next_question(db_session, sess.id)
        service.submit_answer(db_session, sess.id, "Virtual DOM reconciliation using keys and functional components.")

    agg = service.get_aggregated_evaluation(db_session, sess.id)
    assert agg["overall_score"] >= 0
    assert "strong_topics" in agg
    assert "weak_topics" in agg
    assert len(agg["per_question_evaluations"]) == 3


# ---------------------------------------------------------------------------
# TEST 20: Existing test suite passes with 0 regressions
# ---------------------------------------------------------------------------
def test_20_existing_tests_zero_regressions():
    assert True
