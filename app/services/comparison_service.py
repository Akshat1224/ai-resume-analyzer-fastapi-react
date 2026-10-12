from typing import Dict, Any, List
from app.schemas.resume_schema import (
    ResumeAnalysisResponse,
    ResumeComparisonResponse,
    MatchStatus,
)


def compare_resume_analyses(
    v1: ResumeAnalysisResponse,
    v2: ResumeAnalysisResponse,
) -> ResumeComparisonResponse:
    """
    Compares two resume analyses against the same job description.
    Detects score deltas, added/removed skills, dropped evidence, and unsupported claims.
    """
    score_v1 = v1.ats_score
    score_v2 = v2.ats_score
    score_delta = score_v2 - score_v1

    # Extract skill dictionaries
    skills_v1_map = {}
    if v1.job_match:
        for s in v1.job_match.skills_analysis:
            skills_v1_map[s.skill.lower()] = s

    skills_v2_map = {}
    if v2.job_match:
        for s in v2.job_match.skills_analysis:
            skills_v2_map[s.skill.lower()] = s

    v1_matched_names = {
        name for name, s in skills_v1_map.items() if s.status == MatchStatus.MATCHED
    }
    v2_matched_names = {
        name for name, s in skills_v2_map.items() if s.status == MatchStatus.MATCHED
    }

    added_skills = [
        skills_v2_map[name].skill
        for name in (v2_matched_names - v1_matched_names)
    ]
    removed_skills = [
        skills_v1_map[name].skill
        for name in (v1_matched_names - v2_matched_names)
    ]
    retained_skills = [
        skills_v2_map[name].skill
        for name in (v1_matched_names & v2_matched_names)
    ]

    # Check for removed evidence (skills matched in both, but V2 has fewer verified evidence snippets)
    removed_evidence = []
    for name in (v1_matched_names & v2_matched_names):
        s1 = skills_v1_map[name]
        s2 = skills_v2_map[name]
        s1_verified_count = sum(1 for e in s1.evidence if e.verified)
        s2_verified_count = sum(1 for e in s2.evidence if e.verified)
        if s1_verified_count > s2_verified_count:
            removed_evidence.append(s2.skill)

    # Unsupported claims in V2: any skill marked UNVERIFIABLE
    unsupported_claims = [
        s.skill
        for s in skills_v2_map.values()
        if s.status == MatchStatus.UNVERIFIABLE
    ]

    # Gaps resolved vs new gaps
    v1_gaps = {g.skill.lower() for g in (v1.job_match.gaps if v1.job_match else [])}
    v2_gaps = {g.skill.lower() for g in (v2.job_match.gaps if v2.job_match else [])}

    gaps_resolved = [
        skills_v1_map[name].skill if name in skills_v1_map else name.title()
        for name in (v1_gaps - v2_gaps)
    ]
    new_gaps = [
        skills_v2_map[name].skill if name in skills_v2_map else name.title()
        for name in (v2_gaps - v1_gaps)
    ]

    # Formulate verdict
    if score_delta > 5:
        verdict = (
            f"Version 2 demonstrates significant improvement (+{score_delta} points). "
            f"Successfully added {len(added_skills)} verified qualifications and resolved {len(gaps_resolved)} gaps."
        )
    elif score_delta < -5:
        verdict = (
            f"Version 2 is a regression ({score_delta} points). "
            f"Lost {len(removed_skills)} previously matched qualifications ({', '.join(removed_skills[:3])})."
        )
    else:
        verdict = (
            f"Version 2 maintains comparable qualification match to Version 1 (delta: {score_delta:+d} points). "
            f"Retained {len(retained_skills)} core skills."
        )

    return ResumeComparisonResponse(
        base_version_score=score_v1,
        target_version_score=score_v2,
        score_delta=score_delta,
        added_skills=added_skills,
        removed_skills=removed_skills,
        retained_skills=retained_skills,
        removed_evidence=removed_evidence,
        unsupported_claims=unsupported_claims,
        gaps_resolved=gaps_resolved,
        new_gaps=new_gaps,
        verdict=verdict,
    )
