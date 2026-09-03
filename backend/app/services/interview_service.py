"""
Interview Session Management Service
Handles interview lifecycle: creation, question serving, answer recording, completion.
Integrates AI-powered answer evaluation using LangChain + OpenAI.
"""

import uuid
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
from datetime import timezone
from datetime import timedelta

from app.config import settings
from app.services.question_repository import Question

logger = logging.getLogger(__name__)


def determine_question_result(score: Optional[float], correctness: Optional[str] = None) -> str:
    """
    Centralized helper for determining 'Correct' vs 'Wrong' vs 'Unavailable' status.
    
    Rules:
    - If score is None and not correctness: 'Unavailable'
    - If correctness verdict is explicitly 'excellent', 'good', or 'correct': 'Correct'
    - If correctness verdict is explicitly 'poor', 'incorrect', or 'wrong': 'Wrong'
    - If score is provided: score >= 6.0 is 'Correct', < 6.0 is 'Wrong'
    - Default: 'Wrong'
    """
    if score is None and not correctness:
        return "Unavailable"
    c = (correctness or "").strip().lower()
    if c in ("excellent", "good", "correct"):
        return "Correct"
    if c in ("poor", "incorrect", "wrong"):
        return "Wrong"
    if score is not None:
        try:
            return "Correct" if float(score) >= 6.0 else "Wrong"
        except (ValueError, TypeError):
            pass
    return "Wrong"


