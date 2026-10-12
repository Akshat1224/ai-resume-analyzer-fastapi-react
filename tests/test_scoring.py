import pytest
from app.schemas.resume_schema import (
    MatchStatus,
    SkillCategory,
    SkillMatchItem,
    EvidenceSnippet,
)
from app.services.matching_service import (
    calculate_match_score,
    build_gaps_and_suggestions,
)


def test_perfect_match_score():
    """All required and preferred skills matched -> 100 points."""
    skills = [
        SkillMatchItem(
            skill="Python",
            category=SkillCategory.REQUIRED,
            status=MatchStatus.MATCHED,
            evidence=[EvidenceSnippet(page=1, snippet="5 years Python experience", verified=True)],
        ),
        SkillMatchItem(
            skill="FastAPI",
            category=SkillCategory.REQUIRED,
            status=MatchStatus.MATCHED,
            evidence=[EvidenceSnippet(page=1, snippet="Built REST APIs with FastAPI", verified=True)],
        ),
        SkillMatchItem(
            skill="Docker",
            category=SkillCategory.PREFERRED,
            status=MatchStatus.MATCHED,
            evidence=[EvidenceSnippet(page=2, snippet="Dockerized microservices", verified=True)],
        ),
    ]

    breakdown = calculate_match_score(skills)
    assert breakdown.total_match_score == 100
    assert breakdown.required_score == 70.0
    assert breakdown.preferred_score == 30.0
    assert breakdown.required_matched_count == 2
    assert breakdown.preferred_matched_count == 1


def test_zero_match_score():
    """All skills missing -> 0 points."""
    skills = [
        SkillMatchItem(
            skill="Kubernetes",
            category=SkillCategory.REQUIRED,
            status=MatchStatus.MISSING,
        ),
        SkillMatchItem(
            skill="Go",
            category=SkillCategory.PREFERRED,
            status=MatchStatus.MISSING,
        ),
    ]

    breakdown = calculate_match_score(skills)
    assert breakdown.total_match_score == 0
    assert breakdown.required_score == 0.0
    assert breakdown.preferred_score == 0.0


def test_partial_match_weighting():
    """Partially matched skills receive 50% credit."""
    skills = [
        # Required: 1 matched (1.0), 1 partial (0.5) -> avg 0.75 * 70 = 52.5
        SkillMatchItem(
            skill="Python",
            category=SkillCategory.REQUIRED,
            status=MatchStatus.MATCHED,
        ),
        SkillMatchItem(
            skill="SQL",
            category=SkillCategory.REQUIRED,
            status=MatchStatus.PARTIALLY_MATCHED,
        ),
        # Preferred: 1 partial (0.5) -> avg 0.5 * 30 = 15.0
        SkillMatchItem(
            skill="AWS",
            category=SkillCategory.PREFERRED,
            status=MatchStatus.PARTIALLY_MATCHED,
        ),
    ]

    breakdown = calculate_match_score(skills)
    assert breakdown.required_score == 52.5
    assert breakdown.preferred_score == 15.0
    assert breakdown.total_match_score == int(round(52.5 + 15.0))  # 68


def test_missing_required_with_all_preferred_matched():
    """Even if all preferred skills match, missing all required caps score strictly at 30."""
    skills = [
        SkillMatchItem(
            skill="Core Required 1",
            category=SkillCategory.REQUIRED,
            status=MatchStatus.MISSING,
        ),
        SkillMatchItem(
            skill="Core Required 2",
            category=SkillCategory.REQUIRED,
            status=MatchStatus.MISSING,
        ),
        SkillMatchItem(
            skill="Bonus Preferred 1",
            category=SkillCategory.PREFERRED,
            status=MatchStatus.MATCHED,
        ),
    ]

    breakdown = calculate_match_score(skills)
    assert breakdown.required_score == 0.0
    assert breakdown.preferred_score == 30.0
    assert breakdown.total_match_score == 30


def test_gaps_and_prioritized_suggestions():
    """Gaps are categorized by severity and prioritized properly."""
    skills = [
        SkillMatchItem(
            skill="PostgreSQL",
            category=SkillCategory.REQUIRED,
            status=MatchStatus.MISSING,
        ),
        SkillMatchItem(
            skill="Kubernetes",
            category=SkillCategory.PREFERRED,
            status=MatchStatus.MISSING,
        ),
    ]

    gaps, suggestions = build_gaps_and_suggestions(skills)
    assert len(gaps) == 2
    
    # Required missing should be critical
    req_gap = next(g for g in gaps if g.skill == "PostgreSQL")
    assert req_gap.severity == "critical"
    
    # Preferred missing should be minor
    pref_gap = next(g for g in gaps if g.skill == "Kubernetes")
    assert pref_gap.severity == "minor"

    # Highest priority suggestion should address required qualifications
    assert len(suggestions) >= 1
    assert suggestions[0].priority == 1
    assert "Required" in suggestions[0].area
