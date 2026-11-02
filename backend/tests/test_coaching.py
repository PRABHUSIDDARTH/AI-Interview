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

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_coaching.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
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


def test_coach_cold_start():
    """Verify that a user with 0 completed interviews gets the cold-start response."""
    db = TestingSessionLocal()
    user = User(
        email="user_cold@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Cold Candidate",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/interviews/coach", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["has_enough_data"] is False
    assert "don't have enough interview history" in data["summary"]
    assert len(data["recommended_topics"]) == 0
    db.close()


def test_coach_personalized_recommendations():
    """Verify that a user with completed sessions gets personalized guidance grounded in their data."""
    db = TestingSessionLocal()
    user = User(
        email="user_active@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Active Candidate",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    evals = [
        {
            "question": "Design a REST API rate limiter.",
            "answer": "I would use token bucket algorithm.",
            "score": 4,
            "correctness": 0.4,
            "relevance": 0.6,
            "technical_depth": 0.3,
            "communication_quality": 0.5,
            "strengths": ["Understands token bucket concept"],
            "weaknesses": ["System Design depth", "Missing distributed caching strategy"],
            "feedback": "Lacks architectural detail on Redis synchronization.",
        }
    ]

    session = InterviewSession(
        user_id=user.id,
        job_role="Backend Developer",
        interview_type="System Design",
        experience_level="Intermediate",
        difficulty="Medium",
        question_count=1,
        answered_count=1,
        status="completed",
        questions=json.dumps(["Design a REST API rate limiter."]),
        evaluations=json.dumps(evals),
    )
    db.add(session)
    db.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/interviews/coach", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["has_enough_data"] is True
    assert len(data["summary"]) > 0
    assert len(data["weak_areas"]) > 0
    assert len(data["recommended_topics"]) > 0
    assert "next_action" in data
    db.close()


def test_cross_user_isolation():
    """SECURITY TEST: Verify that User A cannot retrieve or be affected by User B's interview data."""
    db = TestingSessionLocal()

    # Create User A with 0 sessions
    user_a = User(
        email="user_a@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="User A",
        is_active=True,
    )
    # Create User B with a low-scoring System Design session
    user_b = User(
        email="user_b@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="User B",
        is_active=True,
    )
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    evals_b = [
        {
            "question": "Explain B-Tree indexing.",
            "answer": "B-Trees store data in nodes.",
            "score": 3,
            "correctness": 0.3,
            "relevance": 0.4,
            "technical_depth": 0.2,
            "communication_quality": 0.4,
            "strengths": ["Basic definition"],
            "weaknesses": ["Database Indexing"],
            "feedback": "Needs to explain page splitting and disk I/O.",
        }
    ]
    session_b = InterviewSession(
        user_id=user_b.id,
        job_role="Data Engineer",
        interview_type="Technical",
        experience_level="Advanced",
        difficulty="Hard",
        question_count=1,
        answered_count=1,
        status="completed",
        questions=json.dumps(["Explain B-Tree indexing."]),
        evaluations=json.dumps(evals_b),
    )
    db.add(session_b)
    db.commit()

    # User A requests their AI coach
    token_a = create_access_token(user_a.id)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    response_a = client.get("/api/v1/interviews/coach", headers=headers_a)
    assert response_a.status_code == 200
    data_a = response_a.json()

    # User A MUST receive cold start response because User A has 0 sessions!
    assert data_a["has_enough_data"] is False
    assert "Database Indexing" not in data_a["weak_areas"]
    assert "don't have enough interview history" in data_a["summary"]

    # User B requests their AI coach
    token_b = create_access_token(user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response_b = client.get("/api/v1/interviews/coach", headers=headers_b)
    assert response_b.status_code == 200
    data_b = response_b.json()

    # User B MUST receive personalized guidance with User B's data
    assert data_b["has_enough_data"] is True
    assert "Database Indexing" in data_b["weak_areas"] or len(data_b["weak_areas"]) > 0

    db.close()