class InterviewService:
    """Manages interview sessions and state."""

    def __init__(
        self,
        database_path: str,
        question_repo,
        question_engine,
        evaluation_service=None
    ):
        """
        Initialize interview service.

        Args:
            database_path: Path to SQLite database
            question_repo: QuestionRepository instance
            question_engine: QuestionSelectionEngine instance
            evaluation_service: EvaluationService instance (optional, loaded on demand)
        """
        self.db_path = database_path
        self.repo = question_repo
        self.engine = question_engine
        self.evaluation_service = evaluation_service

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_question(self, question_id: str, session) -> Optional[Question]:
        question = self.repo.get_question(question_id)
        if question or not question_id.startswith("ROLE-"):
            return question
        return next(
            (item for item in self.repo.get_role_questions(
                session["job_role"], session["interview_type"] or "Technical"
            ) if item.question_id == question_id),
            None,
        )

    def create_interview_session(
        self,
        job_role: str,
        skills: List[str],
        total_questions: int = 10,
        user_id: Optional[str] = None,
        interview_type: str = "Technical",
        difficulty: str = "Medium",
    ) -> Dict:
        """
        Create new interview session.

        Args:
            job_role: Target job role
            skills: List of required skills
            total_questions: Number of questions in interview

        Returns:
            Dict with session_id and first question
        """

        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Store session in database
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO interview_sessions
                (
                    session_id,
                    job_role,
                    total_questions,
                    current_question_number,
                    status,
                    skills_json,
                    user_id,
                    interview_type,
                    difficulty
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    job_role,
                    total_questions,
                    0,
                    "in_progress",
                    json.dumps(skills),
                    user_id,
                    interview_type,
                    difficulty
                )
            )

            conn.commit()

        finally:
            conn.close()

        logger.info(f"✓ Created interview session {session_id}")

        conn = self._get_connection()
        try:
            now_dt = datetime.now(timezone.utc)
            now = now_dt.isoformat()
            conn.execute(
                "UPDATE interview_sessions SET started_at = ?, expires_at = ?, last_activity_at = ? WHERE session_id = ?",
                (now, (now_dt + timedelta(seconds=settings.interview_duration_seconds)).isoformat(), now, session_id),
            )
            conn.commit()
        finally:
            conn.close()

        # Get first question
        first_question = self._get_next_question(session_id)

        return {
            "session_id": session_id,
            "job_role": job_role,
            "total_questions": total_questions,
            "skills": skills,
            "first_question": first_question
        }

    def _get_next_question(self, session_id: str) -> Optional[Dict]:
        """
        Get next question for interview session.

        Returns:
            Dict with question data, or None if interview complete
        """

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get session info
            cursor.execute(
                """
                SELECT *
                FROM interview_sessions
                WHERE session_id = ?
                """,
                (session_id,)
            )

            session = cursor.fetchone()

            if not session:
                return None

            current_num = session["current_question_number"]
            total_questions = session["total_questions"]
            preferred_difficulty = session["difficulty"] or "Medium"

            # Check if interview complete
            if current_num >= total_questions:
                return None

            # Get skills from session
            skills = json.loads(session["skills_json"])

            # Get asked question IDs
            cursor.execute(
                """
                SELECT question_id
                FROM asked_questions
                WHERE session_id = ?
                """,
                (session_id,)
            )

            asked_ids = {
                row["question_id"]
                for row in cursor.fetchall()
            }

            # Get performance history
            cursor.execute(
                """
                SELECT skill, AVG(score) AS avg_score
                FROM candidate_answers
                WHERE session_id = ?
                  AND score IS NOT NULL
                GROUP BY skill
                """,
                (session_id,)
            )

            performance_by_skill = {
                row["skill"]: row["avg_score"]
                for row in cursor.fetchall()
            }

        finally:
            conn.close()

        # Select next question using engine
        next_question_id = self.engine.select_next_question(
            required_skills=skills,
            asked_question_ids=asked_ids,
            performance_by_skill=performance_by_skill,
            total_questions=total_questions,
            current_question_number=current_num,
            preferred_difficulty=preferred_difficulty
            , role=session["job_role"]
            , interview_type=session["interview_type"] or "Technical"
        )

        if not next_question_id:
            logger.warning(
                f"No questions available for session {session_id}"
            )
            return None

        # Get question details
        question = self.repo.get_question(next_question_id)
        if not question and next_question_id.startswith("ROLE-"):
            question = next((item for item in self.repo.get_role_questions(session["job_role"], session["interview_type"] or "Technical") if item.question_id == next_question_id), None)

        if not question:
            return None

        # Record that this question was asked
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            new_question_number = current_num + 1

            cursor.execute(
                """
                INSERT INTO asked_questions
                (
                    session_id,
                    question_id,
                    question_number
                )
                VALUES (?, ?, ?)
                """,
                (
                    session_id,
                    next_question_id,
                    new_question_number
                )
            )

            # Update session
            cursor.execute(
                """
                UPDATE interview_sessions
                SET current_question_number = ?
                WHERE session_id = ?
                """,
                (
                    new_question_number,
                    session_id
                )
            )

            conn.commit()

        finally:
            conn.close()

        return {
            "question_number": new_question_number,
            "total_questions": total_questions,
            "question_id": question.question_id,
            "question": question.question,
            "skill": question.skill,
            "difficulty": question.difficulty,
            "category": question.category
        }

    def submit_answer(
        self,
        session_id: str,
        question_id: str,
        answer_text: str,
        auto_expired: bool = False,
    ) -> Dict:
        """
        Submit candidate answer and get AI evaluation + next question.

        If this is the final answer:
        - interview_complete is set to True
        - interview session is marked completed
        - interview performance summary is generated

        Args:
            session_id: Interview session ID
            question_id: Question being answered
            answer_text: Candidate's answer

        Returns:
            Dict with AI evaluation and next question
        """

        # Validate session exists
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM interview_sessions
            WHERE session_id = ?
            """,
            (session_id,)
        )

        session = cursor.fetchone()

        if not session:
            conn.close()
            raise ValueError(f"Session not found: {session_id}")

        current_question = self._get_current_question_id(session_id)
        if current_question != question_id:
            conn.close()
            raise ValueError("Question is not the current question for this session")

        # Prevent submitting answers to an already completed interview
        if session["status"] == "completed":
            conn.close()
            raise ValueError(
                f"Interview already completed: {session_id}"
            )
        if session["expires_at"]:
            expires_at = datetime.fromisoformat(session["expires_at"])
            if datetime.now(timezone.utc) >= expires_at and not auto_expired:
                raise ValueError("Interview time has expired")

        # Get question details
        question = self._get_question(question_id, session)

        if not question:
            conn.close()
            raise ValueError(
                f"Question not found: {question_id}"
            )

        now = datetime.now(timezone.utc).isoformat()
        try:
            existing = cursor.execute(
                "SELECT * FROM candidate_answers WHERE session_id = ? AND question_id = ?",
                (session_id, question_id),
            ).fetchone()
            if existing:
                conn.close()
                return self.retry_evaluation(session_id, question_id)

            # Persist the answer before any provider call.
            cursor.execute(
                """
                INSERT INTO candidate_answers
                (
                    session_id,
                    question_id,
                    answer,
                    score,
                    feedback,
                    skill,
                    difficulty,
                    evaluation_status,
                    answered_at
                )
                VALUES (?, ?, ?, NULL, NULL, ?, ?, 'pending', ?)
                """,
                (
                    session_id,
                    question_id,
                    answer_text,
                    question.skill,
                    question.difficulty
                    ,now
                )
            )
            conn.commit()
        except Exception:
            conn.rollback()
            conn.close()
            raise
        conn.close()

        return self.retry_evaluation(session_id, question_id)

    def retry_evaluation(self, session_id: str, question_id: str) -> Dict:
        """Evaluate an already-persisted answer without inserting another row."""
        conn = self._get_connection()
        row = conn.execute(
            """SELECT ca.*, aq.question_number
               FROM candidate_answers ca
               JOIN asked_questions aq ON aq.session_id = ca.session_id AND aq.question_id = ca.question_id
               WHERE ca.session_id = ? AND ca.question_id = ?""",
            (session_id, question_id),
        ).fetchone()
        session = conn.execute(
            "SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()
        if not row or not session:
            raise ValueError("Saved answer not found")
        question = self._get_question(question_id, session)
        if row["evaluation_status"] == "complete" and row["evaluation_json"]:
            evaluation_data = json.loads(row["evaluation_json"])
            next_question = self._question_after_number(session_id, row["question_number"])
            return {
                "question_number": row["question_number"],
                "evaluation": evaluation_data,
                "next_question": next_question,
                "interview_complete": not bool(next_question),
                "answer_saved": True,
                "evaluation_status": "complete",
            }
        try:
            evaluation = self._evaluate_answer(
                question.question, question.ideal_answer, question.keywords,
                row["answer"], question.skill, question.difficulty
            )
        except Exception as exc:
            conn = self._get_connection()
            conn.execute(
                "UPDATE candidate_answers SET evaluation_status = 'failed', evaluation_error = ? WHERE id = ?",
                (type(exc).__name__, row["id"]),
            )
            conn.commit()
            conn.close()
            raise RuntimeError("AI evaluation is temporarily unavailable") from exc

        evaluation_data = evaluation.model_dump() if hasattr(evaluation, "model_dump") else {
            "score": evaluation.score,
            "correctness": evaluation.correctness,
            "relevance": evaluation.relevance,
            "completeness": evaluation.completeness,
            "strengths": evaluation.strengths,
            "weaknesses": evaluation.weaknesses,
            "feedback": evaluation.feedback,
            "recommended_difficulty": evaluation.recommended_difficulty,
        }
        ideal_ans = (getattr(evaluation, "ideal_answer", None) or getattr(evaluation, "expected_answer", None) or question.ideal_answer or "").strip()
        improvement = getattr(evaluation, "improvement", None) or evaluation.feedback or ""
        evaluation_data["ideal_answer"] = ideal_ans
        evaluation_data["expected_answer"] = ideal_ans
        evaluation_data["improvement"] = improvement
        evaluation_data["result"] = determine_question_result(evaluation.score, evaluation.correctness)

        conn = self._get_connection()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE candidate_answers SET score = ?, feedback = ?, evaluation_json = ?, evaluation_status = 'complete', evaluation_error = NULL, evaluated_at = ? WHERE id = ?",
            (evaluation.score, evaluation.feedback, json.dumps(evaluation_data), now, row["id"]),
        )
        conn.execute("UPDATE interview_sessions SET last_activity_at = ? WHERE session_id = ?", (now, session_id))
        conn.commit()
        conn.close()

        next_question = self._get_next_question(session_id)
        response = {
            "question_number": row["question_number"],
            "evaluation": evaluation_data,
            "answer_saved": True,
            "evaluation_status": "complete",
            "interview_complete": not bool(next_question),
        }
        if next_question:
            response["next_question"] = next_question
        else:
            self.finish_interview(session_id)
        return response

    @staticmethod
    def _answer_result_from_row(row, session):
        return {
            "question_number": session["current_question_number"],
            "evaluation": None,
            "answer_saved": True,
            "evaluation_status": row["evaluation_status"],
            "message": "Answer already submitted.",
        }

    def expire_interview(self, session_id: str) -> bool:
        conn = self._get_connection()
        session = conn.execute("SELECT status, expires_at FROM interview_sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not session or session["status"] == "completed" or not session["expires_at"]:
            conn.close()
            return False
        expired = datetime.now(timezone.utc) >= datetime.fromisoformat(session["expires_at"])
        if expired:
            conn.execute("UPDATE interview_sessions SET status = 'expired', last_activity_at = ? WHERE session_id = ?", (datetime.now(timezone.utc).isoformat(), session_id))
            conn.commit()
        conn.close()
        return expired

    def _question_after_number(self, session_id: str, question_number: int) -> Optional[Dict]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT question_id, question_number FROM asked_questions WHERE session_id = ? AND question_number = ?",
            (session_id, question_number + 1),
        ).fetchone()
        session = conn.execute("SELECT total_questions FROM interview_sessions WHERE session_id = ?", (session_id,)).fetchone()
        conn.close()
        if not row or not session:
            return None
        question = self.repo.get_question(row["question_id"])
        return {
            "question_number": row["question_number"], "total_questions": session["total_questions"],
            "question_id": question.question_id, "question": question.question,
            "skill": question.skill, "difficulty": question.difficulty, "category": question.category,
        }

        # Get next question.
        #
        # _get_next_question() uses its own DB connection.
        # The current answer has already been committed above.
        next_question = self._get_next_question(session_id)

        # Prepare response
        response = {
            "question_number": session["current_question_number"],
            "evaluation": {
                "score": evaluation.score,
                "correctness": evaluation.correctness,
                "relevance": evaluation.relevance,
                "completeness": evaluation.completeness,
                "strengths": evaluation.strengths,
                "weaknesses": evaluation.weaknesses,
                "feedback": evaluation.feedback,
                "recommended_difficulty": evaluation.recommended_difficulty
            }
        }

        if next_question:
            # Interview continues
            response["next_question"] = next_question

            conn.close()

            return response

        # ==========================================================
        # FINAL ANSWER
        # ==========================================================

        response["interview_complete"] = True

        # Close the original connection before calling
        # finish_interview(), because finish_interview() opens
        # another SQLite connection.
        conn.close()

        logger.info(
            f"Final answer submitted. Completing interview {session_id}"
        )

        # Mark session completed and generate performance summary.
        #
        # This function is now idempotent, so calling /finish later
        # will not create duplicate performance records.
        self.finish_interview(session_id)

        logger.info(
            f"✓ Interview automatically completed: {session_id}"
        )

        return response

    def _get_current_question_id(self, session_id: str) -> Optional[str]:
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT question_id
                FROM asked_questions
                WHERE session_id = ?
                ORDER BY question_number DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            return row["question_id"] if row else None
        finally:
            conn.close()

    def get_hint(self, session_id: str, question_id: str) -> str:
        """Build a concise hint from the stored question, without revealing its answer."""
        conn = self._get_connection()
        try:
            session = conn.execute(
                "SELECT status FROM interview_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not session:
                raise ValueError("Session not found")
            if session["status"] == "completed":
                raise ValueError("Interview already completed")
            current_question = self._get_current_question_id(session_id)
            if current_question != question_id:
                raise ValueError("Hint is only available for the current question")
        finally:
            conn.close()

        question = self._get_question(question_id, session)
        if not question:
            raise ValueError("Question not found")
        keywords = question.keywords[:3] if question.keywords else []
        focus = ", ".join(keywords)
        if focus:
            return f"Start by defining the main idea, then connect your explanation to {focus}. Use a small example and explain why it works."
        return "Start with a clear definition, identify the key trade-off or steps, and support your answer with a small example."

    def record_integrity_event(self, session_id: str, event: Dict) -> None:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT integrity_events_json FROM interview_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            conn.close()
            raise ValueError("Session not found")
        events = json.loads(row["integrity_events_json"] or "[]")
        events.append({key: event[key] for key in ("type", "timestamp", "question_id") if key in event})
        conn.execute(
            "UPDATE interview_sessions SET integrity_events_json = ?, last_activity_at = ? WHERE session_id = ?",
            (json.dumps(events[-100:]), datetime.now(timezone.utc).isoformat(), session_id),
        )
        conn.commit()
        conn.close()

    def _evaluate_answer(
        self,
        question: str,
        ideal_answer: str,
        keywords: List[str],
        candidate_answer: str,
        skill: str,
        difficulty: str
    ):
        """
        Evaluate answer using AI evaluation service with fallback.

        Returns:
            AIEvaluation object with structured assessment
        """

        # Lazy load evaluation service
        if self.evaluation_service is None:
            try:
                from app.services.evaluation_service import (
                    get_evaluation_service
                )

                self.evaluation_service = get_evaluation_service()

                logger.info(
                    "Using AI-powered evaluation service"
                )

            except Exception as e:
                logger.warning(
                    f"AI evaluation unavailable: {e}. "
                    "Using fallback keyword-based evaluation."
                )

                self.evaluation_service = False

        # Use AI evaluation if available
        if self.evaluation_service and self.evaluation_service is not False:
            return self.evaluation_service.evaluate_answer(
                question=question,
                ideal_answer=ideal_answer,
                keywords=keywords,
                candidate_answer=candidate_answer,
                skill=skill,
                difficulty=difficulty,
            )

        raise RuntimeError("AI evaluation service is unavailable")

    def _fallback_evaluation(
        self,
        candidate_answer: str,
        ideal_answer: str,
        keywords: List[str]
    ):
        """
        Fallback evaluation if AI fails.

        Uses simple keyword-based scoring.
        """

        from app.models.interview_models import AIEvaluation

        if not candidate_answer.strip():
            return AIEvaluation(
                score=0,
                correctness="Poor",
                relevance="Low",
                completeness="Incomplete",
                strengths=[],
                weaknesses=["No answer provided"],
                feedback="Please provide an answer to the question.",
                improvement="Answer the question directly by defining the core concept and providing a concrete example.",
                ideal_answer=ideal_answer,
                expected_answer=ideal_answer,
                recommended_difficulty="Easy",
                result="Wrong",
            )

        # Simple keyword matching
        answer_lower = candidate_answer.lower()

        keyword_matches = sum(
            1
            for kw in keywords
            if kw.lower() in answer_lower
        )

        keyword_percentage = (
            keyword_matches / len(keywords)
            if keywords
            else 0
        )

        # Basic scoring
        if keyword_percentage >= 0.8:
            score = 8
            correctness = "Good"

        elif keyword_percentage >= 0.6:
            score = 6
            correctness = "Fair"

        elif keyword_percentage >= 0.4:
            score = 4
            correctness = "Fair"

        else:
            score = 2
            correctness = "Poor"

        feedback_text = (
            "Good foundational understanding demonstrated."
            if score >= 6
            else "Your answer could be improved by providing more specific details and core concepts."
        )
        improvement_text = (
            f"To enhance your answer further, review the model answer: {ideal_answer[:120]}..."
            if len(ideal_answer) > 120
            else f"To enhance your answer further, review the model answer: {ideal_answer}"
        )

        return AIEvaluation(
            score=score,
            correctness=correctness,
            relevance=(
                "Medium"
                if keyword_percentage > 0.3
                else "Low"
            ),
            completeness="Partial",
            strengths=(
                ["Answered the question"]
                if len(candidate_answer) > 10
                else []
            ),
            weaknesses=(
                ["Could provide more detail and specific terminology"]
                if len(candidate_answer) < 50
                else []
            ),
            feedback=feedback_text,
            improvement=improvement_text,
            ideal_answer=ideal_answer,
            expected_answer=ideal_answer,
            recommended_difficulty="Medium",
            result=determine_question_result(score, correctness),
        )

    def get_session_status(
        self,
        session_id: str
    ) -> Dict:
        """Get current session status."""

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM interview_sessions
            WHERE session_id = ?
            """,
            (session_id,)
        )

        session = cursor.fetchone()

        if not session:
            conn.close()
            raise ValueError(
                f"Session not found: {session_id}"
            )

        # Get asked questions count and skills covered
        cursor.execute(
            """
            SELECT DISTINCT skill
            FROM asked_questions aq
            JOIN candidate_answers ca
              ON aq.session_id = ca.session_id
             AND aq.question_id = ca.question_id
            WHERE aq.session_id = ?
            """,
            (session_id,)
        )

        skills_covered = [
            row["skill"]
            for row in cursor.fetchall()
        ]

        saved_answer = conn.execute(
            """SELECT question_id, answer, evaluation_status FROM candidate_answers
               WHERE session_id = ? ORDER BY answered_at DESC LIMIT 1""",
            (session_id,),
        ).fetchone()
        conn.close()

        total_questions = session["total_questions"]

        progress = (
            session["current_question_number"] / total_questions
            if total_questions
            else 0
        )
        current_question = None
        current_question_id = self._get_current_question_id(session_id)
        if current_question_id and session["status"] not in {"completed", "expired"}:
            question = self.repo.get_question(current_question_id)
            if question:
                current_question = {
                    "question_number": session["current_question_number"],
                    "total_questions": total_questions,
                    "question_id": question.question_id,
                    "question": question.question,
                    "skill": question.skill,
                    "difficulty": question.difficulty,
                    "category": question.category,
                }
        return {
            "session_id": session["session_id"],
            "job_role": session["job_role"],
            "status": session["status"],
            "current_question_number": session[
                "current_question_number"
            ],
            "total_questions": total_questions,
            "progress": progress,
            "skills_covered": list(set(skills_covered)),
            "created_at": session["created_at"],
            "started_at": session["started_at"] or session["created_at"],
            "current_question": current_question,
            "evaluation_status": saved_answer["evaluation_status"] if saved_answer else None,
            "saved_answer": saved_answer["answer"] if saved_answer and saved_answer["evaluation_status"] != "complete" else None,
            "saved_question_id": saved_answer["question_id"] if saved_answer and saved_answer["evaluation_status"] != "complete" else None,
            "expires_at": session["expires_at"],
            "remaining_seconds": max(0, int((datetime.fromisoformat(session["expires_at"]) - datetime.now(timezone.utc)).total_seconds())) if session["expires_at"] else None,
        }

    def finish_interview(
        self,
        session_id: str
    ) -> Dict:
        """
        Finish interview and generate summary.

        This method is idempotent:
        calling it multiple times for the same completed
        interview will NOT create duplicate performance records.

        Returns:
            Interview summary with scores and insights
        """

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Verify session exists
            cursor.execute(
                """
                SELECT *
                FROM interview_sessions
                WHERE session_id = ?
                """,
                (session_id,)
            )

            session = cursor.fetchone()

            if not session:
                raise ValueError(
                    f"Session not found: {session_id}"
                )

            # Update session status only if not already completed.
            # This preserves the original completed_at timestamp.
            if session["status"] != "completed":
                cursor.execute(
                    """
                    UPDATE interview_sessions
                    SET
                        status = 'completed',
                        completed_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                    """,
                    (session_id,)
                )

            # Get all scored answers
            cursor.execute(
                """
                SELECT score, skill, difficulty
                FROM candidate_answers
                WHERE session_id = ?
                  AND score IS NOT NULL
                """,
                (session_id,)
            )

            answers = cursor.fetchall()

            if not answers:
                conn.commit()

                return {
                    "session_id": session_id,
                    "status": "completed",
                    "message": "No scored answers yet"
                }

            # Calculate summary
            scores = [
                row["score"]
                for row in answers
            ]

            total_score = sum(scores)

            average_score = (
                total_score / len(scores)
            )

            # Score by skill
            skill_scores = {}

            for row in answers:
                skill = row["skill"]

                if skill not in skill_scores:
                    skill_scores[skill] = []

                skill_scores[skill].append(
                    row["score"]
                )

            skill_summary = {
                skill: {
                    "skill": skill,
                    "avg_score": round(
                        sum(scores) / len(scores),
                        1
                    ),
                    "count": len(scores)
                }
                for skill, scores in skill_scores.items()
            }

            # ======================================================
            # CHECK FOR EXISTING PERFORMANCE RECORD
            # ======================================================

            cursor.execute(
                """
                SELECT *
                FROM interview_performance
                WHERE session_id = ?
                LIMIT 1
                """,
                (session_id,)
            )

            existing_performance = cursor.fetchone()

            if not existing_performance:

                # Create performance summary
                cursor.execute(
                    """
                    INSERT INTO interview_performance
                    (
                        session_id,
                        total_score,
                        average_score,
                        skill_scores,
                        completed_at
                    )
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        session_id,
                        total_score,
                        average_score,
                        json.dumps(skill_summary)
                    )
                )

                logger.info(
                    f"✓ Created performance summary for {session_id}"
                )

            else:
                logger.info(
                    f"Performance summary already exists for "
                    f"{session_id}; skipping duplicate insert"
                )

            conn.commit()

            return {
                "session_id": session_id,
                "status": "completed",
                "total_questions": len(scores),
                "average_score": round(
                    average_score,
                    1
                ),
                "total_score": round(
                    total_score,
                    1
                ),
                "skill_scores": skill_summary,
                "message": "Interview completed successfully"
            }

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()


# Singleton instance
_interview_service: Optional[InterviewService] = None


def get_interview_service(
    database_path: str,
    question_repo,
    question_engine
) -> InterviewService:
    """Get or create interview service."""

    global _interview_service

    if _interview_service is None:
        _interview_service = InterviewService(
            database_path,
            question_repo,
            question_engine
        )

    return _interview_service


import random  # Import here to avoid circular import