from app.schemas.interview import (
    InterviewSessionCreate,
    InterviewSessionResponse,
    InterviewSessionListResponse,
)
from app.schemas.coaching import AICoachResponse
from app.services.rag_coach import RAGCoachService
from app.models.interview_session import InterviewSession
from app.services.interview_engine import InterviewEngine
from fastapi import APIRouter, Depends, HTTPException, status, Body, File, Form, UploadFile
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from app.api import deps

from app.models.user import User as UserModel
from app.utils.pdf_extractor import extract_text_from_pdf
router = APIRouter()

engine = InterviewEngine()

@router.post("/", response_model=InterviewSessionResponse, status_code=status.HTTP_201_CREATED)
def create_interview(
    session_in: InterviewSessionCreate,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Legacy endpoint: create interview session without AI flow."""
    db_session = InterviewSession(
        user_id=current_user.id,
        job_role=session_in.job_role,
        interview_type=session_in.interview_type,
        experience_level=session_in.experience_level,
        difficulty=session_in.difficulty,
        question_count=session_in.question_count,
        status="created",
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

from app.services.resume_parser import ResumeParserService

@router.post("/extract-resume", response_model=Dict, status_code=status.HTTP_200_OK)
async def extract_resume_data(
    resume: UploadFile = File(...),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Extract structured skills, technologies, and inferred job role from uploaded resume PDF."""
    filename = (resume.filename or "").lower()
    if resume.content_type != "application/pdf" and not filename.endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume must be a PDF file.")
    
    content = await resume.read()
    max_size = 2 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume PDF exceeds maximum size of 2 MiB.")
    
    # Magic byte header validation to prevent file extension spoofing
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PDF file format. Missing PDF header.")

    import os, tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        try:
            resume_text = extract_text_from_pdf(tmp_path)
        except Exception as pdf_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process resume PDF: File is corrupt or unreadable."
            )
        
        if not resume_text or not resume_text.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume PDF is empty or contains no extractable text.")
        
        parser = ResumeParserService(engine.provider)
        profile = parser.parse_resume_text(resume_text)
        return {"success": True, "profile": profile}
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

@router.post("/start", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def start_interview(
    interview_type: str = Form(...),
    job_role: str = Form(...),
    experience_level: str = Form(...),
    difficulty: str = Form(...),
    question_count: int = Form(...),
    interview_language: Optional[str] = Form("English"),
    resume_skills: Optional[str] = Form(None),  # JSON string or comma-separated list
    selected_skills: Optional[str] = Form(None),  # JSON string of user-chosen skill subset
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
    resume: UploadFile = File(None),
    job_description: Optional[str] = Form(None),
) -> Any:
    """Create a session and return the first question, with optional resume PDF, language, skills, and selected skill focus."""
    from app.services.resume_parser import normalize_skill
    import logging, os, tempfile, json
    logger = logging.getLogger("uvicorn.error")

    def parse_skill_list(raw: Optional[str]) -> list[str]:
        if not raw or not raw.strip():
            return []
        try:
            val = json.loads(raw)
            if isinstance(val, list):
                return [normalize_skill(str(s)) for s in val if str(s).strip()]
        except Exception:
            pass
        # Fallback to comma separation
        cleaned = raw.strip(" '\"[]")
        parts = [p.strip(" '\"[]") for p in cleaned.split(",") if p.strip(" '\"[]")]
        return [normalize_skill(p) for p in parts]

    parsed_skills = parse_skill_list(resume_skills)
    parsed_selected = parse_skill_list(selected_skills)

    # Ensure selected skills are present in parsed_skills
    if parsed_selected:
        skill_set = set(parsed_skills)
        for sel in parsed_selected:
            if sel not in skill_set:
                parsed_skills.append(sel)
                skill_set.add(sel)

    # Build the Pydantic model for session creation
    session_in = InterviewSessionCreate(
        interview_type=interview_type,
        job_role=job_role,
        experience_level=experience_level,
        difficulty=difficulty,
        question_count=question_count,
        interview_language=interview_language or "English",
        resume_skills=parsed_skills,
        selected_skills=parsed_selected,
    )

    resume_text: Optional[str] = None

    # Process resume PDF if provided
    if resume is not None and getattr(resume, "filename", None):
        filename = (resume.filename or "").lower()
        if resume.content_type != "application/pdf" and not filename.endswith(".pdf"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume must be a PDF file.")
        
        content = await resume.read()
        max_size = 2 * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume PDF exceeds maximum size of 2 MiB.")
        
        if not content.startswith(b"%PDF"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PDF file format. Missing PDF header.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            extracted = extract_text_from_pdf(tmp_path)
            if extracted and extracted.strip():
                resume_text = extracted
        except Exception as pdf_err:
            logger.warning("Failed to extract text from resume PDF in start_interview: %s", pdf_err)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    # Validate job description length if provided
    if job_description is not None and len(job_description) > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description must not exceed 2,000 characters."
        )

    try:
        session = engine.create_session(db, session_in, current_user.id, resume_text=resume_text, job_description=job_description)
        question = engine.get_next_question(db, session.id)
        return {"session_id": session.id, "question": question}
    except Exception as e:
        logger.error("Failed to create interview session: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create interview session: {str(e)}"
        )

@router.get("/{session_id}/next", response_model=Dict)
def get_next_question(
    session_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Return the next question for a session."""
    sess = db.query(InterviewSession).filter(InterviewSession.id == session_id, InterviewSession.user_id == current_user.id).first()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    question = engine.get_next_question(db, sess.id)
    return {"session_id": sess.id, "question": question}

@router.post("/{session_id}/answer", response_model=Dict)
def submit_answer(
    session_id: int,
    payload: Dict = Body(...),  # expects {"answer": "..."}
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Submit an answer and receive evaluation."""
    sess = db.query(InterviewSession).filter(InterviewSession.id == session_id, InterviewSession.user_id == current_user.id).first()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    answer_text = payload.get("answer", "")
    evaluation = engine.submit_answer(db, sess.id, answer_text)
    return {"session_id": sess.id, "evaluation": evaluation}

@router.get("/", response_model=InterviewSessionListResponse)
def list_interviews(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    interviews = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )
    return {"interviews": interviews, "total": len(interviews)}

@router.get("/analytics", response_model=Dict, status_code=status.HTTP_200_OK)
def get_user_analytics(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Return aggregated analytics for the current user across all interview sessions."""
    return engine.get_user_analytics(db, current_user.id)

@router.get("/coach", response_model=AICoachResponse, status_code=status.HTTP_200_OK)
def get_ai_coach_guidance(
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Return personalized AI coaching recommendations using RAG over current user's history."""
    coach_service = RAGCoachService(engine.provider)
    return coach_service.generate_coaching_guidance(db, current_user)

@router.get("/{interview_id}", response_model=InterviewSessionResponse)
def get_interview(
    interview_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    interview = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == interview_id, InterviewSession.user_id == current_user.id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    return interview

@router.get("/{session_id}/evaluation", response_model=Dict)
def get_session_evaluation(
    session_id: int,
    db: Session = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    """Return aggregated evaluation for a completed interview session."""
    sess = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    return engine.get_aggregated_evaluation(db, sess.id)

