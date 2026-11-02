from typing import Literal, Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# ---- Allowed values ----

JOB_ROLES = Literal[
    "Software Developer",
    "AI/ML Engineer",
    "Data Scientist",
    "Backend Developer",
    "Frontend Developer",
    "Custom",
]

INTERVIEW_TYPES = Literal["Technical", "HR", "Mixed", "Behavioral"]

EXPERIENCE_LEVELS = Literal["Beginner", "Intermediate", "Advanced"]

DIFFICULTIES = Literal["Beginner", "Intermediate", "Advanced", "Easy", "Medium", "Hard"]

QUESTION_COUNTS = Literal[3, 5, 10, 15]


# ---- Request schema ----

class InterviewSessionCreate(BaseModel):
    job_role: str = Field(..., max_length=100, description="Target role for interview, e.g., Python Developer")
    interview_type: INTERVIEW_TYPES
    experience_level: EXPERIENCE_LEVELS
    difficulty: DIFFICULTIES
    question_count: QUESTION_COUNTS
    interview_language: Optional[str] = "English"
    resume_skills: Optional[List[str]] = Field(default_factory=list)
    selected_skills: Optional[List[str]] = Field(default_factory=list)


# ---- Response schemas ----

class InterviewSessionResponse(BaseModel):
    id: int
    user_id: int
    job_role: str
    interview_type: str
    experience_level: str
    difficulty: str
    question_count: int
    status: str
    answered_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    interview_language: Optional[str] = "English"
    job_description: Optional[str] = None
    resume_skills: Optional[str] = None
    selected_skills: Optional[str] = None
    source_context: Optional[str] = None
    resume_profile: Optional[str] = None
    adaptive_state: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InterviewSessionListResponse(BaseModel):
    interviews: list[InterviewSessionResponse]
    total: int

# ---- DTO classes for AI provider ----

class FinalEvaluationDTO(BaseModel):
    overall_score: float = Field(..., description="Overall average score out of 10")
    overall_correctness: float = Field(..., description="Average correctness ratio")
    overall_relevance: float = Field(..., description="Average relevance ratio")
    overall_technical_depth: float = Field(..., description="Average technical depth ratio")
    overall_communication_quality: float = Field(..., description="Average communication quality ratio")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    feedback: str = Field(..., description="Aggregated feedback string")

class QuestionDTO(BaseModel):
    text: str = Field(..., description="The interview question text")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AnswerDTO(BaseModel):
    question_id: int = Field(..., description="ID of the question being answered")
    answer: str = Field(..., description="User's answer text")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EvaluationDTO(BaseModel):
    score: int = Field(..., ge=0, le=10, description="Overall score out of 10")
    correctness: float = Field(..., ge=0, le=1, description="Correctness ratio")
    relevance: float = Field(..., ge=0, le=1, description="Relevance ratio")
    technical_depth: float = Field(..., ge=0, le=1, description="Technical depth ratio")
    communication_quality: float = Field(..., ge=0, le=1, description="Communication quality ratio")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    feedback: str = Field(..., description="Human‑readable feedback string")
