"""
Question Repository Service
Handles loading, validating, and querying interview questions from CSV dataset.
"""

import csv
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import logging
from app.services.role_config import ROLE_QUESTION_BANK

logger = logging.getLogger(__name__)


@dataclass
class Question:
    """Represents an interview question."""
    question_id: str
    category: str
    skill: str
    difficulty: str  # Easy, Medium, Hard
    question: str
    ideal_answer: str
    keywords: List[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary (for API responses)."""
        return {
            'question_id': self.question_id,
            'category': self.category,
            'skill': self.skill,
            'difficulty': self.difficulty,
            'question': self.question,
            'keywords': self.keywords,
            # Note: ideal_answer NOT exposed to frontend (for Phase 4 LLM evaluator)
        }


class QuestionRepository:
    """Loads and manages interview question dataset."""
    
    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize question repository.
        
        Args:
            csv_path: Path to questions CSV. If None, uses default path.
        """
        if csv_path is None:
            # Default path: data/interview_questions.csv from project root
            # Path(__file__) = backend/app/services/question_repository.py
            # .parent = backend/app/services
            # .parent = backend/app
            # .parent = backend
            # .parent = project_root (InterviewIQ)
            csv_path = Path(__file__).parent.parent.parent.parent / "data" / "interview_questions.csv"
        
        self.csv_path = Path(csv_path)
        self.questions: Dict[str, Question] = {}
        self.questions_by_skill: Dict[str, List[str]] = {}
        self.questions_by_difficulty: Dict[str, List[str]] = {}
        self.questions_by_category: Dict[str, List[str]] = {}
        
        self._load_questions()

    def get_role_questions(self, role: str, interview_type: str = "Technical") -> List[Question]:
        """Return supplemental questions for roles absent from the CSV bank."""
        mode = interview_type.lower()
        return [
            Question(
                question_id=f"ROLE-{index}", category="Behavioral / HR" if item[4] == "behavioral" else item[1],
                skill=item[1], difficulty="Medium", question=item[2], ideal_answer=item[3], keywords=item[3].split()
            )
            for index, item in enumerate(ROLE_QUESTION_BANK)
            if item[0] == role and (mode == "mixed" or item[4] == mode)
        ]
    
    def _load_questions(self):
        """Load questions from CSV file."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Question dataset not found: {self.csv_path}")
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                question_id = row['question_id']
                
                # Parse keywords
                keywords = [k.strip() for k in row['keywords'].split(',')]
                
                question = Question(
                    question_id=question_id,
                    category=row['category'],
                    skill=row['skill'],
                    difficulty=row['difficulty'],
                    question=row['question'],
                    ideal_answer=row['ideal_answer'],
                    keywords=keywords
                )
                
                self.questions[question_id] = question
                
                # Index by skill
                if question.skill not in self.questions_by_skill:
                    self.questions_by_skill[question.skill] = []
                self.questions_by_skill[question.skill].append(question_id)
                
                # Index by difficulty
                if question.difficulty not in self.questions_by_difficulty:
                    self.questions_by_difficulty[question.difficulty] = []
                self.questions_by_difficulty[question.difficulty].append(question_id)
                
                # Index by category
                if question.category not in self.questions_by_category:
                    self.questions_by_category[question.category] = []
                self.questions_by_category[question.category].append(question_id)
        
        logger.info(f"✓ Loaded {len(self.questions)} questions from {self.csv_path}")
    
    def get_question(self, question_id: str) -> Optional[Question]:
        """Get single question by ID."""
        return self.questions.get(question_id)
    
    def get_questions_by_skill(self, skill: str, difficulty: Optional[str] = None) -> List[str]:
        """Get question IDs by skill, optionally filtered by difficulty."""
        if skill not in self.questions_by_skill:
            return []
        
        question_ids = self.questions_by_skill[skill]
        
        if difficulty:
            question_ids = [
                qid for qid in question_ids
                if self.questions[qid].difficulty == difficulty
            ]
        
        return question_ids
    
    def get_questions_by_difficulty(self, difficulty: str) -> List[str]:
        """Get all question IDs of specific difficulty."""
        return self.questions_by_difficulty.get(difficulty, [])
    
    def get_questions_by_category(self, category: str) -> List[str]:
        """Get all question IDs in category."""
        return self.questions_by_category.get(category, [])
    
    def get_random_question_excluding(
        self,
        skill: Optional[str] = None,
        difficulty: Optional[str] = None,
        exclude_ids: Optional[Set[str]] = None
    ) -> Optional[Question]:
        """
        Get random question matching criteria, excluding specified IDs.
        Used for interview question selection.
        """
        import random
        
        exclude_ids = exclude_ids or set()
        
        # Start with all questions
        candidates = list(self.questions.keys())
        
        # Filter by skill if provided
        if skill:
            candidates = self.get_questions_by_skill(skill, difficulty)
        elif difficulty:
            # Filter by difficulty only
            candidates = self.get_questions_by_difficulty(difficulty)
        
        # Remove already-asked questions
        candidates = [qid for qid in candidates if qid not in exclude_ids]
        
        if not candidates:
            return None
        
        question_id = random.choice(candidates)
        return self.get_question(question_id)
    
    def validate_dataset(self) -> Dict:
        """Validate dataset quality. Returns validation report."""
        report = {
            'total_questions': len(self.questions),
            'by_category': {},
            'by_difficulty': {},
            'by_skill': {},
            'issues': [],
        }
        
        # Count by category
        for category in self.questions_by_category:
            report['by_category'][category] = len(self.questions_by_category[category])
        
        # Count by difficulty
        for difficulty in self.questions_by_difficulty:
            report['by_difficulty'][difficulty] = len(self.questions_by_difficulty[difficulty])
        
        # Count by skill
        for skill in self.questions_by_skill:
            report['by_skill'][skill] = len(self.questions_by_skill[skill])
        
        # Validation checks
        seen_questions = set()
        for qid, question in self.questions.items():
            # Check unique IDs
            if qid in seen_questions:
                report['issues'].append(f"Duplicate question ID: {qid}")
            seen_questions.add(qid)
            
            # Check required fields
            if not question.question:
                report['issues'].append(f"{qid}: Empty question text")
            if not question.ideal_answer:
                report['issues'].append(f"{qid}: Empty ideal answer")
            
            # Check valid difficulty
            if question.difficulty not in ['Easy', 'Medium', 'Hard']:
                report['issues'].append(f"{qid}: Invalid difficulty '{question.difficulty}'")
        
        # Check minimum question count
        if report['total_questions'] < 150:
            report['issues'].append(
                f"Dataset has {report['total_questions']} questions, minimum 150 required"
            )
        
        report['status'] = 'VALID' if not report['issues'] else 'INVALID'
        return report


# Singleton instance
_repository: Optional[QuestionRepository] = None


def get_question_repository() -> QuestionRepository:
    """Get or create question repository singleton."""
    global _repository
    if _repository is None:
        _repository = QuestionRepository()
    return _repository


if __name__ == "__main__":
    # Validation script
    import json
    
    repo = QuestionRepository()
    report = repo.validate_dataset()
    
    print("\n" + "="*60)
    print("DATASET VALIDATION REPORT")
    print("="*60)
    print(f"Status: {report['status']}")
    print(f"Total Questions: {report['total_questions']}")
    print("\nBy Category:")
    for cat, count in sorted(report['by_category'].items()):
        print(f"  {cat}: {count}")
    print("\nBy Difficulty:")
    for diff, count in sorted(report['by_difficulty'].items()):
        print(f"  {diff}: {count}")
    print("\nBy Skill:")
    for skill, count in sorted(report['by_skill'].items()):
        print(f"  {skill}: {count}")
    
    if report['issues']:
        print("\nIssues Found:")
        for issue in report['issues']:
            print(f"  ✗ {issue}")
    else:
        print("\n✓ No issues found!")
    print("="*60)
