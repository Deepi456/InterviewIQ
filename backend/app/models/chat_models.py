"""Request and response models for the InterviewIQ AI Coach."""

from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    mode: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    response: str = ""
    conversation_id: str = ""
    message: str = ""
    suggestions: list[str] = Field(default_factory=list)
    mode: str = "general"
