import re
from typing import List, Dict, Any, Optional
from app.schemas.resume_schema import (
    MatchStatus,
    SkillCategory,
    EvidenceSnippet,
    SkillMatchItem,
    ScoreBreakdown,
    GapItem,
    PrioritizedSuggestion,
    JobMatchAnalysis,
    ResumeAnalysisResponse,
)


def _normalize_text(text: str) -> str:
    """Normalize whitespace and lowercase for reliable snippet searching."""
    return re.sub(r"\s+", " ", text or "").strip().lower()


def verify_evidence_against_pages(
    evidence_list: List[EvidenceSnippet],
    pages: List[Dict[str, Any]]
) -> List[EvidenceSnippet]:
    """
    Verify that each claimed evidence snippet actually appears on the cited page.
    Prevents LLM hallucinations from fabricating candidate qualifications.
    """
    verified_evidence: List[EvidenceSnippet] = []
    page_map = {p["page"]: _normalize_text(p["text"]) for p in pages}
    all_text_normalized = " ".join(page_map.values())

    for item in evidence_list:
        snippet_norm = _normalize_text(item.snippet)
        if not snippet_norm or len(snippet_norm) < 3:
            verified_evidence.append(
                EvidenceSnippet(page=item.page, snippet=item.snippet, verified=False)
            )
            continue

        page_text = page_map.get(item.page, "")
        is_verified = False

        # Direct substring check on claimed page
        if snippet_norm in page_text:
            is_verified = True
        else:
            # Check 4-gram or keyword overlap (resilient to minor OCR/spacing discrepancies)
            snippet_words = [w for w in snippet_norm.split() if len(w) > 3]
            if snippet_words:
                matched_words = sum(1 for w in snippet_words if w in page_text)
                if (matched_words / len(snippet_words)) >= 0.75:
                    is_verified = True

        # Check if snippet appears on a different page (misattributed page number)
        if not is_verified and snippet_norm in all_text_normalized:
            # Locate actual page
            for p_num, p_text in page_map.items():
                if snippet_norm in p_text:
                    item.page = p_num
                    is_verified = True
                    break

        verified_evidence.append(
            EvidenceSnippet(
                page=item.page,
                snippet=item.snippet,
                verified=is_verified
            )
        )

    return verified_evidence


def calculate_match_score(skills: List[SkillMatchItem]) -> ScoreBreakdown:
    """
    Calculates transparent, deterministic match score using a documented weighted rubric:
      - Required Skills Pool: 70 maximum points
      - Preferred Skills Pool: 30 maximum points
      
    Weights per skill:
      - matched: 1.0
      - partially_matched: 0.5
      - unverifiable: 0.1
      - missing: 0.0
    """
    required_skills = [s for s in skills if s.category == SkillCategory.REQUIRED]
    preferred_skills = [s for s in skills if s.category == SkillCategory.PREFERRED]

    weight_map = {
        MatchStatus.MATCHED: 1.0,
        MatchStatus.PARTIALLY_MATCHED: 0.5,
        MatchStatus.UNVERIFIABLE: 0.1,
        MatchStatus.MISSING: 0.0,
    }

    # Required points
    req_matched = sum(1 for s in required_skills if s.status == MatchStatus.MATCHED)
    req_partial = sum(1 for s in required_skills if s.status == MatchStatus.PARTIALLY_MATCHED)
    
    if required_skills:
        req_points_sum = sum(weight_map.get(s.status, 0.0) for s in required_skills)
        req_score = (req_points_sum / len(required_skills)) * 70.0
    else:
        req_score = 70.0  # If no required skills explicitly stated, grant full baseline

    # Preferred points
    pref_matched = sum(1 for s in preferred_skills if s.status == MatchStatus.MATCHED)
    pref_partial = sum(1 for s in preferred_skills if s.status == MatchStatus.PARTIALLY_MATCHED)

    if preferred_skills:
        pref_points_sum = sum(weight_map.get(s.status, 0.0) for s in preferred_skills)
        pref_score = (pref_points_sum / len(preferred_skills)) * 30.0
    else:
        # If no preferred skills specified, re-allocate proportion to required
        pref_score = 30.0 if not required_skills else (req_score / 70.0) * 30.0

    req_score = max(0.0, min(70.0, req_score))
    pref_score = max(0.0, min(30.0, pref_score))
    total_score = int(round(req_score + pref_score))
    total_score = max(0, min(100, total_score))

    summary = (
        f"Evaluated {len(skills)} skills ({len(required_skills)} required, {len(preferred_skills)} preferred). "
        f"Matched {req_matched}/{len(required_skills)} required, {pref_matched}/{len(preferred_skills)} preferred."
    )

    return ScoreBreakdown(
        required_score=round(req_score, 1),
        preferred_score=round(pref_score, 1),
        total_match_score=total_score,
        required_matched_count=req_matched,
        required_partial_count=req_partial,
        required_total_count=len(required_skills),
        preferred_matched_count=pref_matched,
        preferred_partial_count=pref_partial,
        preferred_total_count=len(preferred_skills),
        rubric_formula="Score = (RequiredPoints / TotalRequired * 70) + (PreferredPoints / TotalPreferred * 30)",
        summary=summary,
    )


