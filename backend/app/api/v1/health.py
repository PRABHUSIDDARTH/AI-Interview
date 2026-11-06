from fastapi import APIRouter

from app.services.ai import ai_status

router = APIRouter()

@router.get("/health", status_code=200)
def check_health():
    """
    Health check endpoint to verify backend status.

    `ai` shows which LLM provider/model is active (never the key), so it is easy to tell
    whether interviews are using a real model or mock output.
    """
    return {
        "status": "ok",
        "message": "Backend service is healthy",
        "ai": ai_status(),
    }
