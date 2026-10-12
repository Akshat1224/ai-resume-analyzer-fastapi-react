import pytest
from app.schemas.resume_schema import (
    MatchStatus,
    SkillCategory,
    EvidenceSnippet,
)
from app.services.matching_service import (
    verify_evidence_against_pages,
    process_grounded_job_matching,
)


def test_verifiable_evidence_snippet():
    """Real evidence found on page 1 is verified as true."""
    pages = [
        {"page": 1, "text": "Senior Engineer with 6 years of experience building Python and FastAPI microservices."}
    ]
    evidence = [
        EvidenceSnippet(page=1, snippet="building Python and FastAPI microservices", verified=True)
    ]

    verified = verify_evidence_against_pages(evidence, pages)
    assert len(verified) == 1
    assert verified[0].verified is True


def test_hallucinated_evidence_rejected():
    """Evidence fabricated by the LLM that is not in the resume is rejected as unverified."""
    pages = [
        {"page": 1, "text": "Junior developer with HTML and CSS experience."}
    ]
    evidence = [
        EvidenceSnippet(page=1, snippet="Led architecture of high-scale Kubernetes clusters", verified=True)
    ]

    verified = verify_evidence_against_pages(evidence, pages)
    assert len(verified) == 1
    assert verified[0].verified is False


def test_skill_downgraded_when_evidence_is_hallucinated():
    """
    If AI claims a candidate has a skill but provides fabricated evidence,
    process_grounded_job_matching must downgrade status to UNVERIFIABLE.
    """
    pages = [
        {"page": 1, "text": "Worked as a Frontend Designer writing HTML and Tailwind CSS."}
    ]
    raw_ai_skills = [
        {
            "skill": "Rust Programming",
            "category": "required",
            "status": "matched",
            "evidence": [
                {"page": 1, "snippet": "Implemented high-performance Rust memory safety engines"}
            ],
            "reasoning": "Candidate has Rust experience."
        }
    ]

    result = process_grounded_job_matching(raw_ai_skills, pages)
    skill_item = result.skills_analysis[0]
    
    # Must NOT be MATCHED because the snippet was completely fabricated
    assert skill_item.status == MatchStatus.UNVERIFIABLE
    assert skill_item.evidence[0].verified is False
    assert "could not be verified" in skill_item.reasoning


def test_page_relocation_for_misattributed_page():
    """If candidate text is on page 2 but LLM incorrectly cited page 1, verify and correct page."""
    pages = [
        {"page": 1, "text": "Education: University of Technology, B.S. in Computer Science."},
        {"page": 2, "text": "Work History: Designed PostgreSQL databases and optimized slow queries."}
    ]
    evidence = [
        EvidenceSnippet(page=1, snippet="Designed PostgreSQL databases", verified=True)
    ]

    verified = verify_evidence_against_pages(evidence, pages)
    assert len(verified) == 1
    assert verified[0].verified is True
    assert verified[0].page == 2  # Relocated to actual page
