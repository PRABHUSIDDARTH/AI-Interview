from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TopicMetricDTO(BaseModel):
    topic: str = Field(..., description="Topic name (e.g. 'React Hooks', 'useEffect')")
    skill: str = Field(..., description="Skill category (e.g. 'React')")
    score: float = Field(..., description="Average score for this topic out of 10")
    evaluations_count: int = Field(default=1, description="Number of evaluated questions on this topic")
    status: str = Field(default="neutral", description="'strong' | 'weak' | 'neutral'")
    common_pitfalls: List[str] = Field(default_factory=list, description="Common mistakes detected")
    recommendations: List[str] = Field(default_factory=list, description="Actionable improvement suggestions")


class SkillMetricDTO(BaseModel):
    skill: str = Field(..., description="Skill name")
    score: float = Field(..., description="Average score across all questions for this skill")
    evaluations_count: int = Field(default=1)


class ImprovementTrendDTO(BaseModel):
    direction: str = Field(..., description="'improving' | 'declining' | 'consistent' | 'baseline'")
    description: str = Field(..., description="Honest textual explanation of trend across recent sessions")
    history_scores: List[float] = Field(default_factory=list, description="Chronological session scores")
    delta: float = Field(default=0.0, description="Score change between first and latest session")


class RecommendedInterviewDTO(BaseModel):
    job_role: str = Field(..., description="Recommended job role")
    interview_type: str = Field(default="Technical", description="Interview type")
    difficulty: str = Field(default="Medium", description="Target difficulty")
    experience_level: str = Field(default="Intermediate")
    focus_topic: str = Field(..., description="Primary weak topic to target")
    selected_skills: List[str] = Field(default_factory=list, description="Skills to focus on")
    title: str = Field(..., description="Catchy title e.g. 'Intermediate React Interview: React Hooks Focus'")
    reason: str = Field(..., description="Why this interview is recommended based on candidate history")


class CoachSummaryResponse(BaseModel):
    has_enough_data: bool = Field(True, description="False if insufficient history exists for coaching")
    summary: str = Field(..., description="Personalized greeting and analysis summary")
    overall_score: float = Field(default=0.0, description="Average score across all completed interviews")
    recent_score: float = Field(default=0.0, description="Score of most recent completed interview")
    best_score: float = Field(default=0.0, description="Highest score achieved")
    strongest_skill: Optional[SkillMetricDTO] = Field(None, description="Candidate's highest-scoring skill")
    weakest_skill: Optional[SkillMetricDTO] = Field(None, description="Candidate's lowest-scoring skill")
    weak_topics: List[TopicMetricDTO] = Field(default_factory=list, description="Consistently weak topics")
    strong_topics: List[TopicMetricDTO] = Field(default_factory=list, description="Consistently strong topics")
    improvement_trend: ImprovementTrendDTO = Field(..., description="Trend analysis across sessions")
    metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Average correctness, relevance, technical_depth, communication",
    )
    recommended_interview: Optional[RecommendedInterviewDTO] = Field(
        None, description="Personalized next interview recommendation"
    )
    recommended_actions: List[str] = Field(
        default_factory=list, description="Actionable step-by-step next steps"
    )
    next_action: str = Field(..., description="Clear single next action")
    all_topics: List[TopicMetricDTO] = Field(
        default_factory=list, description="All evaluated topics with scores and status"
    )
    candidate_resume_skills: List[str] = Field(
        default_factory=list, description="Skills detected from candidate's resume"
    )
    is_preliminary: bool = Field(
        default=False, description="True if analysis is preliminary (based on a single interview)"
    )


class CoachChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Candidate question or prompt for the AI Coach")
    history: Optional[List[Dict[str, str]]] = Field(
        default_factory=list, description="Prior conversational messages (role, content)"
    )


class CoachChatResponse(BaseModel):
    response: str = Field(..., description="AI Coach grounded conversational response")
    practice_question: Optional[str] = Field(
        None, description="Targeted practice question if requested or appropriate"
    )
    referenced_topics: List[str] = Field(
        default_factory=list, description="Topics referenced from user history"
    )


class PracticeQuestionRequest(BaseModel):
    topic: Optional[str] = Field(None, description="Specific topic to practice (defaults to weakest)")


class PracticeQuestionResponse(BaseModel):
    question: str = Field(..., description="Targeted interview practice question")
    topic: str = Field(..., description="Targeted topic")
    skill: str = Field(..., description="Targeted skill")
    difficulty: str = Field(..., description="Question difficulty")
    rationale: str = Field(..., description="Why this question was chosen based on user history")


# Legacy schema preserved for full backward compatibility
class AICoachResponse(BaseModel):
    summary: str = Field(..., description="Personalized summary of candidate's progress and history")
    strengths: List[str] = Field(default_factory=list, description="List of key candidate strengths")
    weak_areas: List[str] = Field(default_factory=list, description="Primary weak areas needing improvement")
    recommended_topics: List[str] = Field(default_factory=list, description="Specific topics or actions recommended to practice")
    next_action: str = Field(..., description="Clear recommended next step for the user")
    has_enough_data: bool = Field(True, description="False if insufficient history exists for personalized coaching")
