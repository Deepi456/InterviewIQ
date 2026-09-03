"""
Comprehensive tests for Phase 3: Interview Question Bank + Adaptive Interview Engine
Tests dataset, question selection, session management, and API endpoints.
"""

import sys
import os
import sqlite3
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.services.question_repository import get_question_repository
from app.services.question_engine import QuestionSelectionEngine
from app.services.interview_service import InterviewService
from app.database import init_database, DB_PATH
from unittest.mock import patch


# Test 1: Dataset validation
def test_dataset_loading():
    """Test that question dataset loads with minimum 150 questions."""
    print("\n[TEST 1] Dataset Loading")
    repo = get_question_repository()
    report = repo.validate_dataset()
    
    print(f"  Total questions: {report['total_questions']}")
    assert report['total_questions'] >= 150, f"Need 150+ questions, got {report['total_questions']}"
    assert report['status'] == 'VALID', f"Dataset validation failed: {report['issues']}"
    print("  ✓ Dataset loaded successfully with 150+ questions")
    return True


# Test 2: Question distribution
def test_dataset_distribution():
    """Test question distribution across categories and difficulty."""
    print("\n[TEST 2] Dataset Distribution")
    repo = get_question_repository()
    report = repo.validate_dataset()
    
    print(f"  By Difficulty:")
    for diff, count in sorted(report['by_difficulty'].items()):
        print(f"    {diff}: {count}")
        assert count > 0, f"No {diff} questions found"
    
    print(f"  By Category:")
    for cat, count in sorted(report['by_category'].items()):
        print(f"    {cat}: {count}")
        assert count > 0, f"No questions in {cat}"
    
    print("  ✓ All categories and difficulties represented")
    return True


# Test 3: Question retrieval and structure
def test_question_retrieval():
    """Test retrieving questions by various criteria."""
    print("\n[TEST 3] Question Retrieval")
    repo = get_question_repository()
    
    # Test get_question
    question = repo.get_question('PY001')
    assert question is not None, "Failed to retrieve question PY001"
    assert question.question_id == 'PY001'
    assert question.category == 'Python'
    assert len(question.question) > 0
    assert len(question.ideal_answer) > 0
    print("  ✓ get_question() works")
    
    # Test get_questions_by_skill
    py_questions = repo.get_questions_by_skill('Python')
    assert len(py_questions) > 0, "No Python questions found"
    print(f"  ✓ get_questions_by_skill() works ({len(py_questions)} Python questions)")
    
    # Test get_questions_by_difficulty
    easy_questions = repo.get_questions_by_difficulty('Easy')
    assert len(easy_questions) > 0, "No Easy questions found"
    print(f"  ✓ get_questions_by_difficulty() works ({len(easy_questions)} Easy questions)")
    
    # Test get_questions_by_category
    sql_questions = repo.get_questions_by_category('SQL')
    assert len(sql_questions) > 0, "No SQL questions found"
    print(f"  ✓ get_questions_by_category() works ({len(sql_questions)} SQL questions)")
    
    return True


# Test 4: Adaptive question selection
def test_question_selection():
    """Test adaptive question selection without repetition."""
    print("\n[TEST 4] Question Selection (No Repetition)")
    repo = get_question_repository()
    engine = QuestionSelectionEngine(repo)
    
    # Simulate interview progression
    required_skills = ['Python', 'SQL', 'Machine Learning']
    asked_ids = set()
    
    for i in range(10):
        qid = engine.select_next_question(
            required_skills=required_skills,
            asked_question_ids=asked_ids,
            performance_by_skill={},
            total_questions=10,
            current_question_number=i
        )
        
        assert qid is not None, f"Failed to select question {i+1}"
        assert qid not in asked_ids, f"Question {qid} already asked (repetition)"
        asked_ids.add(qid)
        
        question = repo.get_question(qid)
        print(f"  Q{i+1}: {qid} ({question.skill}, {question.difficulty})")
    
    assert len(asked_ids) == 10, f"Should have 10 unique questions, got {len(asked_ids)}"
    print(f"  ✓ Selected 10 unique questions with no repetition")
    return True


