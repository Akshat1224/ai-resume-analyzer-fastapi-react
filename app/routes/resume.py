import os
import uuid
import tempfile
import time
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.core.config import MAX_UPLOAD_BYTES, MAX_UPLOAD_SIZE_MB
from app.core.telemetry import logger
from app.schemas.resume_schema import (
    ResumeAnalysisResponse,
    ResumeComparisonResponse,
    MatchStatus,
)
from app.services.pdf_service import parse_pdf_document, PDFParsingError
from app.services.prompt_service import (
    build_resume_prompt,
    build_job_matching_prompt,
)
from app.services.ai_service import (
    analyze_resume,
    offline_heuristic_job_matcher,
    get_groq_api_key,
)
from app.services.matching_service import (
    process_grounded_job_matching,
    calculate_deterministic_ats_structural_score,
)
from app.services.cache_service import cache_service
from app.services.history_service import (
    save_analysis,
    list_analyses,
    get_analysis_by_id,
)
from app.services.comparison_service import compare_resume_analyses
from app.utils.stream import stage_broadcaster, stream_job_progress

router = APIRouter(
    prefix="/resume",
    tags=["Resume"]
)

# PDF magic bytes signature
_PDF_MAGIC_BYTES = b"%PDF-"


@router.get("/stream")
async def stream_progress(session_id: str = Query("default")):
    """Server-Sent Events endpoint streaming actual pipeline stages."""
    return EventSourceResponse(
        stream_job_progress(session_id)
    )


