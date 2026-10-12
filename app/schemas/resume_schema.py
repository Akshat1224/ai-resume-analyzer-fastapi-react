from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MatchStatus(str, Enum):
    MATCHED = "matched"
    PARTIALLY_MATCHED = "partially_matched"
    MISSING = "missing"
    UNVERIFIABLE = "unverifiable"


class SkillCategory(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class EvidenceSnippet(BaseModel):
    page: int = Field(..., description="1-indexed page number in the resume where the evidence appears")
    snippet: str = Field(..., description="Verbatim or near-verbatim extract supporting the skill")
    verified: bool = Field(default=True, description="Whether this snippet was verified against actual document text")


class SkillMatchItem(BaseModel):
    skill: str = Field(..., description="Name of the skill or requirement")
    category: SkillCategory = Field(..., description="Whether this skill is required or preferred")
    status: MatchStatus = Field(..., description="Match evaluation status")
    evidence: List[EvidenceSnippet] = Field(default_factory=list, description="Evidence snippets from resume")
    reasoning: str = Field(default="", description="Justification for this match categorization")


class ScoreBreakdown(BaseModel):
    required_score: float = Field(..., ge=0.0, le=70.0, description="Points earned for required skills (max 70)")
    preferred_score: float = Field(..., ge=0.0, le=30.0, description="Points earned for preferred skills (max 30)")
    total_match_score: int = Field(..., ge=0, le=100, description="Deterministic overall match score (0-100)")
    required_matched_count: int = Field(default=0, ge=0)
    required_partial_count: int = Field(default=0, ge=0)
    required_total_count: int = Field(default=0, ge=0)
    preferred_matched_count: int = Field(default=0, ge=0)
    preferred_partial_count: int = Field(default=0, ge=0)
    preferred_total_count: int = Field(default=0, ge=0)
    rubric_formula: str = Field(
        default="Score = (RequiredPoints / MaxRequired * 70) + (PreferredPoints / MaxPreferred * 30)",
        description="Documented rubric formula used"
    )
    summary: str = Field(default="", description="Executive summary of the match calculation")


class GapItem(BaseModel):
    skill: str
    category: SkillCategory
    severity: str = Field(default="critical", description="critical | moderate | minor")
    recommendation: str = Field(..., description="Actionable recommendation to address this gap")


class PrioritizedSuggestion(BaseModel):
    priority: int = Field(..., ge=1, description="1 is highest priority")
    area: str = Field(..., description="Category or skill area")
    suggestion: str = Field(..., description="Concrete, actionable improvement suggestion")


class JobMatchAnalysis(BaseModel):
    score_breakdown: ScoreBreakdown
    skills_analysis: List[SkillMatchItem] = Field(default_factory=list)
    gaps: List[GapItem] = Field(default_factory=list)
    prioritized_suggestions: List[PrioritizedSuggestion] = Field(default_factory=list)
    total_skills_evaluated: int = Field(default=0)


class ResumeAnalysisResponse(BaseModel):
    # Backward-compatible fields
    ats_score: int = Field(..., ge=0, le=100, description="Overall ATS / match score")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    
    # Phase 1 structured evidence & match analysis
    job_match: Optional[JobMatchAnalysis] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResumeComparisonResponse(BaseModel):
    base_version_score: int
    target_version_score: int
    score_delta: int
    added_skills: List[str] = Field(default_factory=list, description="Skills newly verified in V2")
    removed_skills: List[str] = Field(default_factory=list, description="Skills verified in V1 but dropped in V2")
    retained_skills: List[str] = Field(default_factory=list)
    removed_evidence: List[str] = Field(default_factory=list, description="Skills whose supporting evidence was removed in V2")
    unsupported_claims: List[str] = Field(default_factory=list, description="Skills claimed in V2 lacking verified evidence")
    gaps_resolved: List[str] = Field(default_factory=list, description="Gaps from V1 fixed in V2")
    new_gaps: List[str] = Field(default_factory=list, description="New gaps created in V2")
    verdict: str