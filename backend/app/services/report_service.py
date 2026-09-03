"""
Report Generation Service for Phase 5
Analyzes interview results and generates personalized preparation reports using Gemini AI.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from app.models.interview_models import (
    InterviewReport,
    ReportQuestionItem,
    SkillPerformance,
    StrengthItem,
    WeakAreaItem,
    ConceptGap,
    Recommendation,
    PreparationDay
)

from app.config import settings
from app.database import get_connection
from app.services.gemini_provider import get_gemini_provider
from app.services.interview_service import determine_question_result

logger = logging.getLogger(__name__)


class ReportService:
    """Generates personalized interview performance reports using AI."""

    def __init__(self, db_path: str, question_repo):
        """
        Initialize report service.

        Args:
            db_path: Path to SQLite database
            question_repo: QuestionRepository instance for question details
        """
        self.db_path = db_path
        self.repo = question_repo
        self.gemini_api_key = getattr(settings, "gemini_api_key", None) or os.getenv("GEMINI_API_KEY", "")
        self.api_key = self.gemini_api_key

    def _get_connection(self) -> Any:
        """Get database connection."""
        return get_connection(self.db_path)

    def build_interview_report(
        self,
        session_id: str,
        preparation_days: int = 5
    ) -> InterviewReport:
        """Central calculation function to build/retrieve interview report."""
        return self.generate_report(session_id, preparation_days)

    def generate_report(
        self,
        session_id: str,
        preparation_days: int = 5
    ) -> InterviewReport:
        """
        Generate complete interview performance report.

        Args:
            session_id: Interview session ID
            preparation_days: Number of days in preparation plan

        Returns:
            InterviewReport object

        Raises:
            ValueError: If session not found
        """

        # Check if report already cached
        cached_report = self._get_cached_report(session_id, preparation_days)

        if cached_report and cached_report.questions:
            logger.info(f"Returning cached report for session {session_id}")
            return cached_report

        # Gather interview data
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get session
        cursor.execute(
            "SELECT * FROM interview_sessions WHERE session_id = ?",
            (session_id,)
        )

        session = cursor.fetchone()

        if not session:
            conn.close()
            raise ValueError(f"Session not found: {session_id}")

        completion_status = "completed" if session["status"] == "completed" else "in_progress"

        # Get all answers and evaluations
        cursor.execute(
            """
            SELECT * FROM candidate_answers
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,)
        )

        answers = cursor.fetchall()

        # Get skills
        skills = (
            json.loads(session["skills_json"])
            if session["skills_json"]
            else []
        )

        conn.close()

        total_questions = session["total_questions"] or len(answers) or 1

        if not answers:
            now_iso = datetime.now().strftime("%Y-%m-%d")
            return InterviewReport(
                session_id=session_id,
                interview_id=session_id,
                job_role=session["job_role"],
                role=session["job_role"],
                interview_date=now_iso,
                date=now_iso,
                total_questions=total_questions,
                questions_answered=0,
                completion_status=completion_status,
                correct_count=0,
                wrong_count=0,
                accuracy=0.0,
                overall_score=0.0,
                overall_score_numeric=0,
                performance_level="Needs Improvement",
                summary="Interview session has no submitted answers yet.",
                questions=[],
                skill_scores=[],
                strengths=[],
                weak_areas=[],
                areas_to_improve=[],
                concept_gaps=[],
                recommendations=[],
                preparation_plan=[],
                generated_at=datetime.now().isoformat(),
                ai_generated=False,
            )

        # Build question-by-question items
        question_items: List[ReportQuestionItem] = []
        for idx, ans in enumerate(answers, 1):
            q_id = ans["question_id"]
            q_obj = self.repo.get_question(q_id) if hasattr(self.repo, "get_question") else None
            candidate_answer = ans["answer"] or ""
            eval_json_str = ans["evaluation_json"] if "evaluation_json" in ans.keys() else None
            eval_data = {}
            if eval_json_str:
                try:
                    eval_data = json.loads(eval_json_str)
                except Exception:
                    eval_data = {}

            status = ans["evaluation_status"] if "evaluation_status" in ans.keys() else "complete"
            score_val = ans["score"] if ans["score"] is not None else eval_data.get("score")

            if status in ("failed", "pending") or (score_val is None and not eval_data):
                result = "Unavailable"
                score = None
                correctness = None
                eval_text = "Evaluation unavailable — this answer has not been successfully evaluated yet."
                strengths = []
                weaknesses = []
                improvement = "Evaluation unavailable — this answer has not been successfully evaluated yet."
                expected_answer = ""
            else:
                score = float(score_val) if score_val is not None else None
                correctness = eval_data.get("correctness")
                result = determine_question_result(score, correctness)
                eval_text = eval_data.get("feedback") or ans["feedback"] or "Answer evaluated successfully."
                strengths = eval_data.get("strengths") or []
                weaknesses = eval_data.get("weaknesses") or []
                improvement = eval_data.get("improvement") or eval_data.get("feedback") or "Review key concepts for this topic."
                expected_answer = (eval_data.get("ideal_answer") or eval_data.get("expected_answer") or (q_obj.ideal_answer if q_obj else "")).strip()

            question_items.append(
                ReportQuestionItem(
                    question_number=idx,
                    question_id=q_id,
                    question=q_obj.question if q_obj else f"Question {idx}",
                    skill=ans["skill"] or (q_obj.skill if q_obj else "General"),
                    difficulty=ans["difficulty"] or (q_obj.difficulty if q_obj else "Medium"),
                    candidate_answer=candidate_answer,
                    expected_answer=expected_answer,
                    result=result,
                    score=score,
                    correctness=correctness,
                    evaluation=eval_text,
                    strengths=strengths,
                    weaknesses=weaknesses,
                    improvement=improvement,
                )
            )

        total_questions = session["total_questions"] or len(answers) or 1
        correct_count = sum(1 for q in question_items if q.result == "Correct")
        wrong_count = sum(1 for q in question_items if q.result == "Wrong")
        accuracy = round((correct_count / total_questions) * 100.0, 1) if total_questions > 0 else 0.0

        # Calculate deterministic scores
        overall_score_numeric, skill_scores = self._calculate_scores(
            answers,
            skills
        )

        overall_score_percent = overall_score_numeric * 10
        performance_level = self._get_performance_level(
            overall_score_numeric
        )

        # Prepare data for AI analysis
        interview_data = {
            "session_id": session_id,
            "job_role": session["job_role"],
            "total_questions": total_questions,
            "questions_answered": len(answers),
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "accuracy": accuracy,
            "overall_score": overall_score_numeric,
            "overall_score_percent": overall_score_percent,
            "performance_level": performance_level,
            "skill_scores": [
                {
                    "skill": skill.skill,
                    "avg_score": skill.avg_score,
                    "question_count": skill.question_count,
                    "performance_level": skill.performance_level
                }
                for skill in skill_scores
            ],
            "interview_details": self._extract_interview_details(answers)
        }

        # Get AI-generated analysis
        ai_analysis = self._get_ai_analysis(
            interview_data,
            preparation_days
        )

        # ---------------------------------------------------------
        # IMPORTANT:
        # Normalize AI response before passing data to Pydantic.
        # Gemini may occasionally omit required fields.
        # ---------------------------------------------------------
        ai_analysis = self._normalize_ai_analysis(
            ai_analysis,
            interview_data,
            preparation_days
        )

        # Build final report
        report = InterviewReport(
            session_id=session_id,
            job_role=session["job_role"],
            interview_date=datetime.fromisoformat(
                session["created_at"]
            ).isoformat() if session["created_at"] else datetime.now().isoformat(),
            total_questions=total_questions,
            questions_answered=len(answers),
            completion_status=completion_status,
            correct_count=correct_count,
            wrong_count=wrong_count,
            accuracy=accuracy,
            overall_score=overall_score_percent,
            overall_score_numeric=int(round(overall_score_numeric)),
            performance_level=performance_level,
            summary=ai_analysis.get("summary", ""),
            questions=question_items,
            skill_scores=skill_scores,

            strengths=[
                StrengthItem(**s)
                for s in ai_analysis.get("strengths", [])
            ],

            weak_areas=[
                WeakAreaItem(**w)
                for w in ai_analysis.get("weak_areas", [])
            ],

            concept_gaps=[
                ConceptGap(**c)
                for c in ai_analysis.get("concept_gaps", [])
            ],

            recommendations=[
                Recommendation(**r)
                for r in ai_analysis.get("recommendations", [])
            ],

            preparation_plan=[
                PreparationDay(**d)
                for d in ai_analysis.get("preparation_plan", [])
            ],

            generated_at=datetime.now().isoformat(),
            ai_generated=ai_analysis.get("ai_generated", True)
        )

        # Cache report in database
        self._cache_report(session_id, report)

        return report

    # ============================================================
    # AI RESPONSE NORMALIZATION
    # ============================================================

    def _normalize_ai_analysis(
        self,
        analysis: Dict,
        interview_data: Dict,
        preparation_days: int
    ) -> Dict:
        """
        Normalize Gemini output so it always matches our Pydantic models.

        Gemini can occasionally omit fields even when the prompt specifies
        an exact JSON structure. This method adds safe fallback values.
        """

        if not isinstance(analysis, dict):
            logger.warning(
                "AI analysis was not a dictionary. Using fallback."
            )

            return self._get_fallback_analysis(
                interview_data,
                preparation_days
            )

        # ---------------------------------------------------------
        # Ensure top-level collections exist
        # ---------------------------------------------------------

        analysis.setdefault("summary", "")
        analysis.setdefault("strengths", [])
        analysis.setdefault("weak_areas", [])
        analysis.setdefault("concept_gaps", [])
        analysis.setdefault("recommendations", [])
        analysis.setdefault("preparation_plan", [])
        if "ai_generated" not in analysis:
            analysis["ai_generated"] = bool(self.gemini_api_key or self.api_key)
        else:
            analysis["ai_generated"] = bool(analysis["ai_generated"])

        # ---------------------------------------------------------
        # Normalize strengths
        # ---------------------------------------------------------

        normalized_strengths = []

        for item in analysis.get("strengths", []):
            if not isinstance(item, dict):
                continue

            skill = str(item.get("skill", "General"))
            reason = str(
                item.get(
                    "reason",
                    "Positive performance demonstrated during the interview."
                )
            )

            normalized_strengths.append({
                "skill": skill,
                "reason": reason
            })

        analysis["strengths"] = normalized_strengths

        # ---------------------------------------------------------
        # Normalize weak areas
        # ---------------------------------------------------------

        normalized_weak_areas = []

        for item in analysis.get("weak_areas", []):
            if not isinstance(item, dict):
                continue

            skill = str(item.get("skill", "General"))

            reason = str(
                item.get(
                    "reason",
                    f"Further improvement is recommended in {skill}."
                )
            )

            priority = str(
                item.get("priority", "Medium")
            )

            if priority not in {"High", "Medium", "Low"}:
                priority = "Medium"

            normalized_weak_areas.append({
                "skill": skill,
                "reason": reason,
                "priority": priority
            })

        analysis["weak_areas"] = normalized_weak_areas

        # ---------------------------------------------------------
        # Normalize CONCEPT GAPS
        # This fixes the exact error from your screenshot.
        # ---------------------------------------------------------

        normalized_concept_gaps = []

        for item in analysis.get("concept_gaps", []):
            if not isinstance(item, dict):
                continue

            skill = str(
                item.get("skill", "General")
            ).strip()

            if not skill:
                skill = "General"

            concept = str(
                item.get("concept", "")
            ).strip()

            # Gemini sometimes omits "concept".
            if not concept:
                concept = f"{skill} fundamentals"

            reason = str(
                item.get("reason", "")
            ).strip()

            # Gemini sometimes omits "reason".
            if not reason:
                reason = (
                    f"The interview indicates that deeper understanding "
                    f"of {concept} is needed."
                )

            priority = str(
                item.get("priority", "Medium")
            ).strip()

            if priority not in {"High", "Medium", "Low"}:
                priority = "Medium"

            normalized_concept_gaps.append({
                "skill": skill,
                "concept": concept,
                "reason": reason,
                "priority": priority
            })

        analysis["concept_gaps"] = normalized_concept_gaps

        # ---------------------------------------------------------
        # Normalize recommendations
        # ---------------------------------------------------------

        normalized_recommendations = []

        for item in analysis.get("recommendations", []):
            if not isinstance(item, dict):
                continue

            skill = str(
                item.get("skill", "General")
            )

            topic = str(
                item.get(
                    "topic",
                    f"{skill} fundamentals"
                )
            )

            action = str(
                item.get(
                    "action",
                    f"Practice and review {topic}."
                )
            )

            priority = str(
                item.get("priority", "Medium")
            )

            if priority not in {"High", "Medium", "Low"}:
                priority = "Medium"

            resources = item.get("resources")

            if resources is not None and not isinstance(
                resources,
                list
            ):
                resources = None

            normalized_recommendations.append({
                "skill": skill,
                "topic": topic,
                "action": action,
                "priority": priority,
                "resources": resources
            })

        analysis["recommendations"] = normalized_recommendations

        # ---------------------------------------------------------
        # Normalize preparation plan
        # ---------------------------------------------------------

        normalized_plan = []

        for index, item in enumerate(
            analysis.get("preparation_plan", []),
            start=1
        ):
            if not isinstance(item, dict):
                continue

            day = item.get("day", index)

            try:
                day = int(day)
            except (TypeError, ValueError):
                day = index

            focus = str(
                item.get("focus", "General")
            )

            topics = item.get("topics", [])

            if not isinstance(topics, list):
                topics = [str(topics)]

            tasks = item.get("tasks", [])

            if not isinstance(tasks, list):
                tasks = [str(tasks)]

            try:
                estimated_hours = float(
                    item.get("estimated_hours", 2.0)
                )
            except (TypeError, ValueError):
                estimated_hours = 2.0

            normalized_plan.append({
                "day": day,
                "focus": focus,
                "topics": [str(t) for t in topics],
                "tasks": [str(t) for t in tasks],
                "estimated_hours": estimated_hours
            })

        # ---------------------------------------------------------
        # Guarantee requested number of preparation days
        # ---------------------------------------------------------

        skill_scores = interview_data.get("skill_scores", [])

        while len(normalized_plan) < preparation_days:

            day = len(normalized_plan) + 1

            if skill_scores:
                focus_skill = skill_scores[
                    (day - 1) % len(skill_scores)
                ]["skill"]
            else:
                focus_skill = "General"

            normalized_plan.append({
                "day": day,
                "focus": focus_skill,
                "topics": [
                    f"{focus_skill} concepts"
                ],
                "tasks": [
                    f"Review {focus_skill} fundamentals",
                    f"Practice {focus_skill} interview questions"
                ],
                "estimated_hours": 2.0
            })

        analysis["preparation_plan"] = normalized_plan[
            :preparation_days
        ]

        return analysis

    # ============================================================
    # SCORE CALCULATION
    # ============================================================

    def _calculate_scores(
        self,
        answers: List,
        skills: List[str]
    ) -> tuple:
        """
        Calculate deterministic scores from stored evaluations.

        Returns:
            (overall_score_0to10, [SkillPerformance])
        """

        skill_scores_dict: Dict[str, List[float]] = {
            skill: []
            for skill in skills
        }

        total_scores = []

        for answer in answers:
            score = answer["score"]

            if score is not None:
                total_scores.append(float(score))

                skill = answer["skill"]

                if skill in skill_scores_dict:
                    skill_scores_dict[skill].append(
                        float(score)
                    )

        # Calculate overall
        overall_avg = (
            sum(total_scores) / len(total_scores)
            if total_scores
            else 0
        )

        # Calculate per-skill
        skill_performance = []

        for skill in skills:

            scores = skill_scores_dict.get(
                skill,
                []
            )

            if scores:

                avg = sum(scores) / len(scores)

                perf_level = self._get_performance_level(
                    avg
                )

                skill_performance.append(
                    SkillPerformance(
                        skill=skill,
                        avg_score=avg,
                        question_count=len(scores),
                        performance_level=perf_level
                    )
                )

        return overall_avg, skill_performance

    def _get_performance_level(
        self,
        score: float
    ) -> str:
        """Convert numeric score to performance level."""

        if score >= 8.0:
            return "Strong"

        elif score >= 5.0:
            return "Developing"

        else:
            return "Needs Improvement"

    # ============================================================
    # INTERVIEW DETAILS
    # ============================================================

    def _extract_interview_details(
        self,
        answers: List
    ) -> str:
        """Extract key details from answers for AI analysis."""

        details = []

        for idx, answer in enumerate(
            answers,
            1
        ):

            score = (
                answer["score"]
                if answer["score"]
                else 0
            )

            feedback = (
                answer["feedback"]
                or "No feedback"
            )

            skill = answer["skill"]
            difficulty = answer["difficulty"]

            details.append(
                f"Q{idx} ({skill}/{difficulty}): "
                f"Score {score}/10 - "
                f"{feedback[:100]}"
            )

        return "\n".join(details)

    # ============================================================
    # GEMINI AI
    # ============================================================

    def _get_ai_analysis(
        self,
        interview_data: Dict,
        preparation_days: int
    ) -> Dict:
        """
        Call Gemini Provider to generate AI analysis and recommendations.
        """
        api_key = self.gemini_api_key or self.api_key
        if not api_key:
            logger.warning(
                "GEMINI_API_KEY not set. "
                "Returning fallback analysis."
            )
            return self._get_fallback_analysis(
                interview_data,
                preparation_days
            )

        try:
            # Build prompt
            prompt = self._build_analysis_prompt(
                interview_data,
                preparation_days
            )

            provider = get_gemini_provider(api_key)
            result = provider.generate_content(
                prompt=prompt,
                timeout=settings.gemini_timeout_seconds,
                max_output_tokens=2048,
                response_mime_type="application/json",
            )

            # Extract JSON
            analysis = self._parse_analysis_response(result["text"])
            analysis["ai_generated"] = True
            return analysis

        except Exception as e:
            logger.error("Error during AI analysis: %s. Using deterministic fallback.", e)
            return self._get_fallback_analysis(
                interview_data,
                preparation_days
            )

    # ============================================================
    # GEMINI PROMPT
    # ============================================================

    def _build_analysis_prompt(
        self,
        interview_data: Dict,
        preparation_days: int
    ) -> str:
        """Build prompt for Gemini API."""

        return f"""
You are an expert interview coach and skill assessment specialist.

Analyze the following interview performance data and generate a detailed personalized report.

IMPORTANT:
Return ONLY valid JSON.
Do not include markdown.
Do not include ```json.
Do not include explanations outside the JSON.

INTERVIEW DATA:

- Job Role: {interview_data['job_role']}
- Overall Score: {interview_data['overall_score']}/10
  ({interview_data['overall_score_percent']:.0f}%)
- Performance Level: {interview_data['performance_level']}
- Total Questions: {interview_data['total_questions']}
- Questions Answered: {interview_data['questions_answered']}

SKILL PERFORMANCE:

{json.dumps(
    interview_data['skill_scores'],
    indent=2
)}

DETAILED INTERVIEW FEEDBACK:

{interview_data['interview_details']}

TASK:

Generate the report using EXACTLY this JSON structure:

{{
    "summary": "2-3 sentence AI-generated summary of overall interview performance",

    "strengths": [
        {{
            "skill": "SkillName",
            "reason": "Why this is a strength based on interview evidence"
        }}
    ],

    "weak_areas": [
        {{
            "skill": "SkillName",
            "reason": "Why this needs improvement",
            "priority": "High"
        }}
    ],

    "concept_gaps": [
        {{
            "skill": "SkillName",
            "concept": "SpecificConcept",
            "reason": "Why this concept needs improvement",
            "priority": "High"
        }}
    ],

    "recommendations": [
        {{
            "skill": "SkillName",
            "topic": "SpecificTopic",
            "action": "Specific actionable step",
            "priority": "High",
            "resources": []
        }}
    ],

    "preparation_plan": [
        {{
            "day": 1,
            "focus": "PrimarySkill",
            "topics": [
                "Topic1",
                "Topic2"
            ],
            "tasks": [
                "Task1",
                "Task2"
            ],
            "estimated_hours": 2.0
        }}
    ]
}}

STRICT RULES:

1. Every concept_gaps item MUST contain:
   - skill
   - concept
   - reason
   - priority

2. Every weak_areas item MUST contain:
   - skill
   - reason
   - priority

3. Every recommendation MUST contain:
   - skill
   - topic
   - action
   - priority
   - resources

4. Every preparation_plan item MUST contain:
   - day
   - focus
   - topics
   - tasks
   - estimated_hours

5. Generate exactly {preparation_days} days.

6. Priority must be exactly:
   High, Medium, or Low.

7. Do not omit required fields even if information is limited.

8. Make recommendations concrete and actionable.

9. Base the report on the actual interview evidence.
"""

    # ============================================================
    # JSON PARSER
    # ============================================================

    def _parse_analysis_response(
        self,
        response_text: str
    ) -> Dict:
        """Extract JSON from Gemini response."""

        try:

            import re

            # Remove markdown code fences if Gemini adds them
            cleaned_text = response_text.strip()

            cleaned_text = re.sub(
                r"^```json\s*",
                "",
                cleaned_text,
                flags=re.IGNORECASE
            )

            cleaned_text = re.sub(
                r"^```\s*",
                "",
                cleaned_text
            )

            cleaned_text = re.sub(
                r"\s*```$",
                "",
                cleaned_text
            )

            # Find JSON object
            json_match = re.search(
                r"\{[\s\S]*\}",
                cleaned_text
            )

            if not json_match:
                raise ValueError(
                    "No JSON found in Gemini response"
                )

            json_str = json_match.group(0)

            return json.loads(json_str)

        except Exception as e:

            logger.error(
                f"Error parsing analysis response: {e}"
            )

            raise

    # ============================================================
    # FALLBACK ANALYSIS
    # ============================================================

    def _get_fallback_analysis(
        self,
        interview_data: Dict,
        preparation_days: int
    ) -> Dict:
        """
        Generate fallback analysis when Gemini is unavailable.
        Uses deterministic rules based on scores.
        """

        skill_scores = interview_data[
            "skill_scores"
        ]

        # --------------------------------------------------------
        # Strong skills
        # --------------------------------------------------------

        strengths = [
            StrengthItem(
                skill=s["skill"],
                reason=(
                    f"Strong performance with "
                    f"{s['avg_score']:.1f}/10 average"
                )
            )

            for s in skill_scores

            if s["performance_level"] == "Strong"
        ]

        # --------------------------------------------------------
        # Weak areas
        # --------------------------------------------------------

        weak_areas = [
            WeakAreaItem(
                skill=s["skill"],
                reason=(
                    f"Needs improvement with "
                    f"{s['avg_score']:.1f}/10 average"
                ),
                priority="High"
            )

            for s in skill_scores

            if s["performance_level"] == "Needs Improvement"
        ]

        # --------------------------------------------------------
        # Recommendations
        # --------------------------------------------------------

        recommendations = [
            Recommendation(
                skill=s["skill"],
                topic=f"{s['skill']} fundamentals",
                action=(
                    f"Practice core {s['skill']} concepts "
                    f"and solve practice problems"
                ),
                priority="High",
                resources=[]
            )

            for s in skill_scores

            if s["performance_level"] == "Needs Improvement"
        ]

        # --------------------------------------------------------
        # Preparation plan
        # --------------------------------------------------------

        prep_plan = []

        for day in range(
            1,
            preparation_days + 1
        ):

            if day <= len(skill_scores):

                focus_skill = skill_scores[
                    day - 1
                ]["skill"]

            else:

                focus_skill = (
                    skill_scores[0]["skill"]
                    if skill_scores
                    else "General"
                )

            prep_plan.append(
                PreparationDay(
                    day=day,
                    focus=focus_skill,
                    topics=[
                        f"{focus_skill} concepts"
                    ],
                    tasks=[
                        f"Practice {focus_skill} problems",
                        f"Review {focus_skill} fundamentals"
                    ],
                    estimated_hours=2.0
                )
            )

        # --------------------------------------------------------
        # Fallback concept gaps
        # --------------------------------------------------------

        concept_gaps = [
            {
                "skill": s["skill"],
                "concept": "Advanced topics",
                "reason": "Needs deeper understanding",
                "priority": "Medium"
            }

            for s in skill_scores

            if s["performance_level"] == "Developing"
        ]

        return {
            "summary": (
                f"Interview performance: "
                f"{interview_data['overall_score_percent']:.0f}%. "
                f"Focus on strengthening weaker areas."
            ),

            "strengths": (
                [s.model_dump() for s in strengths]
                if strengths
                else [
                    {
                        "skill": skill_scores[0]["skill"],
                        "reason": "Core competency demonstrated"
                    }
                ]
                if skill_scores
                else [
                    {
                        "skill": "General",
                        "reason": "Completed interview"
                    }
                ]
            ),

            "weak_areas": [
                w.model_dump()
                for w in weak_areas
            ],

            "concept_gaps": concept_gaps,

            "recommendations": [
                r.model_dump()
                for r in recommendations
            ],

            "preparation_plan": [
                p.model_dump()
                for p in prep_plan
            ],

            "ai_generated": False
        }

    # ============================================================
    # CACHE
    # ============================================================

    def _get_cached_report(
        self,
        session_id: str,
        preparation_days: int
    ) -> Optional[InterviewReport]:
        """Retrieve cached report from database if it exists."""

        try:

            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT report_json
                FROM interview_reports
                WHERE session_id = ?
                """,
                (session_id,)
            )

            row = cursor.fetchone()

            conn.close()

            if row:

                report_data = json.loads(
                    row["report_json"]
                )

                report = InterviewReport(**report_data)
                if len(report.preparation_plan) != preparation_days:
                    return None
                if not report.questions:
                    return None
                return report

            return None

        except Exception as e:

            logger.warning(
                f"Error retrieving cached report: {e}"
            )

            return None

    def _cache_report(
        self,
        session_id: str,
        report: InterviewReport
    ):
        """Store generated report in database."""

        try:

            conn = self._get_connection()
            cursor = conn.cursor()

            # Convert report to JSON
            report_json = json.dumps(
                report.model_dump()
            )

            # Check if report already exists
            cursor.execute(
                """
                SELECT id
                FROM interview_reports
                WHERE session_id = ?
                """,
                (session_id,)
            )

            existing = cursor.fetchone()

            if existing:

                # Update existing report
                cursor.execute(
                    """
                    UPDATE interview_reports
                    SET report_json = ?,
                        overall_score = ?,
                        performance_level = ?,
                        summary = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                    """,
                    (
                        report_json,
                        report.overall_score,
                        report.performance_level,
                        report.summary,
                        session_id
                    )
                )

            else:

                # Insert new report
                cursor.execute(
                    """
                    INSERT INTO interview_reports
                    (
                        session_id,
                        overall_score,
                        performance_level,
                        summary,
                        report_json,
                        ai_generated
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        report.overall_score,
                        report.performance_level,
                        report.summary,
                        report_json,
                        report.ai_generated
                    )
                )

            conn.commit()
            conn.close()

            logger.info(
                f"Report cached for session {session_id}"
            )

        except Exception as e:

            logger.error(
                f"Error caching report: {e}"
            )

    # ============================================================
    # REGENERATE
    # ============================================================

    def regenerate_report(
        self,
        session_id: str,
        preparation_days: int = 5
    ) -> InterviewReport:
        """
        Force regenerate report and bypass cache.
        """

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM interview_reports
            WHERE session_id = ?
            """,
            (session_id,)
        )

        conn.commit()
        conn.close()

        return self.generate_report(
            session_id,
            preparation_days
        )


# ================================================================
# FACTORY
# ================================================================

def get_report_service(
    db_path: str,
    question_repo
) -> ReportService:
    """Factory function to create report service."""

    return ReportService(
        db_path,
        question_repo
    )