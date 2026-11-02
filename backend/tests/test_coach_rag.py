import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.api.deps import get_db
from app.main import app
from app.models.user import User
from app.models.interview_session import InterviewSession
from app.core.security import create_access_token, get_password_hash
from app.services.adaptive_engine import AdaptiveDecisionEngine
from app.services.resume_parser import normalize_skill

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_coach_rag.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


client = TestClient(app)


# ---------------------------------------------------------------------------
# TEST 1: User A requests coach summary. Expected: Only User A data.
# ---------------------------------------------------------------------------

def test_1_user_a_requests_coach_summary_only_user_a_data():
    """TEST 1: User A requests coach summary. Expected: Only User A data."""
    db = TestingSessionLocal()

    user_a = User(
        email="user_a1@example.com",
        hashed_password=get_password_hash("passwordA123"),
        full_name="User A (React Dev)",
        is_active=True,
    )
    user_b = User(
        email="user_b1@example.com",
        hashed_password=get_password_hash("passwordB123"),
        full_name="User B (Spring Dev)",
        is_active=True,
    )
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    # User A has 2 React interview sessions (weak in React Hooks)
    evals_a1 = [
        {
            "question": "How do useEffect dependencies work?",
            "answer": "It re-renders.",
            "score": 4.0,
            "correctness": 0.4,
            "relevance": 0.5,
            "technical_depth": 0.3,
            "communication_quality": 0.5,
            "strengths": [],
            "weaknesses": ["React Hooks", "useEffect cleanup"],
            "feedback": "Needs improvement on effect dependency array.",
        }
    ]
    evals_a2 = [
        {
            "question": "Explain custom hooks in React.",
            "answer": "They are regular JS functions.",
            "score": 5.0,
            "correctness": 0.5,
            "relevance": 0.6,
            "strengths": [],
            "weaknesses": ["React Hooks"],
            "feedback": "Lacks detail on hook composition.",
        }
    ]
    sess_a1 = InterviewSession(
        user_id=user_a.id,
        job_role="React Developer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React", "Python"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps(["How do useEffect dependencies work?"]),
        evaluations=json.dumps(evals_a1),
    )
    sess_a2 = InterviewSession(
        user_id=user_a.id,
        job_role="React Developer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React", "Python"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps(["Explain custom hooks in React."]),
        evaluations=json.dumps(evals_a2),
    )

    # User B has Spring Security session
    evals_b = [
        {
            "question": "Explain Spring Security filter chains.",
            "answer": "Filters intercept requests.",
            "score": 3.0,
            "weaknesses": ["Spring Security"],
            "feedback": "Lacks depth on SecurityFilterChain.",
        }
    ]
    sess_b = InterviewSession(
        user_id=user_b.id,
        job_role="Java Backend Engineer",
        interview_type="Technical",
        experience_level="Advanced",
        difficulty="Hard",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["Java", "Spring"]),
        selected_skills=json.dumps(["Spring"]),
        questions=json.dumps(["Explain Spring Security filter chains."]),
        evaluations=json.dumps(evals_b),
    )
    db.add_all([sess_a1, sess_a2, sess_b])
    db.commit()

    token_a = create_access_token(user_a.id)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res_a = client.get("/api/v1/coach/summary", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()

    # Verify only User A data is present
    assert data_a["has_enough_data"] is True
    assert data_a["overall_score"] == 4.5
    assert any("React Hooks" in w["topic"] for w in data_a["weak_topics"])
    # Must NEVER include User B's Spring Security or Java
    assert not any("Spring" in w["topic"] or "Java" in w["topic"] for w in data_a["weak_topics"])
    assert "Spring" not in data_a["summary"]
    db.close()


# ---------------------------------------------------------------------------
# TEST 2: User B requests coach summary. Expected: Only User B data.
# ---------------------------------------------------------------------------

def test_2_user_b_requests_coach_summary_only_user_b_data():
    """TEST 2: User B requests coach summary. Expected: Only User B data."""
    db = TestingSessionLocal()

    user_a = User(email="user_a2@example.com", hashed_password=get_password_hash("pass"), full_name="User A", is_active=True)
    user_b = User(email="user_b2@example.com", hashed_password=get_password_hash("pass"), full_name="User B", is_active=True)
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    # User A session (React)
    sess_a = InterviewSession(
        user_id=user_a.id,
        job_role="React Developer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React"]),
        evaluations=json.dumps([{"question": "React Q", "score": 4.0, "weaknesses": ["React Hooks"]}]),
    )
    # User B session (Spring Security)
    sess_b = InterviewSession(
        user_id=user_b.id,
        job_role="Java Engineer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["Java", "Spring"]),
        selected_skills=json.dumps(["Spring"]),
        questions=json.dumps(["Configure Spring Security filter chain."]),
        evaluations=json.dumps([{"question": "Configure Spring Security filter chain.", "score": 3.5, "weaknesses": ["Spring Security"]}]),
    )
    db.add_all([sess_a, sess_b])
    db.commit()

    token_b = create_access_token(user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    res_b = client.get("/api/v1/coach/summary", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()

    # Verify only User B data
    assert data_b["has_enough_data"] is True
    assert data_b["overall_score"] == 3.5
    assert any("Spring Security" in w["topic"] for w in data_b["weak_topics"])
    # Must NEVER contain User A's React data
    assert not any("React" in w["topic"] for w in data_b["weak_topics"])
    assert "React" not in data_b["summary"]
    db.close()


# ---------------------------------------------------------------------------
# TEST 3: Cross-user access attempt. Expected: Blocked.
# ---------------------------------------------------------------------------

def test_3_cross_user_access_attempt_blocked():
    """TEST 3: Cross-user access attempt. Expected: Blocked."""
    db = TestingSessionLocal()
    user_a = User(email="user_a3@example.com", hashed_password=get_password_hash("pass"), is_active=True)
    user_b = User(email="user_b3@example.com", hashed_password=get_password_hash("pass"), is_active=True)
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    sess_b = InterviewSession(
        user_id=user_b.id,
        job_role="Secret Agent",
        interview_type="Technical",
        experience_level="Senior",
        difficulty="Hard",
        question_count=1,
        answered_count=1,
        status="completed",
        questions=json.dumps(["User B Classified Question"]),
        evaluations=json.dumps([{"question": "User B Classified Question", "answer": "classified", "score": 10.0}]),
    )
    db.add(sess_b)
    db.commit()
    db.refresh(sess_b)

    token_a = create_access_token(user_a.id)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User A tries to GET User B's interview by session_id -> 404
    r1 = client.get(f"/api/v1/interviews/{sess_b.id}", headers=headers_a)
    assert r1.status_code == 404

    # User A tries to GET User B's evaluation by session_id -> 404
    r2 = client.get(f"/api/v1/interviews/{sess_b.id}/evaluation", headers=headers_a)
    assert r2.status_code == 404

    # User A checks coach summary -> 0 completed sessions, 0.0 overall score
    r3 = client.get("/api/v1/coach/summary", headers=headers_a)
    assert r3.status_code == 200
    assert r3.json()["has_enough_data"] is False
    assert r3.json()["overall_score"] == 0.0
    db.close()


# ---------------------------------------------------------------------------
# TEST 4: No interview history. Expected: No fabricated insights.
# ---------------------------------------------------------------------------

def test_4_no_interview_history_no_fabricated_insights():
    """TEST 4: No interview history. Expected: No fabricated insights."""
    db = TestingSessionLocal()
    user = User(email="user_cold4@example.com", hashed_password=get_password_hash("pass"), full_name="New Candidate", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    res = client.get("/api/v1/coach/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["has_enough_data"] is False
    assert len(data["weak_topics"]) == 0
    assert len(data["strong_topics"]) == 0
    assert data["overall_score"] == 0.0
    assert "first interview" in data["summary"].lower() or "not enough" in data["summary"].lower()
    db.close()


# ---------------------------------------------------------------------------
# TEST 5: One interview. Expected: Preliminary analysis only.
# ---------------------------------------------------------------------------

def test_5_one_interview_preliminary_analysis_only():
    """TEST 5: One interview. Expected: Preliminary analysis only."""
    db = TestingSessionLocal()
    user = User(email="user_single_interview@example.com", hashed_password=get_password_hash("pass"), full_name="Single Session Candidate", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    sess = InterviewSession(
        user_id=user.id,
        job_role="Frontend Engineer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps(["Explain useState and useEffect."]),
        evaluations=json.dumps([{"question": "Explain useState and useEffect.", "score": 7.0, "strengths": ["State basics"]}]),
    )
    db.add(sess)
    db.commit()

    token = create_access_token(user.id)
    res = client.get("/api/v1/coach/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["has_enough_data"] is True
    assert data["is_preliminary"] is True
    assert "preliminary" in data["summary"].lower()
    assert data["improvement_trend"]["direction"] == "baseline"
    db.close()


# ---------------------------------------------------------------------------
# TEST 6: Repeated weak topic. Expected: Weak topic detected.
# ---------------------------------------------------------------------------

def test_6_repeated_weak_topic_detected():
    """TEST 6: Repeated weak topic. Expected: Weak topic detected."""
    db = TestingSessionLocal()
    user = User(email="user_weak_hooks6@example.com", hashed_password=get_password_hash("pass"), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    s1 = InterviewSession(
        user_id=user.id,
        job_role="Frontend Dev",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps(["Explain useState and useEffect hooks."]),
        evaluations=json.dumps([{"question": "Explain useState and useEffect hooks.", "score": 4.0, "weaknesses": ["React Hooks"]}]),
    )
    s2 = InterviewSession(
        user_id=user.id,
        job_role="Frontend Dev",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps(["How do you handle cleanup in useEffect?"]),
        evaluations=json.dumps([{"question": "How do you handle cleanup in useEffect?", "score": 5.0, "weaknesses": ["React Hooks", "useEffect cleanup"]}]),
    )
    s3 = InterviewSession(
        user_id=user.id,
        job_role="Frontend Dev",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps(["How to avoid infinite loops in useEffect?"]),
        evaluations=json.dumps([{"question": "How to avoid infinite loops in useEffect?", "score": 5.0, "weaknesses": ["React Hooks"]}]),
    )
    db.add_all([s1, s2, s3])
    db.commit()

    token = create_access_token(user.id)
    res = client.get("/api/v1/coach/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    weak_topics = [w["topic"] for w in data["weak_topics"]]
    assert any("React Hooks" in t for t in weak_topics)
    assert data["weak_topics"][0]["score"] <= 5.5
    db.close()


# ---------------------------------------------------------------------------
# TEST 7: Repeated strong topic. Expected: Strong topic detected.
# ---------------------------------------------------------------------------

def test_7_repeated_strong_topic_detected():
    """TEST 7: Repeated strong topic. Expected: Strong topic detected."""
    db = TestingSessionLocal()
    user = User(email="user_strong_components7@example.com", hashed_password=get_password_hash("pass"), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    s1 = InterviewSession(
        user_id=user.id,
        job_role="Frontend Dev",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=2,
        answered_count=2,
        status="completed",
        resume_skills=json.dumps(["React", "JavaScript"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps(["Explain React Components and JSX.", "Explain props and data flow."]),
        evaluations=json.dumps([
            {"question": "Explain React Components and JSX.", "score": 8.8, "strengths": ["Clean JSX architecture"]},
            {"question": "Explain props and data flow.", "score": 9.0, "strengths": ["One-way data flow mastery"]},
        ]),
    )
    db.add(s1)
    db.commit()

    token = create_access_token(user.id)
    res = client.get("/api/v1/coach/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    strong_topics = [s["topic"] for s in data["strong_topics"]]
    assert any("React Components" in t for t in strong_topics)
    assert data["strongest_skill"]["skill"] == "React"
    assert data["strongest_skill"]["score"] >= 8.5
    db.close()


# ---------------------------------------------------------------------------
# TEST 8: Improving interview scores. Expected: Improvement trend detected.
# ---------------------------------------------------------------------------

def test_8_improving_interview_scores_trend_detected():
    """TEST 8: Improving interview scores. Expected: Improvement trend detected."""
    db = TestingSessionLocal()
    user = User(email="user_improving8@example.com", hashed_password=get_password_hash("pass"), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    scores = [6.2, 7.1, 7.8]
    sessions = []
    for idx, sc in enumerate(scores, start=1):
        s = InterviewSession(
            user_id=user.id,
            job_role="Fullstack Engineer",
            interview_type="Technical",
            experience_level="Intermediate",
            difficulty="Medium",
            question_count=1,
            answered_count=1,
            status="completed",
            resume_skills=json.dumps(["Python"]),
            selected_skills=json.dumps(["Python"]),
            questions=json.dumps([f"Question {idx}"]),
            evaluations=json.dumps([{"question": f"Question {idx}", "score": sc}]),
        )
        sessions.append(s)
    db.add_all(sessions)
    db.commit()

    token = create_access_token(user.id)
    res = client.get("/api/v1/coach/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    trend = res.json()["improvement_trend"]

    assert trend["direction"] == "improving"
    assert trend["delta"] > 0
    assert "improved" in trend["description"].lower()
    db.close()


# ---------------------------------------------------------------------------
# TEST 9: Declining interview scores. Expected: Decline detected.
# ---------------------------------------------------------------------------

def test_9_declining_interview_scores_decline_detected():
    """TEST 9: Declining interview scores. Expected: Decline detected."""
    db = TestingSessionLocal()
    user = User(email="user_declining9@example.com", hashed_password=get_password_hash("pass"), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    scores = [8.5, 6.5, 5.0]
    sessions = []
    for idx, sc in enumerate(scores, start=1):
        s = InterviewSession(
            user_id=user.id,
            job_role="Backend Engineer",
            interview_type="Technical",
            experience_level="Intermediate",
            difficulty="Medium",
            question_count=1,
            answered_count=1,
            status="completed",
            resume_skills=json.dumps(["Python"]),
            selected_skills=json.dumps(["Python"]),
            questions=json.dumps([f"Question {idx}"]),
            evaluations=json.dumps([{"question": f"Question {idx}", "score": sc}]),
        )
        sessions.append(s)
    db.add_all(sessions)
    db.commit()

    token = create_access_token(user.id)
    res = client.get("/api/v1/coach/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    trend = res.json()["improvement_trend"]

    assert trend["direction"] == "declining"
    assert trend["delta"] < 0
    assert "declined" in trend["description"].lower()
    db.close()


# ---------------------------------------------------------------------------
# TEST 10: Coach recommendation. Expected: Matches actual weakness.
# ---------------------------------------------------------------------------

def test_10_coach_recommendation_matches_actual_weakness():
    """TEST 10: Coach recommendation. Expected: Matches actual weakness."""
    db = TestingSessionLocal()
    user = User(email="user_rec10@example.com", hashed_password=get_password_hash("pass"), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    s1 = InterviewSession(
        user_id=user.id,
        job_role="Frontend Engineer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps(["Why do useEffect dependencies cause loops?"]),
        evaluations=json.dumps([{"question": "Why do useEffect dependencies cause loops?", "score": 4.0, "weaknesses": ["React Hooks"]}]),
    )
    db.add(s1)
    db.commit()

    token = create_access_token(user.id)
    res = client.get("/api/v1/coach/recommendations", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    recs = res.json()

    assert len(recs) > 0
    assert any("React Hooks" in r["topic"] for r in recs)
    assert len(recs[0]["recommendations"]) > 0
    assert any("useEffect" in act or "hook" in act.lower() or "state" in act.lower() for act in recs[0]["recommendations"])
    db.close()


# ---------------------------------------------------------------------------
# TEST 11: Practice question. Expected: Targets weak topic.
# ---------------------------------------------------------------------------

def test_11_practice_question_targets_weak_topic():
    """TEST 11: Practice question. Expected: Targets weak topic."""
    db = TestingSessionLocal()
    user = User(email="user_pq11@example.com", hashed_password=get_password_hash("pass"), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    sess = InterviewSession(
        user_id=user.id,
        job_role="React Engineer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps(["Explain useEffect"]),
        evaluations=json.dumps([{"question": "Explain useEffect", "score": 4.0, "weaknesses": ["React Hooks"]}]),
    )
    db.add(sess)
    db.commit()

    token = create_access_token(user.id)
    res = client.post("/api/v1/coach/practice-question", json={}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert "React Hooks" in data["topic"]
    assert "React" in data["skill"]
    assert len(data["question"]) > 15
    db.close()


# ---------------------------------------------------------------------------
# TEST 12: Practice question duplication. Expected: No duplicate.
# ---------------------------------------------------------------------------

def test_12_practice_question_duplication_no_duplicate():
    """TEST 12: Practice question duplication. Expected: No duplicate."""
    db = TestingSessionLocal()
    user = User(email="user_dedup12@example.com", hashed_password=get_password_hash("pass"), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    previous_question = "Explain useEffect cleanup function and why it is necessary."
    sess = InterviewSession(
        user_id=user.id,
        job_role="Frontend Developer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps([previous_question]),
        evaluations=json.dumps([{"question": previous_question, "score": 4.0, "weaknesses": ["React Hooks"]}]),
    )
    db.add(sess)
    db.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/coach/practice-question", json={}, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["question"].strip().lower() != previous_question.strip().lower()
    assert len(data["question"]) > 10
    db.close()


# ---------------------------------------------------------------------------
# TEST 13: Recommended interview button. Expected: Uses existing interview flow.
# ---------------------------------------------------------------------------

def test_13_recommended_interview_uses_existing_interview_flow():
    """TEST 13: Recommended interview button. Expected: Uses existing interview flow."""
    db = TestingSessionLocal()
    user = User(email="user_flow13@example.com", hashed_password=get_password_hash("pass"), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    sess = InterviewSession(
        user_id=user.id,
        job_role="React Developer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React", "TypeScript"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps(["React Hooks question"]),
        evaluations=json.dumps([{"question": "React Hooks question", "score": 4.5, "weaknesses": ["React Hooks"]}]),
    )
    db.add(sess)
    db.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/coach/summary", headers=headers)
    assert res.status_code == 200
    rec = res.json()["recommended_interview"]

    assert rec is not None
    assert rec["job_role"] == "React Developer"
    assert rec["interview_type"] == "Technical"
    assert rec["difficulty"] == "Medium"
    assert "React" in rec["selected_skills"]
    assert "React Hooks" in rec["focus_topic"]

    form_data = {
        "interview_type": rec["interview_type"],
        "job_role": rec["job_role"],
        "experience_level": rec["experience_level"],
        "difficulty": rec["difficulty"],
        "question_count": 3,
        "selected_skills": json.dumps(rec["selected_skills"]),
        "resume_skills": json.dumps(["React", "TypeScript"]),
    }
    start_res = client.post("/api/v1/interviews/start", data=form_data, headers=headers)
    assert start_res.status_code == 201
    assert "session_id" in start_res.json()
    assert "question" in start_res.json()
    db.close()


# ---------------------------------------------------------------------------
# TEST 14: Resume context. Expected: Coach uses actual resume information.
# ---------------------------------------------------------------------------

def test_14_resume_context_uses_actual_resume_information():
    """TEST 14: Resume context. Expected: Coach uses actual resume information."""
    db = TestingSessionLocal()
    user = User(email="user_resume14@example.com", hashed_password=get_password_hash("pass"), full_name="Resume Candidate", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    resume_profile = {
        "skills": ["React", "Python", "FastAPI", "PostgreSQL"],
        "projects": [{"name": "AI Interview Platform", "technologies": ["FastAPI", "React"]}],
    }
    sess = InterviewSession(
        user_id=user.id,
        job_role="Fullstack Dev",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(resume_profile["skills"]),
        resume_profile=json.dumps(resume_profile),
        questions=json.dumps(["Explain FastAPI dependency injection"]),
        evaluations=json.dumps([{"question": "Explain FastAPI dependency injection", "score": 8.0}]),
    )
    db.add(sess)
    db.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Summary checks
    res = client.get("/api/v1/coach/summary", headers=headers)
    assert res.status_code == 200
    skills = res.json()["candidate_resume_skills"]
    assert "React" in skills
    assert "FastAPI" in skills

    # Chat inquiry on resume
    chat_res = client.post("/api/v1/coach/chat", json={"message": "What skills are on my resume?"}, headers=headers)
    assert chat_res.status_code == 200
    reply = chat_res.json()["response"]
    assert "React" in reply
    assert "Python" in reply
    db.close()


# ---------------------------------------------------------------------------
# TEST 15: Unsupported resume claim. Expected: No hallucination.
# ---------------------------------------------------------------------------

def test_15_unsupported_resume_claim_no_hallucination():
    """TEST 15: Unsupported resume claim. Expected: No hallucination."""
    db = TestingSessionLocal()
    user = User(email="user_nohallucinate15@example.com", hashed_password=get_password_hash("pass"), full_name="Strict Dev", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    sess = InterviewSession(
        user_id=user.id,
        job_role="Frontend Engineer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        resume_skills=json.dumps(["React", "JavaScript"]),
        questions=json.dumps(["Explain React Components"]),
        evaluations=json.dumps([{"question": "Explain React Components", "score": 8.5}]),
    )
    db.add(sess)
    db.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Ask about Rust (not in candidate's resume or interviews)
    r = client.post("/api/v1/coach/chat", json={"message": "Do I have experience with Rust?"}, headers=headers)
    assert r.status_code == 200
    reply = r.json()["response"]
    # Must not hallucinate that user knows Rust
    assert "not listed" in reply.lower() or "not in" in reply.lower() or "verified candidate profile" in reply.lower()
    db.close()


# ---------------------------------------------------------------------------
# TEST 16: Existing adaptive interview tests pass.
# ---------------------------------------------------------------------------

def test_16_existing_adaptive_interview_tests_pass():
    """TEST 16: Existing adaptive interview engine decisions and state progression."""
    engine = AdaptiveDecisionEngine()
    state = engine.initialize_state(initial_difficulty="Medium", selected_skills=["React"])

    q1 = "Explain React component lifecycle and virtual DOM diffing."
    a1 = "Virtual DOM uses tree diffing algorithm to minimize browser reflows."
    eval_high = {
        "score": 8.5,
        "relevance": 0.9,
        "strengths": ["Clear DOM diffing concept"],
        "weaknesses": [],
    }
    topic1, skill1 = engine.classify_question_topic(q1, a1, candidate_skills=["React"])
    state1 = engine.update_adaptive_state(state, q1, a1, eval_high, topic1, skill1)

    # High score -> difficulty must have escalated to Hard
    assert state1["current_difficulty"] == "Hard"
    # Strong topic should be detected
    assert topic1 in state1["strong_topics"]

    # 2. Low score adaptation -> difficulty de-escalates back to Medium
    q2 = "How do useEffect dependencies avoid stale closure bugs?"
    a2 = "Not sure."
    eval_low = {
        "score": 3.0,
        "relevance": 0.7,
        "strengths": [],
        "weaknesses": ["React Hooks"],
    }
    topic2, skill2 = engine.classify_question_topic(q2, a2, candidate_skills=["React"])
    state2 = engine.update_adaptive_state(state1, q2, a2, eval_low, topic2, skill2)
    assert state2["current_difficulty"] == "Medium"
    assert topic2 in state2["weak_topics"]


# ---------------------------------------------------------------------------
# TEST 17: Existing evaluation tests pass.
# ---------------------------------------------------------------------------

def test_17_existing_evaluation_tests_pass():
    """TEST 17: Verify evaluation scores, technical depth, and ground feedback."""
    db = TestingSessionLocal()
    user = User(email="test_eval17@example.com", hashed_password=get_password_hash("pass"), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    sess = InterviewSession(
        user_id=user.id,
        job_role="Frontend Engineer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=3,
        answered_count=1,
        status="completed",
        questions=json.dumps(["Explain virtual DOM in React."]),
        evaluations=json.dumps([{
            "question": "Explain virtual DOM in React.",
            "answer": "Virtual DOM is a lightweight JavaScript representation of real DOM.",
            "score": 8.0,
            "correctness": 0.85,
            "relevance": 0.90,
            "technical_depth": 0.80,
            "communication_quality": 0.85,
            "feedback": "Great concise explanation.",
            "strengths": ["Clear DOM diffing concept"],
            "weaknesses": [],
        }]),
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    r_eval = client.get(f"/api/v1/interviews/{sess.id}/evaluation", headers=headers)
    assert r_eval.status_code == 200
    eval_data = r_eval.json()
    assert eval_data["overall_score"] == 8.0
    assert len(eval_data["per_question_evaluations"]) == 1
    db.close()


# ---------------------------------------------------------------------------
# TEST 18: Existing resume tests pass.
# ---------------------------------------------------------------------------

def test_18_existing_resume_tests_pass():
    """TEST 18: Verify resume skill extraction and normalization."""
    assert normalize_skill("react.js") == "React"
    assert normalize_skill("python3") == "Python"
    assert normalize_skill("postgresql") == "PostgreSQL"
    assert normalize_skill("k8s") == "Kubernetes"


# ---------------------------------------------------------------------------
# TEST 19: Existing authentication tests pass.
# ---------------------------------------------------------------------------

def test_19_existing_authentication_tests_pass():
    """TEST 19: Existing authentication tests pass (register, login, JWT validation, 401)."""
    email = "test_auth_pass_19@example.com"
    pwd = "ValidPass123!"

    # 1. Registration
    r_reg = client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "full_name": "Auth Tester"})
    assert r_reg.status_code == 201
    assert r_reg.json()["email"] == email

    # 2. Login
    r_login = client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
    assert r_login.status_code == 200
    token = r_login.json()["access_token"]
    assert len(token) > 20

    # 3. Authenticated endpoint allows access
    r_me = client.get("/api/v1/coach/summary", headers={"Authorization": f"Bearer {token}"})
    assert r_me.status_code == 200

    # 4. Unauthenticated endpoint rejected with 401
    r_unauth = client.get("/api/v1/coach/summary")
    assert r_unauth.status_code == 401


# ---------------------------------------------------------------------------
# TEST 20: Full regression suite pass.
# ---------------------------------------------------------------------------

def test_20_full_regression_suite_pass():
    """TEST 20: Full regression suite covering topics, chat, practice, and session lifecycle."""
    db = TestingSessionLocal()
    user = User(email="test_regression20@example.com", hashed_password=get_password_hash("pass"), full_name="Full Regression User", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    sess = InterviewSession(
        user_id=user.id,
        job_role="React Developer",
        interview_type="Technical",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=2,
        answered_count=2,
        status="completed",
        resume_skills=json.dumps(["React"]),
        selected_skills=json.dumps(["React"]),
        questions=json.dumps(["Explain React Components", "Explain React Hooks pitfalls"]),
        evaluations=json.dumps([
            {"question": "Explain React Components", "score": 9.0, "strengths": ["Clean modular component design"]},
            {"question": "Explain React Hooks pitfalls", "score": 4.5, "weaknesses": ["React Hooks", "useEffect dependency loop"]},
        ]),
    )
    db.add(sess)
    db.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Summary
    r_sum = client.get("/api/v1/coach/summary", headers=headers)
    assert r_sum.status_code == 200
    assert r_sum.json()["overall_score"] == 6.8

    # 2. Topics
    r_topics = client.get("/api/v1/coach/topics", headers=headers)
    assert r_topics.status_code == 200
    assert len(r_topics.json()) >= 2

    # 3. Weak Topics
    r_weak = client.get("/api/v1/coach/weak-topics", headers=headers)
    assert r_weak.status_code == 200
    assert any("React Hooks" in w["topic"] for w in r_weak.json())

    # 4. Strong Topics
    r_strong = client.get("/api/v1/coach/strong-topics", headers=headers)
    assert r_strong.status_code == 200
    assert any("React Components" in s["topic"] for s in r_strong.json())

    # 5. Chat "What should I improve?"
    r_chat1 = client.post("/api/v1/coach/chat", json={"message": "What should I improve?"}, headers=headers)
    assert r_chat1.status_code == 200
    assert "React Hooks" in r_chat1.json()["response"]

    # 6. Chat "Why?"
    r_chat2 = client.post("/api/v1/coach/chat", json={"message": "Why?"}, headers=headers)
    assert r_chat2.status_code == 200
    assert "React Hooks" in r_chat2.json()["response"] or "score" in r_chat2.json()["response"].lower()

    # 7. Practice question
    r_pq = client.post("/api/v1/coach/practice-question", json={}, headers=headers)
    assert r_pq.status_code == 200
    assert len(r_pq.json()["question"]) > 10
    db.close()