def build_gaps_and_suggestions(skills: List[SkillMatchItem]) -> tuple[List[GapItem], List[PrioritizedSuggestion]]:
    """Generate categorized gaps and prioritized suggestions from evaluated skills."""
    gaps: List[GapItem] = []
    suggestions: List[PrioritizedSuggestion] = []
    priority_counter = 1

    for s in skills:
        if s.status == MatchStatus.MISSING:
            severity = "critical" if s.category == SkillCategory.REQUIRED else "minor"
            recom = f"Add verifiable project experience, coursework, or certifications demonstrating {s.skill}."
            gaps.append(GapItem(skill=s.skill, category=s.category, severity=severity, recommendation=recom))
        elif s.status == MatchStatus.UNVERIFIABLE:
            severity = "moderate" if s.category == SkillCategory.REQUIRED else "minor"
            recom = f"Clarify claims regarding {s.skill} with concrete metrics and project context."
            gaps.append(GapItem(skill=s.skill, category=s.category, severity=severity, recommendation=recom))
        elif s.status == MatchStatus.PARTIALLY_MATCHED:
            severity = "moderate" if s.category == SkillCategory.REQUIRED else "minor"
            recom = f"Expand on how you applied {s.skill} to match the full role requirements."
            gaps.append(GapItem(skill=s.skill, category=s.category, severity=severity, recommendation=recom))

    # Priority 1: Critical Missing Required Skills
    critical_missing = [g.skill for g in gaps if g.severity == "critical"]
    if critical_missing:
        suggestions.append(
            PrioritizedSuggestion(
                priority=priority_counter,
                area="Required Qualifications",
                suggestion=f"Target missing core requirements: {', '.join(critical_missing[:3])}.",
            )
        )
        priority_counter += 1

    # Priority 2: Unverifiable / Partial Evidence
    unverifiable = [s.skill for s in skills if s.status in (MatchStatus.UNVERIFIABLE, MatchStatus.PARTIALLY_MATCHED)]
    if unverifiable:
        suggestions.append(
            PrioritizedSuggestion(
                priority=priority_counter,
                area="Evidence Substantiation",
                suggestion=f"Quantify and substantiate experience with {', '.join(unverifiable[:3])} with specific achievements and tools.",
            )
        )
        priority_counter += 1

    # Priority 3: Preferred Skills
    pref_missing = [g.skill for g in gaps if g.category == SkillCategory.PREFERRED]
    if pref_missing:
        suggestions.append(
            PrioritizedSuggestion(
                priority=priority_counter,
                area="Preferred Qualifications",
                suggestion=f"Bolster candidate competitive edge by highlighting preferred skills: {', '.join(pref_missing[:3])}.",
            )
        )

    return gaps, suggestions


def process_grounded_job_matching(
    raw_ai_skills: List[Dict[str, Any]],
    pages: List[Dict[str, Any]],
) -> JobMatchAnalysis:
    """
    Takes untrusted AI output, strictly validates and verifies evidence against actual resume text,
    and calculates the deterministic match score.
    """
    validated_skills: List[SkillMatchItem] = []

    for item in raw_ai_skills:
        skill_name = str(item.get("skill", "")).strip()
        if not skill_name:
            continue

        raw_cat = str(item.get("category", "required")).lower()
        category = SkillCategory.PREFERRED if "pref" in raw_cat else SkillCategory.REQUIRED

        raw_status = str(item.get("status", "missing")).lower()
        if "partial" in raw_status:
            status = MatchStatus.PARTIALLY_MATCHED
        elif "match" in raw_status:
            status = MatchStatus.MATCHED
        elif "unverif" in raw_status:
            status = MatchStatus.UNVERIFIABLE
        else:
            status = MatchStatus.MISSING

        raw_evidence = item.get("evidence", [])
        evidence_objs: List[EvidenceSnippet] = []
        if isinstance(raw_evidence, list):
            for ev in raw_evidence:
                if isinstance(ev, dict) and ev.get("snippet"):
                    evidence_objs.append(
                        EvidenceSnippet(
                            page=int(ev.get("page", 1)),
                            snippet=str(ev.get("snippet", "")).strip(),
                        )
                    )

        # Cross-verify evidence against real PDF text
        verified_evidence = verify_evidence_against_pages(evidence_objs, pages)
        has_verified_snippet = any(e.verified for e in verified_evidence)

        # Anti-hallucination check: if status is matched but no evidence was verified, downgrade
        reasoning = str(item.get("reasoning", "")).strip()
        if status in (MatchStatus.MATCHED, MatchStatus.PARTIALLY_MATCHED) and not has_verified_snippet:
            status = MatchStatus.UNVERIFIABLE
            reasoning = f"{reasoning} [Evidence snippet could not be verified in document text.]".strip()

        validated_skills.append(
            SkillMatchItem(
                skill=skill_name,
                category=category,
                status=status,
                evidence=verified_evidence,
                reasoning=reasoning,
            )
        )

    score_breakdown = calculate_match_score(validated_skills)
    gaps, suggestions = build_gaps_and_suggestions(validated_skills)

    return JobMatchAnalysis(
        score_breakdown=score_breakdown,
        skills_analysis=validated_skills,
        gaps=gaps,
        prioritized_suggestions=suggestions,
        total_skills_evaluated=len(validated_skills),
    )