@router.post("/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume_api(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
):
    actual_session_id = session_id or "default"
    start_time = time.perf_counter()
    unique_file_id = str(uuid.uuid4())
    temp_path = os.path.join(tempfile.gettempdir(), f"resumeiq_{unique_file_id}.pdf")

    logger.info(f"Intake started: session={actual_session_id}, filename={file.filename}")

    try:
        await stage_broadcaster.emit_stage(actual_session_id, "Validating file format and size...")

        # 1. Validate file extension
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            msg = "Invalid file format. Only PDF documents are supported."
            await stage_broadcaster.emit_error(actual_session_id, msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            )

        # 2. Read content with size limit enforcement
        content = await file.read()
        if not content:
            msg = "Uploaded file is empty (0 bytes)."
            await stage_broadcaster.emit_error(actual_session_id, msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            )

        if len(content) > MAX_UPLOAD_BYTES:
            msg = f"File size ({len(content) / (1024*1024):.1f} MB) exceeds maximum limit of {MAX_UPLOAD_SIZE_MB} MB."
            await stage_broadcaster.emit_error(actual_session_id, msg)
            raise HTTPException(
                status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
                detail=msg,
            )

        # 3. Validate magic bytes header
        if not content.startswith(_PDF_MAGIC_BYTES):
            msg = "Corrupted or invalid PDF header. File is not a valid PDF document."
            await stage_broadcaster.emit_error(actual_session_id, msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            )

        # 4. Check deterministic cache
        cache_key = cache_service.build_resume_cache_key(content, job_description)
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            logger.info(f"[CACHE HIT] Resume analysis returned from cache for session={actual_session_id}")
            await stage_broadcaster.emit_stage(actual_session_id, "Retrieved verified analysis from cache")
            await stage_broadcaster.emit_stage(actual_session_id, "Completed")
            return ResumeAnalysisResponse.model_validate(cached_result)

        # 5. Write to secure ephemeral temp file
        with open(temp_path, "wb") as f:
            f.write(content)

        # 5. Parse PDF preserving page numbers and text snippets
        await stage_broadcaster.emit_stage(actual_session_id, "Parsing document pages and layout...")
        try:
            doc = parse_pdf_document(temp_path)
        except PDFParsingError as e:
            await stage_broadcaster.emit_error(actual_session_id, str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        if doc["is_scanned_or_empty"]:
            msg = "PDF contains no selectable text (scanned or image-only document). Please provide a text-based PDF."
            await stage_broadcaster.emit_error(actual_session_id, msg)
            raise HTTPException(
                status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                detail=msg,
            )

        # 6. Branch: Targeted Job Matching vs General ATS
        if job_description and job_description.strip():
            await stage_broadcaster.emit_stage(actual_session_id, "Evaluating qualifications against job description...")
            raw_skills = []
            api_key = get_groq_api_key()

            if api_key:
                prompt = build_job_matching_prompt(doc["pages"], job_description)
                ai_resp = await analyze_resume(prompt, max_tokens=1500)
                if isinstance(ai_resp, dict) and "skills" in ai_resp:
                    raw_skills = ai_resp["skills"]

            # Fallback to offline heuristic matcher if AI returned no skills or key missing
            if not raw_skills:
                heuristic_resp = offline_heuristic_job_matcher(doc["pages"], job_description)
                raw_skills = heuristic_resp.get("skills", [])

            await stage_broadcaster.emit_stage(actual_session_id, "Cross-verifying evidence citations in document...")
            job_match = process_grounded_job_matching(raw_skills, doc["pages"])

            await stage_broadcaster.emit_stage(actual_session_id, "Calculating deterministic match rubric...")

            matched_skills = [
                s.skill for s in job_match.skills_analysis if s.status == MatchStatus.MATCHED
            ]
            weak_skills = [
                s.skill for s in job_match.skills_analysis
                if s.status in (MatchStatus.UNVERIFIABLE, MatchStatus.PARTIALLY_MATCHED)
            ]
            missing_skills = [
                s.skill for s in job_match.skills_analysis if s.status == MatchStatus.MISSING
            ]
            suggestions = [s.suggestion for s in job_match.prioritized_suggestions]

            response = ResumeAnalysisResponse(
                ats_score=job_match.score_breakdown.total_match_score,
                strengths=[f"Verified match: {s}" for s in matched_skills] or ["Relevant candidate qualifications found."],
                weaknesses=[f"Needs substantiation: {s}" for s in weak_skills] if weak_skills else [],
                missing_skills=missing_skills,
                suggestions=suggestions or ["Review job requirements and align project bullet points."],
                job_match=job_match,
                metadata={
                    "page_count": doc["page_count"],
                    "total_words": doc["total_words"],
                    "mode": "job_matching",
                    "duration_seconds": round(time.perf_counter() - start_time, 2),
                },
            )

        else:
            await stage_broadcaster.emit_stage(actual_session_id, "Auditing structural ATS completeness...")
            structural_result = calculate_deterministic_ats_structural_score(doc)

            api_key = get_groq_api_key()
            if api_key:
                prompt = build_resume_prompt(doc["chunks"])
                ai_resp = await analyze_resume(prompt, max_tokens=600)
                if isinstance(ai_resp, dict) and "ats_score" in ai_resp:
                    llm_score = int(ai_resp.get("ats_score", 70))
                    blended_score = int(round(0.6 * structural_result["ats_score"] + 0.4 * llm_score))
                    structural_result["ats_score"] = max(0, min(100, blended_score))
                    if ai_resp.get("strengths"):
                        structural_result["strengths"] = list(set(structural_result["strengths"] + ai_resp["strengths"]))
                    if ai_resp.get("suggestions"):
                        structural_result["suggestions"] = list(set(structural_result["suggestions"] + ai_resp["suggestions"]))

            response = ResumeAnalysisResponse(
                ats_score=structural_result["ats_score"],
                strengths=structural_result["strengths"],
                weaknesses=structural_result["weaknesses"],
                missing_skills=structural_result["missing_skills"],
                suggestions=structural_result["suggestions"],
                job_match=None,
                metadata={
                    "page_count": doc["page_count"],
                    "total_words": doc["total_words"],
                    "mode": "structural_ats_only",
                    "duration_seconds": round(time.perf_counter() - start_time, 2),
                },
            )

        # 7. Store in cache, persist to history, and emit Completed upon genuine success
        await cache_service.set(cache_key, response.model_dump(), ttl=3600)
        
        analysis_id = save_analysis(
            session_id=actual_session_id,
            ats_score=response.ats_score,
            role_target=(job_description[:60] if job_description else "General ATS"),
            filename=file.filename or "resume.pdf",
            summary=(response.job_match.score_breakdown.summary if response.job_match else "ATS Structural Audit"),
            response_data=response.model_dump(),
        )
        response.metadata["analysis_id"] = analysis_id

        await stage_broadcaster.emit_stage(actual_session_id, "Completed")
        elapsed = time.perf_counter() - start_time
        logger.info(f"Intake completed successfully: session={actual_session_id}, score={response.ats_score}, duration={elapsed:.2f}s")
        return response

    except HTTPException:
        raise
    except Exception as exc:
        msg = f"Unexpected processing error: {str(exc)}"
        await stage_broadcaster.emit_error(actual_session_id, msg)
        logger.error(f"Intake exception: session={actual_session_id}, error={msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )

    finally:
        # Guaranteed cleanup of sensitive resume file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@router.get("/history")
async def get_analysis_history(session_id: str = Query("default"), limit: int = Query(20)):
    """List historical resume analyses for this workspace/session."""
    return list_analyses(session_id=session_id, limit=limit)


@router.get("/history/{analysis_id}")
async def get_historical_analysis_detail(analysis_id: str):
    """Retrieve full details of a specific historical resume analysis."""
    record = get_analysis_by_id(analysis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID '{analysis_id}' was not found.",
        )
    return record


@router.post("/compare", response_model=ResumeComparisonResponse)
async def compare_resume_versions(
    file_v1: UploadFile = File(..., description="Base version (V1) resume PDF"),
    file_v2: UploadFile = File(..., description="Updated version (V2) resume PDF"),
    job_description: str = Form(..., description="Target job description for both versions"),
):
    """
    Compare two resume versions against the exact same job description.
    Detects score deltas, newly matched skills, dropped qualifications,
    removed evidence snippets, and unsupported claims.
    """
    if not job_description or not job_description.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A job description is required to compare resume versions.",
        )

    # Analyze V1
    resp_v1 = await analyze_resume_api(file=file_v1, job_description=job_description, session_id=None)
    # Analyze V2
    resp_v2 = await analyze_resume_api(file=file_v2, job_description=job_description, session_id=None)

    # Compute deterministic version comparison
    comparison = compare_resume_analyses(resp_v1, resp_v2)
    return comparison