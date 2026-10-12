from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class InterviewRequest(BaseModel):
    role: str
    industry: str
    experience_level: str
    difficulty: str = "medium"
    num_questions: int = Field(default=5, ge=1, le=10)
    skill_gaps: Optional[List[str]] = Field(
        default=None,
        description="Target job-specific skill gaps identified from resume analysis"
    )
    session_id: Optional[str] = Field(default="default", description="Workspace/session identifier")


class Question(BaseModel):
    question: str
    hints: str
    sample_answer: str
    difficulty: str
    target_skill: Optional[str] = None


class InterviewResponse(BaseModel):
    questions: List[Question]
    session_id: Optional[str] = "default"
    adapted_from_gaps: bool = False


class PracticeAttemptRequest(BaseModel):
    question: str
    target_skill: str
    difficulty: str
    user_answer: str = Field(..., min_length=3)
    session_id: Optional[str] = "default"


class PracticeAttemptResponse(BaseModel):
    attempt_id: str
    target_skill: str
    score: int = Field(..., ge=0, le=100)
    feedback: str
    suggested_improvements: List[str] = Field(default_factory=list)
    next_difficulty: str


class SkillProgress(BaseModel):
    skill: str
    attempts_count: int
    average_score: float
    current_difficulty: str
    mastery_status: str  # "needs_practice" | "proficient" | "mastered"


class ProgressSummaryResponse(BaseModel):
    session_id: str
    total_attempts: int
    skills_tracked: List[SkillProgress]
    recommended_focus: List[str]
