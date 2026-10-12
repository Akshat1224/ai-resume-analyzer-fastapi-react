import pytest
from pydantic import ValidationError
from app.schemas.resume_schema import (
    MatchStatus,
    SkillCategory,
    EvidenceSnippet,
    SkillMatchItem,
    ScoreBreakdown,
    ResumeAnalysisResponse,
)


def test_valid_resume_response_model():
    """Verify that ResumeAnalysisResponse serializes correctly with all fields."""
    response = ResumeAnalysisResponse(
        ats_score=85,
        strengths=["Strong Python", "Proven FastAPI experience"],
        weaknesses=["Missing Kubernetes"],
        missing_skills=["Kubernetes"],
        suggestions=["Add containerization details"],
        metadata={"page_count": 2},
    )

    data = response.model_dump()
    assert data["ats_score"] == 85
    assert len(data["strengths"]) == 2
    assert data["job_match"] is None


def test_invalid_score_bounds_raises_validation_error():
    """Score must be within 0-100."""
    with pytest.raises(ValidationError):
        ResumeAnalysisResponse(
            ats_score=150,  # Invalid: > 100
            strengths=[],
            weaknesses=[],
            missing_skills=[],
            suggestions=[],
        )

    with pytest.raises(ValidationError):
        ResumeAnalysisResponse(
            ats_score=-5,  # Invalid: < 0
            strengths=[],
            weaknesses=[],
            missing_skills=[],
            suggestions=[],
        )


def test_invalid_score_breakdown_bounds():
    """ScoreBreakdown required_score cannot exceed 70.0 and preferred cannot exceed 30.0."""
    with pytest.raises(ValidationError):
        ScoreBreakdown(
            required_score=75.0,  # Invalid: > 70
            preferred_score=10.0,
            total_match_score=85,
        )

    with pytest.raises(ValidationError):
        ScoreBreakdown(
            required_score=50.0,
            preferred_score=35.0,  # Invalid: > 30
            total_match_score=85,
        )


def test_invalid_enum_status():
    """Passing an arbitrary unrecognized string for MatchStatus raises validation error."""
    with pytest.raises(ValidationError):
        SkillMatchItem(
            skill="Python",
            category=SkillCategory.REQUIRED,
            status="totally_awesome",  # Invalid enum value
        )
