import pytest
from starlette.testclient import TestClient
import pymupdf as fitz

from app.main import app
from app.schemas.resume_schema import (
    ResumeAnalysisResponse,
    JobMatchAnalysis,
    ScoreBreakdown,
    SkillMatchItem,
    SkillCategory,
    MatchStatus,
    EvidenceSnippet,
)
from app.services.comparison_service import compare_resume_analyses
from app.services.history_service import (
    save_analysis,
    list_analyses,
    get_analysis_by_id,
    save_practice_attempt,
    get_adaptive_difficulty_for_skill,
)

client = TestClient(app)


def create_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_compare_resume_analyses_detects_improvement():
    """Version comparison identifies newly verified skills and positive score delta."""
    # V1: Only Python
    v1 = ResumeAnalysisResponse(
        ats_score=50,
        job_match=JobMatchAnalysis(
            score_breakdown=ScoreBreakdown(required_score=35.0, preferred_score=15.0, total_match_score=50),
            skills_analysis=[
                SkillMatchItem(skill="Python", category=SkillCategory.REQUIRED, status=MatchStatus.MATCHED, evidence=[EvidenceSnippet(page=1, snippet="Python dev", verified=True)]),
                SkillMatchItem(skill="Docker", category=SkillCategory.REQUIRED, status=MatchStatus.MISSING),
            ],
            gaps=[],
            prioritized_suggestions=[],
        ),
    )

    # V2: Python + Docker verified
    v2 = ResumeAnalysisResponse(
        ats_score=85,
        job_match=JobMatchAnalysis(
            score_breakdown=ScoreBreakdown(required_score=70.0, preferred_score=15.0, total_match_score=85),
            skills_analysis=[
                SkillMatchItem(skill="Python", category=SkillCategory.REQUIRED, status=MatchStatus.MATCHED, evidence=[EvidenceSnippet(page=1, snippet="Python dev", verified=True)]),
                SkillMatchItem(skill="Docker", category=SkillCategory.REQUIRED, status=MatchStatus.MATCHED, evidence=[EvidenceSnippet(page=1, snippet="Docker containers", verified=True)]),
            ],
            gaps=[],
            prioritized_suggestions=[],
        ),
    )

    diff = compare_resume_analyses(v1, v2)
    assert diff.score_delta == 35
    assert "Docker" in diff.added_skills
    assert len(diff.removed_skills) == 0
    assert "significant improvement" in diff.verdict.lower()


def test_compare_resume_analyses_detects_regression_and_unsupported_claims():
    """Version comparison flags dropped qualifications and unsupported claims."""
    # V1 has PostgreSQL verified
    v1 = ResumeAnalysisResponse(
        ats_score=80,
        job_match=JobMatchAnalysis(
            score_breakdown=ScoreBreakdown(required_score=50.0, preferred_score=30.0, total_match_score=80),
            skills_analysis=[
                SkillMatchItem(skill="PostgreSQL", category=SkillCategory.REQUIRED, status=MatchStatus.MATCHED, evidence=[EvidenceSnippet(page=1, snippet="PostgreSQL DBA", verified=True)]),
            ],
        ),
    )

    # V2 dropped PostgreSQL and claimed Kubernetes vaguely without evidence
    v2 = ResumeAnalysisResponse(
        ats_score=40,
        job_match=JobMatchAnalysis(
            score_breakdown=ScoreBreakdown(required_score=20.0, preferred_score=20.0, total_match_score=40),
            skills_analysis=[
                SkillMatchItem(skill="PostgreSQL", category=SkillCategory.REQUIRED, status=MatchStatus.MISSING),
                SkillMatchItem(skill="Kubernetes", category=SkillCategory.PREFERRED, status=MatchStatus.UNVERIFIABLE),
            ],
        ),
    )

    diff = compare_resume_analyses(v1, v2)
    assert diff.score_delta == -40
    assert "PostgreSQL" in diff.removed_skills
    assert "Kubernetes" in diff.unsupported_claims
    assert "regression" in diff.verdict.lower()


def test_compare_endpoint_integration():
    """POST /resume/compare analyzes two PDF versions against a job description."""
    pdf_v1 = create_pdf_bytes("John\nExperience: Built web tools in Python.")
    pdf_v2 = create_pdf_bytes("John\nExperience: Built web tools in Python and deployed Docker microservices with PostgreSQL.")
    jd = "Requirements:\n- Python\n- Docker\n- PostgreSQL"

    response = client.post(
        "/resume/compare",
        files={
            "file_v1": ("v1.pdf", pdf_v1, "application/pdf"),
            "file_v2": ("v2.pdf", pdf_v2, "application/pdf"),
        },
        data={"job_description": jd},
    )

    assert response.status_code == 200
    data = response.json()
    assert "base_version_score" in data
    assert "target_version_score" in data
    assert "score_delta" in data
    assert "verdict" in data
    assert data["target_version_score"] >= data["base_version_score"]


def test_history_persistence_and_retrieval():
    """Verify analyses are persisted to SQLite and retrievable by session ID."""
    test_session = "test_sess_hist_99"
    analysis_id = save_analysis(
        session_id=test_session,
        ats_score=82,
        role_target="Senior Python Engineer",
        filename="test_resume.pdf",
        summary="Strong Python match",
        response_data={"ats_score": 82, "strengths": ["Python"]},
    )

    # List history
    response = client.get(f"/resume/history?session_id={test_session}")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    assert items[0]["id"] == analysis_id
    assert items[0]["ats_score"] == 82

    # Get single history detail
    detail_resp = client.get(f"/resume/history/{analysis_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == analysis_id
    assert detail["response"]["ats_score"] == 82


def test_interview_generator_gap_targeting():
    """POST /interview/generate targets specific candidate skill gaps."""
    payload = {
        "role": "Cloud Architect",
        "industry": "Fintech",
        "experience_level": "Senior",
        "difficulty": "medium",
        "num_questions": 3,
        "skill_gaps": ["Kubernetes", "Disaster Recovery"],
        "session_id": "gap_test_session",
    }

    response = client.post("/interview/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert len(data["questions"]) > 0
    assert data.get("adapted_from_gaps") is True


def test_adaptive_difficulty_practice_attempts():
    """Submitting practice attempts grades answer, records progress, and adapts difficulty."""
    test_session = "practice_sess_42"

    # Attempt 1: Poor answer -> should recommend easy next
    resp1 = client.post(
        "/interview/attempt",
        json={
            "question": "Explain Kubernetes pods.",
            "target_skill": "Kubernetes",
            "difficulty": "medium",
            "user_answer": "I guess they run stuff.",
            "session_id": test_session,
        },
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["score"] < 60
    assert data1["next_difficulty"] == "easy"

    # Check progress summary
    prog_resp = client.get(f"/interview/progress?session_id={test_session}")
    assert prog_resp.status_code == 200
    prog_data = prog_resp.json()
    assert prog_data["total_attempts"] >= 1
    assert any(s["skill"] == "Kubernetes" for s in prog_data["skills_tracked"])
    assert "Kubernetes" in prog_data["recommended_focus"]
