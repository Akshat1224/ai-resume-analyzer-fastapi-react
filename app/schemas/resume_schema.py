from pydantic import BaseModel
from typing import List

class ResumeAnalysisResponse(BaseModel):
    ats_score:int
    strengths:List[str]
    weaknesses:List[str]
    missing_skills:List[str]
    suggestions:List[str]