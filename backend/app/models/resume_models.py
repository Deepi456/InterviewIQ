"""Models for grounded resume tailoring."""

from typing import List
from pydantic import BaseModel, Field


class ResumeTailorResponse(BaseModel):
    tailoring_id: str
    job_match_score: int = Field(ge=0, le=100)
    strong_matches: List[str]
    skill_gaps: List[str]
    recommendations: List[str]
    tailored_resume: str


class ResumeTextRequest(BaseModel):
    resume_text: str = Field(..., min_length=40, max_length=50000)
    job_description: str = Field(..., min_length=20, max_length=30000)