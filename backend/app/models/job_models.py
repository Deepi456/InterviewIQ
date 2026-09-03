"""
Pydantic models for job analysis and skill extraction.
"""
from typing import List, Literal
from pydantic import BaseModel, Field


class SkillModel(BaseModel):
    """Model representing a single skill extracted from a job description."""
    
    name: str = Field(..., description="Name of the skill")
    importance: Literal["high", "medium", "low"] = Field(..., description="Importance level")
    category: str = Field(..., description="Skill category (e.g., Programming, AI/ML, Database)")


class JobAnalysisRequest(BaseModel):
    """Request model for job description analysis."""
    
    job_role: str = Field(..., description="Target job role", min_length=1)
    job_description: str = Field(..., description="Job description text", min_length=10)


class JobAnalysisResponse(BaseModel):
    """Response model for job description analysis."""
    
    job_role: str = Field(..., description="Target job role")
    skills: List[SkillModel] = Field(..., description="List of extracted skills")
    recommended_topics: List[str] = Field(..., description="Recommended interview topics")