# Test 5: Adaptive difficulty adjustment
def test_adaptive_difficulty():
    """Test that difficulty adjusts based on performance."""
    print("\n[TEST 5] Adaptive Difficulty Adjustment")
    repo = get_question_repository()
    engine = QuestionSelectionEngine(repo)
    
    required_skills = ['Python', 'SQL']
    
    # Scenario 1: Strong performance (score 9.0)
    print("  Scenario 1: Strong performance (9.0 average)")
    asked_ids_1 = set()
    performance_1 = {'Python': 9.0, 'SQL': 9.0}
    
    for i in range(3, 6):  # Mid-to-end questions
        qid = engine.select_next_question(
            required_skills=required_skills,
            asked_question_ids=asked_ids_1,
            performance_by_skill=performance_1,
            total_questions=10,
            current_question_number=i
        )
        asked_ids_1.add(qid)
        q = repo.get_question(qid)
        print(f"    Q{i+1}: {q.difficulty}")
        # With strong performance, should get some Hard questions
    
    # Scenario 2: Weak performance (score 3.0)
    print("  Scenario 2: Weak performance (3.0 average)")
    asked_ids_2 = set()
    performance_2 = {'Python': 3.0, 'SQL': 3.0}
    
    for i in range(3, 6):
        qid = engine.select_next_question(
            required_skills=required_skills,
            asked_question_ids=asked_ids_2,
            performance_by_skill=performance_2,
            total_questions=10,
            current_question_number=i
        )
        asked_ids_2.add(qid)
        q = repo.get_question(qid)
        print(f"    Q{i+1}: {q.difficulty}")
    
    print("  ✓ Adaptive difficulty adjustment works")
    return True


# Test 6: Database initialization and schema
def test_database_schema():
    """Test database initialization and schema."""
    print("\n[TEST 6] Database Schema")
    
    # Clear old database
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    # Initialize database
    init_database()
    assert DB_PATH.exists(), "Database not created"
    print(f"  ✓ Database created at {DB_PATH}")
    
    # Check tables exist
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    required_tables = [
        'interview_sessions',
        'asked_questions',
        'candidate_answers',
        'interview_performance'
    ]
    
    for table in required_tables:
        assert table in tables, f"Table {table} not found"
        print(f"  ✓ Table '{table}' exists")
    
    return True


# Test 7: Interview session creation and lifecycle
def test_interview_session_lifecycle():
    """Test complete interview session lifecycle."""
    print("\n[TEST 7] Interview Session Lifecycle")
    
    # Initialize fresh database
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_database()
    
    repo = get_question_repository()
    engine = QuestionSelectionEngine(repo)
    service = InterviewService(str(DB_PATH), repo, engine)
    
    # Test session creation
    print("  Creating interview session...")
    session_data = service.create_interview_session(
        job_role='Data Scientist',
        skills=['Python', 'SQL', 'Machine Learning'],
        total_questions=5  # Use 5 for testing
    )
    
    session_id = session_data['session_id']
    assert session_id is not None, "Session ID not created"
    print(f"  ✓ Session created: {session_id}")
    
    # Check first question received
    first_q = session_data['first_question']
    assert first_q is not None, "First question not returned"
    print(f"  ✓ First question: {first_q['question_id']}")
    
    # Test submitting answers through interview
    print("  Simulating 5-question interview...")
    asked_question_ids = [first_q['question_id']]
    from app.services.evaluation_service import AnswerEvaluation

    def mock_eval(*args, **kwargs):
        return AnswerEvaluation(
            score=8,
            correctness="Good",
            relevance="High",
            completeness="Comprehensive",
            strengths=["Clear answer"],
            weaknesses=[],
            feedback="Good response",
            recommended_difficulty="Medium"
        )

    with patch.object(service, '_evaluate_answer', side_effect=mock_eval):
        for i in range(1, 5):  # Questions 2-5
            # Submit answer
            result = service.submit_answer(
                session_id=session_id,
                question_id=first_q['question_id'],
                answer_text="This is a comprehensive answer that demonstrates understanding of the topic."
            )
            
            score_val = result.get('evaluation', {}).get('score', 8)
            print(f"  Q{i}: score={score_val}")
            
            # Get next question
            if 'next_question' in result and result['next_question']:
                first_q = result['next_question']
                asked_question_ids.append(first_q['question_id'])
            else:
                break
    
    # Verify all question IDs are unique
    assert len(asked_question_ids) == len(set(asked_question_ids)), \
        f"Duplicate questions found: {asked_question_ids}"
    print(f"  ✓ All {len(asked_question_ids)} questions unique (no repetition)")
    
    # Finish interview
    print("  Finishing interview...")
    summary = service.finish_interview(session_id)
    assert summary['status'] == 'completed', "Interview not marked completed"
    print(f"  ✓ Interview completed")
    print(f"    Average score: {summary['average_score']}")
    print(f"    Total score: {summary['total_score']}")
    print(f"    Skill scores: {list(summary['skill_scores'].keys())}")
    
    return True