def calculate_deterministic_ats_structural_score(
    doc_meta: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deterministic structural ATS score when no Job Description is provided.
    Evaluates section completeness, formatting, action verbs, and quantifiable impact.
    """
    full_text = doc_meta.get("full_text", "")
    text_lower = full_text.lower()
    total_words = doc_meta.get("total_words", 0)

    score = 0
    strengths: List[str] = []
    weaknesses: List[str] = []
    missing_skills: List[str] = []
    suggestions: List[str] = []

    # 1. Contact / Header (15 pts)
    has_email = bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", full_text))
    has_phone = bool(re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", full_text))
    if has_email and has_phone:
        score += 15
        strengths.append("Clear contact information (Email and Phone found).")
    elif has_email or has_phone:
        score += 8
        weaknesses.append("Incomplete contact details (missing phone or email).")
    else:
        weaknesses.append("Missing contact information header.")
        suggestions.append("Ensure your full name, email, phone number, and LinkedIn are at the top.")

    # 2. Key Sections (35 pts)
    sections = {
        "Experience": ["experience", "employment history", "work history"],
        "Education": ["education", "academic", "degree"],
        "Skills": ["skills", "technical skills", "technologies", "competencies"],
        "Projects / Summary": ["projects", "summary", "profile"],
    }
    found_sections = 0
    for sec_name, keywords in sections.items():
        if any(kw in text_lower for kw in keywords):
            found_sections += 1
        else:
            weaknesses.append(f"Missing distinct '{sec_name}' section header.")
            suggestions.append(f"Add a dedicated '{sec_name}' section to improve ATS parsing.")

    section_score = int((found_sections / len(sections)) * 35)
    score += section_score
    if found_sections >= 3:
        strengths.append("Well-structured document with standard ATS section headings.")

    # 3. Action Verbs & Metrics (30 pts)
    action_verbs = ["led", "developed", "architected", "built", "managed", "created", "increased", "reduced", "delivered", "optimized"]
    verb_matches = sum(1 for v in action_verbs if re.search(rf"\b{v}\b", text_lower))
    if verb_matches >= 4:
        score += 15
        strengths.append(f"Strong action-oriented phrasing used ({verb_matches}+ strong verbs).")
    elif verb_matches >= 2:
        score += 8
    else:
        weaknesses.append("Limited action verbs in experience descriptions.")
        suggestions.append("Begin bullet points with strong action verbs (e.g., Developed, Optimized, Architected).")

    # Metrics / numbers
    metric_matches = len(re.findall(r"\b\d+([%kKmM+]|\s*(percent|users|revenue|reduction|increase))\b", text_lower))
    if metric_matches >= 3:
        score += 15
        strengths.append("Demonstrated quantifiable impact with metrics and percentages.")
    elif metric_matches >= 1:
        score += 8
        weaknesses.append("Few quantifiable metrics in project bullet points.")
        suggestions.append("Include measurable results (e.g., 'improved performance by 25%').")
    else:
        weaknesses.append("Lacks quantifiable business outcomes and metrics.")
        suggestions.append("Add metrics and measurable outcomes to prove your impact.")

    # 4. Content Length & Balance (20 pts)
    if 250 <= total_words <= 1200:
        score += 20
        strengths.append("Optimal resume length and word density for single/two-page review.")
    elif total_words < 250:
        score += 5
        weaknesses.append("Resume appears too brief (under 250 words).")
        suggestions.append("Expand on your technical achievements and project details.")
    else:
        score += 12
        weaknesses.append("High word count; consider condensing for clearer readability.")

    score = max(0, min(100, score))

    return {
        "ats_score": score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "missing_skills": missing_skills,
        "suggestions": suggestions,
    }
