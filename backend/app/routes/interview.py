"""
Interview API endpoints
POST /api/interview/start - Start new interview
POST /api/interview/answer - Submit answer
GET /api/interview/{session_id} - Get session status
POST /api/interview/{session_id}/finish - Complete interview
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.models.interview_models import (
    InterviewStartRequest, InterviewStartResponse, QuestionResponse, AIEvaluation,
    CandidateAnswerRequest, AnswerResponse, AnswerFeedback,
    SessionStatus, InterviewSummary, HintRequest, HintResponse
)
from app.services.question_repository import get_question_repository
from app.services.question_engine import QuestionSelectionEngine
from app.services.interview_service import InterviewService
from app.auth import assert_session_owner, require_current_user
from app.database import DB_PATH, get_connection
from app.services.gemini_provider import ProviderTimeoutError, ProviderUnavailableError
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview", tags=["interview"])

# Initialize services (lazy load)
_question_repo = None
_question_engine = None
_interview_service = None


def _get_services():
    """Lazy initialize services."""
    global _question_repo, _question_engine, _interview_service
    
    if _question_repo is None:
        _question_repo = get_question_repository()
    if _question_engine is None:
        _question_engine = QuestionSelectionEngine(_question_repo)
    if _interview_service is None:
        _interview_service = InterviewService(str(DB_PATH), _question_repo, _question_engine)
    
    return _question_repo, _question_engine, _interview_service


@router.post("/start", response_model=InterviewStartResponse)
def start_interview(request: InterviewStartRequest, current_user=Depends(require_current_user)):
    """
    Start new interview session.
    
    Creates session in database, selects first question.
    """
    try:
        _, _, interview_service = _get_services()
        
        # Create session
        session_data = interview_service.create_interview_session(
            job_role=request.job_role,
            skills=request.skills,
            total_questions=request.total_questions,
            user_id=current_user["id"] if current_user else None,
            interview_type=request.interview_type,
            difficulty=request.difficulty,
        )
        
        # Build response
        current_question_data = session_data['first_question']
        if not current_question_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to select first question"
            )
        
        current_question = QuestionResponse(**current_question_data)
        
        return InterviewStartResponse(
            session_id=session_data['session_id'],
            job_role=session_data['job_role'],
            total_questions=session_data['total_questions'],
            skills=session_data['skills'],
            current_question=current_question
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting interview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start interview: {str(e)}"
        )


@router.post("/answer", response_model=AnswerResponse)
def submit_answer(request: CandidateAnswerRequest, current_user=Depends(require_current_user)):
    """
    Submit candidate answer and get AI evaluation + next question.
    
    Uses LangChain + OpenAI to intelligently evaluate answer,
    records in database, selects next question using adaptive engine.
    """
    try:
        assert_session_owner(request.session_id, current_user)
        # Validate inputs
        if not request.answer.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Answer cannot be empty"
            )
        
        _, _, interview_service = _get_services()
        
        # Submit answer (with AI evaluation)
        result = interview_service.submit_answer(
            session_id=request.session_id,
            question_id=request.question_id,
            answer_text=request.answer,
            auto_expired=request.auto_expired,
        )
        
        # Build response
        if result.get("evaluation_status") != "complete":
            return AnswerResponse(
                question_number=result["question_number"],
                evaluation=None,
                answer_saved=True,
                evaluation_status=result.get("evaluation_status", "failed"),
                message="Your answer was saved, but AI evaluation is temporarily unavailable. You can retry evaluation.",
            )

        evaluation = AIEvaluation(
            score=result['evaluation']['score'],
            correctness=result['evaluation']['correctness'],
            relevance=result['evaluation']['relevance'],
            completeness=result['evaluation']['completeness'],
            strengths=result['evaluation']['strengths'],
            weaknesses=result['evaluation']['weaknesses'],
            feedback=result['evaluation']['feedback'],
            recommended_difficulty=result['evaluation']['recommended_difficulty']
        )
        
        next_question = None
        if 'next_question' in result and result['next_question']:
            next_question = QuestionResponse(**result['next_question'])
        
        return AnswerResponse(
            question_number=result['question_number'],
            evaluation=evaluation,
            next_question=next_question,
            interview_complete=result.get('interview_complete', False)
        )
    
    except (ProviderUnavailableError, RuntimeError) as e:
        logger.warning("Answer saved but evaluation failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "EVALUATION_UNAVAILABLE",
                "message": "Your answer was saved, but AI evaluation is temporarily unavailable. You can retry evaluation.",
                "answer_saved": True,
            },
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit answer: {str(e)}"
        )


@router.post("/{session_id}/hint", response_model=HintResponse)
def get_hint(session_id: str, request: HintRequest, current_user=Depends(require_current_user)):
    """Return a grounded hint for the question currently being answered."""
    try:
        assert_session_owner(session_id, current_user)
        _, _, interview_service = _get_services()
        hint = interview_service.get_hint(session_id, request.question_id)
        return HintResponse(session_id=session_id, question_id=request.question_id, hint=hint)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error creating interview hint: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create hint") from exc


@router.post("/{session_id}/answers/{question_id}/retry", response_model=AnswerResponse)
def retry_answer_evaluation(session_id: str, question_id: str, current_user=Depends(require_current_user)):
    """Retry evaluation for an answer already persisted by the server."""
    try:
        assert_session_owner(session_id, current_user)
        _, _, interview_service = _get_services()
        result = interview_service.retry_evaluation(session_id, question_id)
        evaluation = result.get("evaluation")
        return AnswerResponse(
            question_number=result["question_number"],
            evaluation=AIEvaluation(**evaluation) if evaluation else None,
            next_question=QuestionResponse(**result["next_question"]) if result.get("next_question") else None,
            interview_complete=result.get("interview_complete", False),
            answer_saved=True,
            evaluation_status=result.get("evaluation_status", "failed"),
            message=result.get("message", ""),
        )
    except (ProviderUnavailableError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={
            "code": "EVALUATION_UNAVAILABLE",
            "answer_saved": True,
            "message": "Your answer was saved, but AI evaluation is temporarily unavailable. You can retry evaluation.",
        }) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{session_id}/integrity")
def record_integrity_event(session_id: str, event: dict, current_user=Depends(require_current_user)):
    assert_session_owner(session_id, current_user)
    _, _, interview_service = _get_services()
    interview_service.record_integrity_event(session_id, event)
    return {"success": True}


@router.post("/{session_id}/expire")
def expire_interview(session_id: str, current_user=Depends(require_current_user)):
    assert_session_owner(session_id, current_user)
    _, _, interview_service = _get_services()
    return {"expired": interview_service.expire_interview(session_id)}


@router.get("/history")
def get_interview_history(current_user=Depends(require_current_user)):
    """Return only the authenticated user's interview history."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT s.session_id, s.job_role, s.total_questions, s.status,
                   s.created_at, s.interview_type, s.difficulty, r.report_json
            FROM interview_sessions AS s
            LEFT JOIN interview_reports AS r ON r.session_id = s.session_id
            WHERE s.user_id = ?
            ORDER BY COALESCE(r.updated_at, s.created_at) DESC
            """,
            (current_user["id"],),
        ).fetchall()
    finally:
        conn.close()

    history = []
    for row in rows:
        report = {}
        if row["report_json"]:
            try:
                report = json.loads(row["report_json"])
            except (TypeError, ValueError):
                report = {}
        history.append({
            "sessionId": row["session_id"], "jobRole": row["job_role"],
            "date": report.get("interview_date") or row["created_at"],
            "questions": report.get("questions_answered", 0),
            "totalQuestions": report.get("total_questions", row["total_questions"]),
            "correctCount": report.get("correct_count", 0), "wrongCount": report.get("wrong_count", 0),
            "accuracy": report.get("accuracy", 0), "score": report.get("overall_score", 0),
            "performance": report.get("performance_level", "In progress" if row["status"] != "completed" else "Completed"),
            "type": row["interview_type"] or "Technical interview", "status": row["status"],
        })
    return history


@router.get("/{session_id}", response_model=SessionStatus)
def get_interview_status(session_id: str, current_user=Depends(require_current_user)):
    """
    Get current interview session status.
    
    Returns: question progress, skills covered, current status.
    """
    try:
        assert_session_owner(session_id, current_user)
        _, _, interview_service = _get_services()
        
        status_data = interview_service.get_session_status(session_id)
        
        return SessionStatus(**status_data)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session status: {str(e)}"
        )


@router.post("/{session_id}/finish", response_model=InterviewSummary)
def finish_interview(session_id: str, current_user=Depends(require_current_user)):
    """
    Complete interview and get summary.
    
    Returns: average score, score by skill, interview status.
    
    Note: Advanced reporting features (detailed insights, 
    recommendations) will be added in Phase 4.
    """
    try:
        assert_session_owner(session_id, current_user)
        _, _, interview_service = _get_services()
        
        summary_data = interview_service.finish_interview(session_id)
        
        return InterviewSummary(
            session_id=summary_data['session_id'],
            status=summary_data['status'],
            total_questions=summary_data.get('total_questions', 0),
            average_score=summary_data.get('average_score', 0.0),
            total_score=summary_data.get('total_score', 0.0),
            skill_scores=summary_data.get('skill_scores', {}),
            message=summary_data.get('message', '')
        )
    
    except Exception as e:
        logger.error(f"Error finishing interview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finish interview: {str(e)}"
        )
