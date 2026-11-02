from fastapi import APIRouter, Depends, status, HTTPException
from typing import List, Any
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User as UserModel
from app.services.rag_coach import RAGCoachService
from app.services.interview_engine import InterviewEngine
from app.schemas.coaching import (
    CoachSummaryResponse,
    TopicMetricDTO,
    PracticeQuestionRequest,
    PracticeQuestionResponse,
    CoachChatRequest,
    CoachChatResponse,
)

router = APIRouter()

# Shared interview engine providing underlying AI provider
engine = InterviewEngine()


@router.get("/summary", response_model=CoachSummaryResponse, status_code=status.HTTP_200_OK)
def get_coach_summary(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Return comprehensive personalized AI Coach analysis grounded in current user's history."""
    coach_service = RAGCoachService(engine.provider)
    return coach_service.get_coach_summary(db, current_user)


@router.get("/recommendations", response_model=List[TopicMetricDTO], status_code=status.HTTP_200_OK)
def get_coach_recommendations(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Return actionable, grounded recommendations targeting the user's weak topics."""
    coach_service = RAGCoachService(engine.provider)
    return coach_service.get_coach_recommendations(db, current_user)


@router.get("/topics", response_model=List[TopicMetricDTO], status_code=status.HTTP_200_OK)
def get_coach_topics(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Return topic-wise breakdown and performance scores for the authenticated candidate."""
    coach_service = RAGCoachService(engine.provider)
    return coach_service.get_coach_topics(db, current_user)


@router.get("/weak-topics", response_model=List[TopicMetricDTO], status_code=status.HTTP_200_OK)
def get_coach_weak_topics(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Return identified weak topics for the authenticated candidate."""
    coach_service = RAGCoachService(engine.provider)
    return coach_service.get_coach_weak_topics(db, current_user)


@router.get("/strong-topics", response_model=List[TopicMetricDTO], status_code=status.HTTP_200_OK)
def get_coach_strong_topics(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Return identified strong topics for the authenticated candidate."""
    coach_service = RAGCoachService(engine.provider)
    return coach_service.get_coach_strong_topics(db, current_user)


@router.post("/practice-question", response_model=PracticeQuestionResponse, status_code=status.HTTP_200_OK)
def generate_practice_question(
    payload: PracticeQuestionRequest = PracticeQuestionRequest(),
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Generate a non-duplicate practice question targeting candidate's weakest topic."""
    coach_service = RAGCoachService(engine.provider)
    return coach_service.generate_practice_question(db, current_user, target_topic=payload.topic)


@router.post("/chat", response_model=CoachChatResponse, status_code=status.HTTP_200_OK)
def chat_with_coach(
    payload: CoachChatRequest,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Conversational AI Coach answering queries strictly grounded in authenticated user history."""
    coach_service = RAGCoachService(engine.provider)
    return coach_service.chat_with_coach(db, current_user, payload.message, payload.history)
