"""
Pydantic models for interview API endpoints.
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any


class InterviewStartRequest(BaseModel):
    """Request to start new interview session."""
    job_role: str = Field(..., min_length=1, description="Job role to interview for")
    skills: List[str] = Field(..., min_items=1, description="Required skills from job analysis")
    total_questions: int = Field(default=10, ge=1, le=50, description="Number of questions in interview")
    interview_type: str = Field(default="Technical", min_length=1)
    difficulty: str = Field(default="Medium", min_length=1)


class QuestionResponse(BaseModel):
    """Interview question to display to candidate."""
    question_number: int
    total_questions: int
    question_id: str
    question: str
    skill: str
    difficulty: str
    category: str


class InterviewStartResponse(BaseModel):
    """Response from starting interview."""
    session_id: str
    job_role: str
    total_questions: int
    skills: List[str]
    current_question: QuestionResponse


class CandidateAnswerRequest(BaseModel):
    """Candidate's answer submission."""
    session_id: str
    question_id: str
    answer: str = Field(..., min_length=1, description="Candidate's answer text")
    auto_expired: bool = False


class HintRequest(BaseModel):
    """Request for a question-specific interview hint."""
    question_id: str = Field(..., min_length=1)


class HintResponse(BaseModel):
    """A non-answer-revealing hint grounded in the current question."""
    session_id: str
    question_id: str
    hint: str


class AIEvaluation(BaseModel):
    """AI-powered evaluation of answer."""
    score: int = Field(..., ge=0, le=10, description="Score 0-10")
    correctness: str = Field(..., description="Poor/Fair/Good/Excellent")
    relevance: str = Field(..., description="Low/Medium/High")
    completeness: str = Field(..., description="Incomplete/Partial/Moderate/Comprehensive")
    strengths: List[str] = Field(default_factory=list, description="Answer strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Areas for improvement")
    feedback: str = Field(..., description="Constructive feedback")
    recommended_difficulty: str = Field(..., description="Recommended next difficulty")
    ideal_answer: Optional[str] = Field(default=None, description="Expected ideal answer")
    expected_answer: Optional[str] = Field(default=None, description="Expected ideal answer alias")
    improvement: Optional[str] = Field(default="", description="Specific actionable improvement advice")
    result: Optional[str] = Field(default=None, description="Correct/Wrong verdict")


class AnswerFeedback(BaseModel):
    """Feedback on answer (deprecated - use AIEvaluation)."""
    question_number: int
    score: float = Field(..., ge=0, le=10, description="Score 0-10")
    feedback: str


class AnswerResponse(BaseModel):
    """Response after submitting answer."""
    question_number: int
    evaluation: Optional[AIEvaluation] = None
    next_question: Optional[QuestionResponse] = None
    interview_complete: Optional[bool] = False
    answer_saved: bool = False
    evaluation_status: str = "pending"
    message: str = ""


class SessionStatus(BaseModel):
    """Interview session status."""
    session_id: str
    job_role: str
    status: str  # 'in_progress' or 'completed'
    current_question_number: int
    total_questions: int
    progress: float  # 0.0 to 1.0
    skills_covered: List[str]
    created_at: str
    started_at: Optional[str] = None
    current_question: Optional[QuestionResponse] = None
    evaluation_status: Optional[str] = None
    saved_answer: Optional[str] = None
    saved_question_id: Optional[str] = None
    expires_at: Optional[str] = None
    remaining_seconds: Optional[int] = None


class SkillScore(BaseModel):
    """Score for individual skill."""
    skill: str
    avg_score: float
    count: int


class InterviewSummary(BaseModel):
    """Interview completion summary."""
    session_id: str
    status: str
    total_questions: int
    average_score: float
    total_score: float
    skill_scores: Dict[str, SkillScore]
    message: str


# ============================================
# Phase 5: Report Generation Models
# ============================================

class SkillPerformance(BaseModel):
    """Skill performance in report."""
    skill: str
    avg_score: float
    question_count: int
    performance_level: str  # "Strong", "Developing", "Needs Improvement"


class StrengthItem(BaseModel):
    """Identified strength."""
    skill: str
    reason: str


class WeakAreaItem(BaseModel):
    """Identified weak area."""
    skill: str
    reason: str
    priority: str  # "High", "Medium", "Low"


class ConceptGap(BaseModel):
    """Identified concept gap."""
    skill: str
    concept: str
    reason: str
    priority: str  # "High", "Medium", "Low"


class Recommendation(BaseModel):
    """Personalized recommendation."""
    skill: str
    topic: str
    action: str
    priority: str  # "High", "Medium", "Low"
    resources: Optional[List[str]] = None


class PreparationDay(BaseModel):
    """Single day in preparation plan."""
    day: int
    focus: str  # Primary skill focus
    topics: List[str]
    tasks: List[str]
    estimated_hours: float = Field(default=2.0)


class ReportQuestionItem(BaseModel):
    """Question review item in performance report."""
    question_number: int
    question_id: str
    question: str
    skill: str
    difficulty: str
    candidate_answer: str
    expected_answer: str
    result: str  # "Correct" or "Wrong" or "Unavailable"
    score: Optional[float] = None
    correctness: Optional[str] = None
    evaluation: str = ""
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    improvement: str = ""


class InterviewReport(BaseModel):
    """Complete interview report with AI analysis."""
    session_id: str
    interview_id: Optional[str] = None
    job_role: str
    role: Optional[str] = None
    interview_date: str
    date: Optional[str] = None
    total_questions: int
    questions_answered: int
    completion_status: str
    correct_count: int = 0
    wrong_count: int = 0
    accuracy: float = 0.0
    overall_score: float
    overall_score_numeric: int
    performance_level: str
    summary: str
    questions: List[ReportQuestionItem] = Field(default_factory=list)
    skill_scores: List[SkillPerformance] = Field(default_factory=list)
    strengths: List[StrengthItem] = Field(default_factory=list)
    weak_areas: List[WeakAreaItem] = Field(default_factory=list)
    areas_to_improve: List[WeakAreaItem] = Field(default_factory=list)
    concept_gaps: List[ConceptGap] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)
    preparation_plan: List[PreparationDay] = Field(default_factory=list)
    generated_at: str
    ai_generated: bool = True

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "interview_id" not in data and "session_id" in data:
                data["interview_id"] = data["session_id"]
            if "session_id" not in data and "interview_id" in data:
                data["session_id"] = data["interview_id"]
            if "role" not in data and "job_role" in data:
                data["role"] = data["job_role"]
            if "job_role" not in data and "role" in data:
                data["job_role"] = data["role"]
            if "date" not in data and "interview_date" in data:
                data["date"] = data["interview_date"]
            if "interview_date" not in data and "date" in data:
                data["interview_date"] = data["date"]
            if "areas_to_improve" not in data and "weak_areas" in data:
                data["areas_to_improve"] = data["weak_areas"]
            if "weak_areas" not in data and "areas_to_improve" in data:
                data["weak_areas"] = data["areas_to_improve"]
        return data


class SendReportRequest(BaseModel):
    """Request payload for sending a report by email via n8n."""
    candidate_email: str = Field(..., min_length=3, description="Candidate email address")
    resend: bool = Field(default=False, description="Allow resending if a prior delivery exists")


class SendReportResponse(BaseModel):
    """Response payload for report delivery automation."""
    success: bool
    message: str
    automation_status: str