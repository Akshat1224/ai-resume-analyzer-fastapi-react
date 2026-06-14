from fastapi import APIRouter

from app.schemas.interview_schema import InterviewRequest

from app.services.interview_service import generate_interview_questions

router = APIRouter(prefix="/interview", tags=["Interview"])


@router.post("/generate")
async def generate_questions(payload: InterviewRequest):

    result = await generate_interview_questions(
        payload.role,
        payload.industry,
        payload.experience_level,
        payload.difficulty,
        payload.num_questions,
    )

    return result
