from pydantic import BaseModel
from typing import List


class InterviewRequest(BaseModel):
    role: str
    industry: str
    experience_level: str
    difficulty: str
    num_questions: int = 5


class Question(BaseModel):
    question: str
    hints: str
    sample_answer: str
    difficulty: str


class InterviewResponse(BaseModel):
    questions: List[Question]
