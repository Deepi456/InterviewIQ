"""Regression coverage for automatic completion after the final answer."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import DB_PATH, get_connection, init_database
from app.services.interview_service import InterviewService
from app.services.question_engine import QuestionSelectionEngine
from app.services.question_repository import get_question_repository


def test_final_answer_commits_completed_session():
    """The final answer keeps the response flag and commits completed status."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_database()

    repo = get_question_repository()
    service = InterviewService(
        str(DB_PATH),
        repo,
        QuestionSelectionEngine(repo),
    )
    session = service.create_interview_session(
        job_role="Python Developer",
        skills=["Python"],
        total_questions=1,
    )

    evaluation = SimpleNamespace(
        score=8,
        correctness="Good",
        relevance="High",
        completeness="Comprehensive",
        strengths=["Clear explanation"],
        weaknesses=[],
        feedback="Strong answer",
        recommended_difficulty="Medium",
    )

    with patch.object(service, "_evaluate_answer", return_value=evaluation):
        result = service.submit_answer(
            session_id=session["session_id"],
            question_id=session["first_question"]["question_id"],
            answer_text="A complete answer",
        )

    assert result["interview_complete"] is True
    assert result.get("next_question") is None

    conn = get_connection()
    row = conn.execute(
        "SELECT status, completed_at FROM interview_sessions WHERE session_id = ?",
        (session["session_id"],),
    ).fetchone()
    conn.close()

    assert row["status"] == "completed"
    assert row["completed_at"] is not None
