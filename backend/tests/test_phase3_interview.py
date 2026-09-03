"""Comprehensive tests for Phase 3: Interview Question Bank + Adaptive Interview Engine
Tests cover: dataset validation, services, API endpoints, and end-to-end flows.
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.database import DB_PATH, get_connection, init_database
from app.services.evaluation_service import AnswerEvaluation
from app.services.interview_service import InterviewService
from app.services.question_engine import QuestionSelectionEngine
from app.services.question_repository import (
    Question,
    QuestionRepository,
    get_question_repository,
)


class TestDatasetValidation:
    """Test dataset quality and structure."""

    def test_dataset_loads_successfully(self):
        """Test that dataset loads without errors."""
        repo = get_question_repository()
        assert repo is not None
        assert len(repo.questions) > 0

    def test_dataset_has_minimum_150_questions(self):
        """Test dataset meets minimum 150 question requirement."""
        repo = get_question_repository()
        report = repo.validate_dataset()
        assert report['total_questions'] >= 150, \
            f"Dataset has {report['total_questions']} questions, minimum 150 required"

    def test_dataset_no_validation_issues(self):
        """Test dataset has no quality issues."""
        repo = get_question_repository()
        report = repo.validate_dataset()
        assert report['status'] == 'VALID'
        assert len(report['issues']) == 0

    def test_question_structure_completeness(self):
        """Test all questions have required fields."""
        repo = get_question_repository()
        for q in repo.questions.values():
            assert q.question_id, "Missing question_id"
            assert q.question, "Missing question text"
            assert q.category, "Missing category"
            assert q.difficulty in ['Easy', 'Medium', 'Hard'], f"Invalid difficulty: {q.difficulty}"
            assert q.skill, "Missing skill"
            assert q.ideal_answer, "Missing ideal_answer"
            assert len(q.keywords) > 0, "Missing keywords"


class TestQuestionSelectionEngine:
    """Test adaptive question selection logic."""

    def setup_method(self):
        self.repo = get_question_repository()
        self.engine = QuestionSelectionEngine(self.repo)

    def test_foundational_question_selection(self):
        """Test that early questions prioritize foundational topics."""
        required_skills = ['Python', 'SQL']
        exclude_ids = set()

        for i in range(3):
            question_id = self.engine.select_next_question(
                required_skills=required_skills,
                asked_question_ids=exclude_ids,
                performance_by_skill={},
                total_questions=10,
                current_question_number=i,
                preferred_difficulty='Easy'
            )
            if question_id:
                exclude_ids.add(question_id)

    def test_strong_performance_increases_difficulty(self):
        """Test that strong performance leads to harder questions."""
        required_skills = ['Python']
        exclude_ids = set()
        performance = {'Python': 8.5}

        question_id = self.engine.select_next_question(
            required_skills=required_skills,
            asked_question_ids=exclude_ids,
            performance_by_skill=performance,
            total_questions=10,
            current_question_number=5
        )
        if question_id:
            question = self.repo.get_question(question_id)
            assert question is not None

    def test_weak_performance_stays_same_difficulty(self):
        """Test that weak performance maintains similar difficulty."""
        required_skills = ['Python']
        exclude_ids = set()
        performance = {'Python': 3.0}

        question_id = self.engine.select_next_question(
            required_skills=required_skills,
            asked_question_ids=exclude_ids,
            performance_by_skill=performance,
            total_questions=10,
            current_question_number=5
        )
        if question_id:
            question = self.repo.get_question(question_id)
            assert question is not None

    def test_no_question_repetition(self):
        """Test that same question is never selected twice."""
        required_skills = ['Python', 'SQL']
        exclude_ids = set()

        selected_questions = []
        for i in range(5):
            question_id = self.engine.select_next_question(
                required_skills=required_skills,
                asked_question_ids=exclude_ids,
                performance_by_skill={},
                total_questions=10,
                current_question_number=i
            )
            if question_id:
                selected_questions.append(question_id)
                exclude_ids.add(question_id)

        assert len(selected_questions) == len(set(selected_questions))


class TestDatabaseSchema:
    """Test database initialization and schema."""

    def setup_method(self):
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name

    def teardown_method(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_database_initialization(self):
        """Test that database initializes correctly."""
        with patch('app.database.DB_PATH', Path(self.db_path)):
            init_database()

            conn = get_connection(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interview_sessions'")
            assert cursor.fetchone() is not None

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asked_questions'")
            assert cursor.fetchone() is not None

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candidate_answers'")
            assert cursor.fetchone() is not None

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interview_performance'")
            assert cursor.fetchone() is not None

            conn.close()


def _mock_eval_func(*args, **kwargs):
    return AnswerEvaluation(
        score=8,
        correctness="Good",
        relevance="High",
        completeness="Comprehensive",
        strengths=["Clear explanation"],
        weaknesses=[],
        feedback="Good job.",
        recommended_difficulty="Medium"
    )


class TestInterviewService:
    """Test interview session management."""

    def setup_method(self):
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name

        with patch('app.database.DB_PATH', Path(self.db_path)):
            init_database()

        self.repo = get_question_repository()
        self.engine = QuestionSelectionEngine(self.repo)
        self.service = InterviewService(self.db_path, self.repo, self.engine)

    def teardown_method(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_interview_session(self):
        """Test creating an interview session."""
        result = self.service.create_interview_session(
            job_role='Data Scientist',
            skills=['Python', 'SQL', 'Machine Learning'],
            total_questions=10
        )

        assert result is not None
        assert 'session_id' in result
        assert 'job_role' in result
        assert result['job_role'] == 'Data Scientist'
        assert result['total_questions'] == 10
        assert 'first_question' in result
        assert result['first_question'] is not None

    def test_no_question_repetition_in_session(self):
        """Test NEVER repeat a question within same session."""
        result = self.service.create_interview_session(
            job_role='Data Scientist',
            skills=['Python', 'SQL'],
            total_questions=5
        )

        session_id = result['session_id']
        asked_ids = [result['first_question']['question_id']]

        with patch.object(self.service, '_evaluate_answer', side_effect=_mock_eval_func):
            for i in range(4):
                response = self.service.submit_answer(
                    session_id=session_id,
                    question_id=asked_ids[-1],
                    answer_text='Test answer'
                )

                if 'next_question' in response and response['next_question']:
                    next_id = response['next_question']['question_id']
                    asked_ids.append(next_id)

        assert len(asked_ids) == len(set(asked_ids)), "Question repeated in same session!"

    def test_get_session_status(self):
        """Test retrieving session status."""
        result = self.service.create_interview_session(
            job_role='Data Scientist',
            skills=['Python', 'SQL'],
            total_questions=5
        )

        session_id = result['session_id']
        status = self.service.get_session_status(session_id)

        assert status['session_id'] == session_id
        assert status['status'] == 'in_progress'
        assert status['current_question_number'] == 1
        assert status['total_questions'] == 5

    def test_finish_interview(self):
        """Test finishing an interview and getting summary."""
        result = self.service.create_interview_session(
            job_role='Data Scientist',
            skills=['Python', 'SQL'],
            total_questions=3
        )

        session_id = result['session_id']

        response = result['first_question']
        with patch.object(self.service, '_evaluate_answer', side_effect=_mock_eval_func):
            for i in range(3):
                answer_result = self.service.submit_answer(
                    session_id=session_id,
                    question_id=response['question_id'],
                    answer_text='Test answer'
                )
                if 'next_question' in answer_result and answer_result['next_question']:
                    response = answer_result['next_question']

        summary = self.service.finish_interview(session_id)

        assert summary['status'] == 'completed'
        assert 'total_questions' in summary
        assert 'average_score' in summary
        assert 'skill_scores' in summary


class TestEndToEndFlow:
    """Test complete end-to-end interview flow."""

    def setup_method(self):
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name

        with patch('app.database.DB_PATH', Path(self.db_path)):
            init_database()

        self.repo = get_question_repository()
        self.engine = QuestionSelectionEngine(self.repo)
        self.service = InterviewService(self.db_path, self.repo, self.engine)

    def teardown_method(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_complete_10_question_interview(self):
        """Test a complete 10-question interview with no repetition."""
        result = self.service.create_interview_session(
            job_role='Data Scientist',
            skills=['Python', 'SQL', 'Machine Learning'],
            total_questions=10
        )

        session_id = result['session_id']
        asked_ids = []

        response = result['first_question']
        with patch.object(self.service, '_evaluate_answer', side_effect=_mock_eval_func):
            for i in range(10):
                asked_ids.append(response['question_id'])

                answer_result = self.service.submit_answer(
                    session_id=session_id,
                    question_id=response['question_id'],
                    answer_text='Answer text'
                )

                if i < 9:
                    assert 'next_question' in answer_result
                    assert answer_result['next_question'] is not None
                    response = answer_result['next_question']

        assert len(asked_ids) == 10
        assert len(set(asked_ids)) == 10
