#!/usr/bin/env python3
"""End-to-end verification for Phase 5 report generation."""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.database import DB_PATH, init_database
from app.services.interview_service import InterviewService
from app.services.question_engine import QuestionSelectionEngine
from app.services.question_repository import get_question_repository
from app.services.report_export_service import ReportExportService
from app.services.report_service import get_report_service


os.environ.pop('GEMINI_API_KEY', None)

if DB_PATH.exists():
    DB_PATH.unlink()

init_database()
question_repo = get_question_repository()
question_engine = QuestionSelectionEngine(question_repo)
interview_service = InterviewService(str(DB_PATH), question_repo, question_engine)
report_service = get_report_service(str(DB_PATH), question_repo)
export_service = ReportExportService()

session = interview_service.create_interview_session(
    job_role='Backend Engineer',
    skills=['Python', 'SQL'],
    total_questions=5,
)
session_id = session['session_id']

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()
answers = [
    ('Python', 8.5, 'Strong Python fundamentals and clean logic.'),
    ('Python', 7.0, 'Good structure with some missing edge cases.'),
    ('SQL', 5.0, 'Basic querying skills but limited optimization knowledge.'),
    ('Python', 6.5, 'Solid understanding but needs stronger debugging examples.'),
    ('SQL', 7.0, 'Good joins and filtering, needs more index awareness.'),
]
for idx, (skill, score, feedback) in enumerate(answers, 1):
    cursor.execute(
        """
        INSERT INTO candidate_answers
        (session_id, question_id, answer, score, feedback, skill, difficulty)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, f'q{idx}', 'sample answer', score, feedback, skill, 'Medium'),
    )

cursor.execute(
    "UPDATE interview_sessions SET status = 'completed', current_question_number = ? WHERE session_id = ?",
    (5, session_id),
)
conn.commit()
conn.close()

report = report_service.generate_report(session_id, preparation_days=3)
assert report.session_id == session_id
assert report.ai_generated in (True, False)
assert 0 <= report.overall_score <= 100

cached = report_service.generate_report(session_id, preparation_days=3)
assert cached.summary == report.summary

pdf_bytes = export_service.generate_pdf(report)
assert len(pdf_bytes) > 500, 'PDF is too small'
assert pdf_bytes[:4] == b'%PDF', 'Invalid PDF header'

# DOCX output is created without python-docx due Windows lxml policy restrictions.
docx_bytes = export_service.generate_docx(report)
assert len(docx_bytes) > 500, 'DOCX is too small'
assert docx_bytes[:4] == b'PK\x03\x04', 'Invalid DOCX ZIP header'

print('PHASE 5 E2E PASS')
print('session_id=', session_id)
print('overall_score=', round(report.overall_score, 2))
print('performance_level=', report.performance_level)
print('pdf_size=', len(pdf_bytes))
print('docx_size=', len(docx_bytes))
print('cached_match=', cached.summary == report.summary)