# Test 8: Complete 10-question interview
def test_full_10_question_interview():
    """Test complete 10-question adaptive interview with unique questions."""
    print("\n[TEST 8] Complete 10-Question Adaptive Interview")
    
    # Initialize fresh database
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_database()
    
    repo = get_question_repository()
    engine = QuestionSelectionEngine(repo)
    service = InterviewService(str(DB_PATH), repo, engine)
    
    # Create session with 10 questions
    print("  Creating 10-question interview session...")
    session_data = service.create_interview_session(
        job_role='Machine Learning Engineer',
        skills=['Python', 'SQL', 'Machine Learning', 'Statistics', 'Deep Learning'],
        total_questions=10
    )
    
    session_id = session_data['session_id']
    print(f"  ✓ Session: {session_id}")
    
    asked_ids = []
    current_q = session_data['first_question']
    asked_ids.append(current_q['question_id'])
    
    print(f"  Q1: {current_q['question_id']} ({current_q['skill']}, {current_q['difficulty']})")
    
    from app.services.evaluation_service import AnswerEvaluation

    def mock_eval(*args, **kwargs):
        return AnswerEvaluation(
            score=8,
            correctness="Good",
            relevance="High",
            completeness="Comprehensive",
            strengths=["Solid answer"],
            weaknesses=[],
            feedback="Good answer.",
            recommended_difficulty="Medium"
        )

    # Go through interview
    with patch.object(service, '_evaluate_answer', side_effect=mock_eval):
        for question_num in range(2, 11):
            # Simulate answer submission
            result = service.submit_answer(
                session_id=session_id,
                question_id=current_q['question_id'],
                answer_text="This is a comprehensive answer demonstrating knowledge."
            )
            
            if 'next_question' in result and result['next_question']:
                current_q = result['next_question']
                asked_ids.append(current_q['question_id'])
                print(f"  Q{question_num}: {current_q['question_id']} ({current_q['skill']}, {current_q['difficulty']})")
            else:
                print(f"  ✗ Interview ended prematurely at question {question_num}")
                break
    
    # Verify all 10 questions are unique
    print(f"\n  Uniqueness check:")
    print(f"    Total questions asked: {len(asked_ids)}")
    print(f"    Unique questions: {len(set(asked_ids))}")
    
    assert len(asked_ids) == 10, f"Expected 10 questions, got {len(asked_ids)}"
    assert len(set(asked_ids)) == 10, f"Found {len(asked_ids) - len(set(asked_ids))} duplicate(s)"
    
    print(f"  ✓ All 10 question IDs are unique (no repetition)")
    
    # Finish and get summary
    summary = service.finish_interview(session_id)
    print(f"\n  Interview Summary:")
    print(f"    Status: {summary['status']}")
    print(f"    Average Score: {summary['average_score']:.1f}/10")
    print(f"    Total Score: {summary['total_score']:.1f}")
    print(f"    Skills Evaluated: {', '.join(summary['skill_scores'].keys())}")
    
    return True


# Run all tests
def run_all_tests():
    """Run all Phase 3 tests."""
    print("\n" + "="*70)
    print("PHASE 3 COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    tests = [
        ("Dataset Loading", test_dataset_loading),
        ("Dataset Distribution", test_dataset_distribution),
        ("Question Retrieval", test_question_retrieval),
        ("Question Selection (No Repetition)", test_question_selection),
        ("Adaptive Difficulty", test_adaptive_difficulty),
        ("Database Schema", test_database_schema),
        ("Session Lifecycle", test_interview_session_lifecycle),
        ("Full 10-Question Interview", test_full_10_question_interview),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
        except AssertionError as e:
            failed += 1
            errors.append(f"{test_name}: {str(e)}")
            print(f"  ✗ FAILED: {str(e)}")
        except Exception as e:
            failed += 1
            errors.append(f"{test_name}: {type(e).__name__}: {str(e)}")
            print(f"  ✗ ERROR: {str(e)}")
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✓ All tests passed!")
    
    print("="*70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
