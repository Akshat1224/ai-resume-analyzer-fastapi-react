from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

import os

from app.services.pdf_service import extract_text_from_pdf
from app.services.prompt_service import build_resume_prompt
from app.services.ai_service import analyze_resume
from app.utils.stream import fake_progress_stream

router = APIRouter(
    prefix="/resume",
    tags=["Resume"]
)


UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/stream")
async def stream_progress():

    return EventSourceResponse(
        fake_progress_stream()
    )


@router.post("/analyze")
async def analyze_resume_api(
    file: UploadFile = File(...)
):

    file_path = f"{UPLOAD_DIR}/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    resume_text = await extract_text_from_pdf(file_path)

    prompt = build_resume_prompt(resume_text)

    result = await analyze_resume(prompt)

    return JSONResponse(content=result)