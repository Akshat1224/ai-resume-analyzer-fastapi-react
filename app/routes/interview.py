from fastapi import APIRouter, Query
from app.schemas.interview_schema import (
    InterviewRequest,
    PracticeAttemptRequest,
    PracticeAttemptResponse,
    ProgressSummaryResponse,
)
from app.services.interview_service import (
    generate_interview_questions,
    evaluate_practice_attempt,
    fetch_progress_summary,
)

router = APIRouter(prefix="/interview", tags=["Interview"])


@router.post("/generate")
async def generate_questions(payload: InterviewRequest):
    """
    Generates interview questions, optionally targeted to specific candidate skill gaps
    with adaptive difficulty based on past performance.
    """
    result = await generate_interview_questions(
        role=payload.role,
        industry=payload.industry,
        experience_level=payload.experience_level,
        difficulty=payload.difficulty,
        num_questions=payload.num_questions,
        skill_gaps=payload.skill_gaps,
        session_id=payload.session_id or "default",
    )
    return result


@router.post("/attempt", response_model=PracticeAttemptResponse)
async def submit_practice_attempt(payload: PracticeAttemptRequest):
    """
    Records and grades a candidate's answer to an interview question,
    tracks per-skill progress, and adapts difficulty for subsequent questions.
    """
    return await evaluate_practice_attempt(payload)


@router.get("/progress", response_model=ProgressSummaryResponse)
async def get_practice_progress(session_id: str = Query("default")):
    """Retrieves practice history, per-skill mastery status, and recommended focus areas."""
    return fetch_progress_summary(session_id)
