"""
Unit tests for Phase 5 Report System, Question-by-Question review, PDF export,
and correct/wrong counting integrity.
"""

import json
import sqlite3
from datetime import datetime
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import DB_PATH, get_connection
from app.services.interview_service import determine_question_result, get_interview_service
from app.services.report_service import get_report_service
from app.services.report_export_service import get_export_service
from app.services.question_repository import get_question_repository
from app.models.interview_models import InterviewReport, ReportQuestionItem


def test_determine_question_result():
    """Verify centralized question result calculation logic."""
    # Missing / unevaluated
    assert determine_question_result(None, None) == "Unavailable"
    assert determine_question_result(None, "") == "Unavailable"

    # Explicit correctness verdicts
    assert determine_question_result(None, "Good") == "Correct"
    assert determine_question_result(None, "Excellent") == "Correct"
    assert determine_question_result(None, "Correct") == "Correct"
    assert determine_question_result(None, "Poor") == "Wrong"
    assert determine_question_result(None, "Incorrect") == "Wrong"
    assert determine_question_result(None, "Wrong") == "Wrong"

    # Score threshold (>= 6.0 is Correct, < 6.0 is Wrong)
    assert determine_question_result(10.0, None) == "Correct"
    assert determine_question_result(8.5, None) == "Correct"
    assert determine_question_result(6.0, None) == "Correct"
    assert determine_question_result(5.9, None) == "Wrong"
    assert determine_question_result(0.0, None) == "Wrong"


def test_build_interview_report_integrity():
    """Verify full question-by-question review and metric calculations."""
    conn = get_connection()
    session_id = f"test-report-{datetime.now().timestamp()}"
    
    # Create test session
    conn.execute(
        """
        INSERT INTO interview_sessions 
        (session_id, job_role, status, current_question_number, total_questions, skills_json, created_at)
        VALUES (?, ?, 'completed', 5, 5, ?, ?)
        """,
        (session_id, "Senior Python Developer", json.dumps(["Python", "SQL", "System Design"]), datetime.now().isoformat())
    )

    # 5 test questions with known evaluations: 3 correct, 2 wrong
    test_answers = [
        (1, "py_1", "Python", "Medium", "Lists are mutable and tuples are immutable.", 8.5, "Good", "Strong answer.", "Lists are mutable and tuples are immutable in Python.", ["Correct syntax"], [], "Mention hashability."),
        (2, "py_2", "Python", "Hard", "A generator uses yield instead of return.", 9.0, "Excellent", "Excellent explanation.", "Generators use yield to lazily produce values.", ["Detailed reasoning"], [], "Give an example of itertools."),
        (3, "sql_1", "SQL", "Medium", "I do not know how window functions work.", 2.0, "Poor", "Incorrect explanation.", "Window functions calculate across a set of table rows related to current row.", [], ["Missing OVER clause"], "Study ROW_NUMBER and RANK."),
        (4, "sys_1", "System Design", "Hard", "Consistent hashing reduces remapping keys when resizing cache nodes.", 7.5, "Good", "Clear explanation.", "Consistent hashing distributes keys across a hash ring.", ["Ring concept included"], [], "Discuss virtual nodes."),
        (5, "sql_2", "SQL", "Easy", "SELECT * FROM table", 4.0, "Fair", "Incomplete answer.", "Use GROUP BY with aggregate functions to summarize records.", [], ["Missing GROUP BY"], "Practice aggregation queries.")
    ]

    for q_num, q_id, skill, diff, ans, score, correctness, feedback, ideal, strengths, weaknesses, improvement in test_answers:
        eval_dict = {
            "score": score,
            "correctness": correctness,
            "feedback": feedback,
            "ideal_answer": ideal,
            "expected_answer": ideal,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "improvement": improvement,
            "result": determine_question_result(score, correctness),
            "relevance": "High",
            "completeness": "Moderate",
            "recommended_difficulty": diff
        }
        conn.execute(
            """
            INSERT INTO candidate_answers
            (session_id, question_id, answer, score, feedback, skill, difficulty, evaluation_status, evaluation_json, evaluated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'complete', ?, ?)
            """,
            (session_id, q_id, ans, score, feedback, skill, diff, json.dumps(eval_dict), datetime.now().isoformat())
        )

    conn.commit()
    conn.close()

    # Generate report
    repo = get_question_repository()
    report_service = get_report_service(str(DB_PATH), repo)
    report = report_service.build_interview_report(session_id, preparation_days=5)

    # Validate report metrics
    assert report.total_questions == 5
    assert report.questions_answered == 5
    assert report.correct_count == 3
    assert report.wrong_count == 2
    assert report.accuracy == 60.0  # (3 / 5) * 100
    assert len(report.questions) == 5

    # Validate question items detail
    for idx, q in enumerate(report.questions):
        expected_ans_tuple = test_answers[idx]
        assert q.question_number == idx + 1
        assert q.candidate_answer == expected_ans_tuple[4]
        assert q.expected_answer == expected_ans_tuple[8]
        assert q.score == expected_ans_tuple[5]
        assert q.result in ("Correct", "Wrong")

    # Validate model aliases
    assert report.interview_id == session_id
    assert report.role == "Senior Python Developer"
    assert report.date == report.interview_date
    assert len(report.areas_to_improve) == len(report.weak_areas)

    # Validate PDF export
    export_service = get_export_service()
    pdf_bytes = export_service.generate_pdf(report)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

    # Validate DOCX export
    docx_bytes = export_service.generate_docx(report)
    assert len(docx_bytes) > 500
    assert docx_bytes.startswith(b"PK\x03\x04")


def test_safe_handling_of_incomplete_and_missing_evaluation():
    """Verify safe handling of unevaluated answers without inventing scores or ideal answers."""
    conn = get_connection()
    session_id = f"test-incomplete-{datetime.now().timestamp()}"
    
    conn.execute(
        """
        INSERT INTO interview_sessions 
        (session_id, job_role, status, current_question_number, total_questions, skills_json, created_at)
        VALUES (?, ?, 'in_progress', 1, 5, ?, ?)
        """,
        (session_id, "Frontend Engineer", json.dumps(["React"]), datetime.now().isoformat())
    )

    # Insert one pending/unevaluated answer
    conn.execute(
        """
        INSERT INTO candidate_answers
        (session_id, question_id, answer, score, feedback, skill, difficulty, evaluation_status)
        VALUES (?, ?, ?, NULL, NULL, ?, ?, 'pending')
        """,
        (session_id, "q_react_1", "React uses virtual DOM", "React", "Medium")
    )
    conn.commit()
    conn.close()

    repo = get_question_repository()
    report_service = get_report_service(str(DB_PATH), repo)
    report = report_service.build_interview_report(session_id, preparation_days=3)

    assert report.completion_status == "in_progress"
    assert len(report.questions) == 1
    q1 = report.questions[0]
    assert q1.result == "Unavailable"
    assert q1.score is None
    assert q1.expected_answer == ""
    assert "Evaluation unavailable" in q1.evaluation
