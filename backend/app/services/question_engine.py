"""
Adaptive Question Selection Engine
Selects appropriate interview questions based on:
- Required skills from job description
- Candidate performance history
- Difficulty level progression
- Question repetition prevention
"""

import random
from typing import List, Optional, Set, Dict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceScore:
    """Tracks performance on a skill."""
    skill: str
    score: float  # 0-10
    question_count: int


class QuestionSelectionEngine:
    """Selects next interview question based on adaptive logic."""
    
    def __init__(self, question_repository):
        """
        Initialize question selection engine.
        
        Args:
            question_repository: QuestionRepository instance for accessing questions.
        """
        self.repo = question_repository
        
        # Performance thresholds for difficulty adjustment
        self.STRONG_PERFORMANCE = 8.0  # Increase difficulty
        self.WEAK_PERFORMANCE = 5.0    # Stay/decrease difficulty
        self.WEAK_SKILL_THRESHOLD = 5.0  # Prioritize weak skills
    
    def select_next_question(
        self,
        required_skills: List[str],
        asked_question_ids: Set[str],
        performance_by_skill: Dict[str, float],
        total_questions: int,
        current_question_number: int,
        preferred_difficulty: str = "Medium"
        , role: Optional[str] = None
        , interview_type: str = "Technical"
    ) -> Optional[str]:
        """
        Select next question ID for interview.
        
        Args:
            required_skills: Skills extracted from job description
            asked_question_ids: Set of question IDs already asked (prevents repetition)
            performance_by_skill: Dict mapping skill -> average score (0-10)
            total_questions: Total questions in interview
            current_question_number: Current question number (0-indexed)
        
        Returns:
            question_id of next question, or None if no questions available
        """
        
        available_role_questions = self.repo.get_role_questions(role, interview_type) if role else []

        # Role-specific questions fill gaps in the CSV bank while preserving adaptive selection.
        for question in available_role_questions:
            if question.question_id not in asked_question_ids and (question.skill in required_skills or interview_type.lower() == "behavioral"):
                return question.question_id

        # Early questions: focus on required skills, build foundation
        if current_question_number < 3:
            return self._select_foundational_question(
                required_skills, asked_question_ids, preferred_difficulty
            )
        
        # Mid questions: adapt based on performance
        if current_question_number < total_questions - 2:
            return self._select_adaptive_question(
                required_skills, asked_question_ids, performance_by_skill
            )
        
        # Final questions: reinforce weak areas or confirm strength
        return self._select_final_question(
            required_skills, asked_question_ids, performance_by_skill
        )
    
    def _select_foundational_question(
        self,
        required_skills: List[str],
        exclude_ids: Set[str],
        preferred_difficulty: str = "Medium"
    ) -> Optional[str]:
        """
        Select foundational questions to establish baseline.
        Prioritize Easy→Medium difficulty.
        """
        # Honor the selected starting difficulty before falling back to Easy.
        for skill in required_skills:
            question = self.repo.get_random_question_excluding(
                skill=skill, difficulty=preferred_difficulty,
                exclude_ids=exclude_ids
            )
            if question:
                return question.question_id
            question = self.repo.get_random_question_excluding(
                skill=skill, difficulty='Easy',
                exclude_ids=exclude_ids
            )
            if question:
                return question.question_id
        
        # Fallback to any Easy question
        question = self.repo.get_random_question_excluding(
            difficulty='Easy',
            exclude_ids=exclude_ids
        )
        return question.question_id if question else None
    
    def _select_adaptive_question(
        self,
        required_skills: List[str],
        exclude_ids: Set[str],
        performance_by_skill: Dict[str, float]
    ) -> Optional[str]:
        """
        Adapt difficulty and skill based on performance.
        
        Strategy:
        1. If weak skill (<5): ask more questions on that skill (same/easier)
        2. If strong skill (>=8): increase difficulty
        3. If medium skill (5-7): maintain difficulty
        4. Ensure skill coverage across interview
        """
        
        # Find weakest skill
        weakest_skill = None
        weakest_score = float('inf')
        
        for skill in required_skills:
            score_data = performance_by_skill.get(skill, [5.0])  # Default middle if not yet asked
            
            # Handle both list of scores and single float values
            if isinstance(score_data, list):
                skill_score = sum(score_data) / len(score_data) if score_data else 5.0
            else:
                skill_score = float(score_data)
            
            if skill_score < weakest_score:
                weakest_score = skill_score
                weakest_skill = skill
        
        # Prioritize weak skills
        if weakest_skill and weakest_score < self.WEAK_SKILL_THRESHOLD:
            logger.info(f"Prioritizing weak skill: {weakest_skill} (score: {weakest_score})")
            
            # Ask easier or same difficulty
            difficulty = 'Easy' if weakest_score < 3 else 'Medium'
            question = self.repo.get_random_question_excluding(
                skill=weakest_skill,
                difficulty=difficulty,
                exclude_ids=exclude_ids
            )
            if question:
                return question.question_id
        
        # Find strongest skill to increase difficulty
        strongest_skill = None
        strongest_score = -1
        
        for skill in required_skills:
            score_data = performance_by_skill.get(skill, [5.0])
            
            # Handle both list of scores and single float values
            if isinstance(score_data, list):
                skill_score = sum(score_data) / len(score_data) if score_data else 5.0
            else:
                skill_score = float(score_data)
            
            if skill_score > strongest_score:
                strongest_score = skill_score
                strongest_skill = skill
        
        if strongest_skill and strongest_score >= self.STRONG_PERFORMANCE:
            logger.info(f"Increasing difficulty for strong skill: {strongest_skill}")
            question = self.repo.get_random_question_excluding(
                skill=strongest_skill,
                difficulty='Hard',
                exclude_ids=exclude_ids
            )
            if question:
                return question.question_id
        
        # Default: balanced mix from required skills
        random_skill = random.choice(required_skills)
        difficulty = 'Medium'
        
        question = self.repo.get_random_question_excluding(
            skill=random_skill,
            difficulty=difficulty,
            exclude_ids=exclude_ids
        )
        if question:
            return question.question_id
        
        # Fallback: any available question
        question = self.repo.get_random_question_excluding(
            exclude_ids=exclude_ids
        )
        return question.question_id if question else None
    
    def _select_final_question(
        self,
        required_skills: List[str],
        exclude_ids: Set[str],
        performance_by_skill: Dict[str, float]
    ) -> Optional[str]:
        """
        Select final questions to reinforce learning or test confidence.
        
        Strategy:
        1. If weak areas remain: ask challenging question on weak skill
        2. If strong: test depth with Hard question
        """
        
        # Check if any skill needs reinforcement
        weak_skills = [
            skill for skill in required_skills
            if performance_by_skill.get(skill, 5.0) < self.WEAK_SKILL_THRESHOLD
        ]
        
        if weak_skills:
            skill = random.choice(weak_skills)
            # Challenge them but don't overwhelm
            difficulty = 'Medium'
            logger.info(f"Final reinforcement on weak skill: {skill}")
        else:
            # All strong: test with hard question
            skill = random.choice(required_skills)
            difficulty = 'Hard'
            logger.info(f"Final confidence test: {skill} (Hard)")
        
        question = self.repo.get_random_question_excluding(
            skill=skill,
            difficulty=difficulty,
            exclude_ids=exclude_ids
        )
        if question:
            return question.question_id
        
        # Fallback
        question = self.repo.get_random_question_excluding(
            exclude_ids=exclude_ids
        )
        return question.question_id if question else None
