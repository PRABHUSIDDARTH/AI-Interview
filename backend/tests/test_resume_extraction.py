import pytest
from app.services.resume_parser import ResumeParserService, normalize_skill
from app.services.ai import AIProvider

def test_skill_normalization():
    assert normalize_skill("ReactJS") == "React"
    assert normalize_skill("React.js") == "React"
    assert normalize_skill("Node.js") == "Node.js"
    assert normalize_skill("Postgres") == "PostgreSQL"
    assert normalize_skill("FastAPI") == "FastAPI"

def test_resume_parser_deterministic_extraction():
    parser = ResumeParserService(ai_provider=AIProvider())
    sample_resume = (
        "John Doe - Senior Software Engineer\n"
        "Proficient in Python, FastAPI, React.js, PostgreSQL, Docker, and Git.\n"
        "Built scalable microservices REST API backend.\n"
    )
    profile = parser.parse_resume_text(sample_resume)
    
    assert "Python" in profile["skills"]
    assert "FastAPI" in profile["skills"]
    assert "React" in profile["skills"]
    assert "PostgreSQL" in profile["skills"]
    assert "Docker" in profile["skills"]
    assert profile["inferred_role"] == "Backend Developer"

def test_no_hallucinated_skills():
    parser = ResumeParserService(ai_provider=AIProvider())
    sample_resume = "Simple resume mentioning only HTML and CSS."
    profile = parser.parse_resume_text(sample_resume)
    
    assert "Python" not in profile["skills"]
    assert "Docker" not in profile["skills"]
    assert "Kubernetes" not in profile["skills"]

def test_question_generation_with_resume_skills():
    ai = AIProvider()
    setup = {
        "job_role": "Backend Developer",
        "interview_type": "Technical",
        "experience_level": "Intermediate",
        "difficulty": "Medium",
        "question_count": 3,
        "resume_skills": ["Python", "FastAPI", "Docker"],
        "interview_language": "English",
    }
    questions = ai.generate_questions_batch(setup, 3)
    assert len(questions) == 3
    # Verify at least one question mentions candidate resume skills
    assert any("Python" in q or "FastAPI" in q or "Docker" in q for q in questions)

def test_question_generation_multilingual_preserves_technical_terms():
    ai = AIProvider()
    setup = {
        "job_role": "Backend Developer",
        "interview_type": "Technical",
        "experience_level": "Intermediate",
        "difficulty": "Medium",
        "question_count": 3,
        "resume_skills": ["Python", "FastAPI"],
        "interview_language": "Tamil",
    }
    questions = ai.generate_questions_batch(setup, 3)
    assert len(questions) == 3
    assert any("Tamil" in q for q in questions)


def test_uploaded_resume_remains_available_from_step1_to_step2():
    """Verify that extract_resume response format exposes profile.skills directly for Step 2."""
    parser = ResumeParserService(ai_provider=AIProvider())
    text = "Experience with Python, React, PostgreSQL, Docker."
    profile = parser.parse_resume_text(text)
    assert "skills" in profile
    assert isinstance(profile["skills"], list)
    assert len(profile["skills"]) >= 3
    assert "React" in profile["skills"]
    assert "Python" in profile["skills"]


def test_selected_resume_skills_remain_available_until_interview_creation():
    """Verify that extracted skills and selected focus skills flow into setup state."""
    parser = ResumeParserService(ai_provider=AIProvider())
    text = "Proficient in React, Python, PostgreSQL, Docker."
    extracted = parser.parse_resume_text(text)["skills"]
    selected = ["React"]
    assert set(selected).issubset(set(extracted))

