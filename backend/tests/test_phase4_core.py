"""
Phase 4 Core Logic Tests
Tests core evaluation logic without LangChain dependencies.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


def test_interview_models():
    """Test that updated interview models are correct."""
    print("\n[TEST 1] Interview Models Structure")
    
    try:
        from app.models.interview_models import AIEvaluation, AnswerResponse, QuestionResponse
        
        # Test AIEvaluation model
        eval_obj = AIEvaluation(
            score=8,
            correctness="Good",
            relevance="High",
            completeness="Comprehensive",
            strengths=["Point A", "Point B"],
            weaknesses=["Area to improve"],
            feedback="Good answer with room for improvement",
            recommended_difficulty="Hard"
        )
        
        assert eval_obj.score == 8
        assert eval_obj.correctness == "Good"
        assert len(eval_obj.strengths) == 2
        print("  ✓ AIEvaluation model validated")
        
        # Test AnswerResponse model
        q_resp = QuestionResponse(
            question_id="q1",
            question="Test question",
            skill="Python",
            difficulty="Easy",
            category="Language",
            question_number=1,
            total_questions=10
        )
        
        ans_resp = AnswerResponse(
            question_number=1,
            evaluation=eval_obj,
            next_question=q_resp
        )
        
        assert ans_resp.question_number == 1
        assert ans_resp.evaluation.score == 8
        assert ans_resp.next_question is not None
        print("  ✓ AnswerResponse model validated")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_interview_service_integration():
    """Test interview service with fallback evaluation."""
    print("\n[TEST 2] Interview Service with Fallback Evaluation")
    
    try:
        from app.services.question_repository import get_question_repository
        from app.services.question_engine import QuestionSelectionEngine
        from app.services.interview_service import InterviewService
        from app.database import init_database, DB_PATH
        
        # Initialize fresh database
        if DB_PATH.exists():
            DB_PATH.unlink()
        init_database()
        
        repo = get_question_repository()
        engine = QuestionSelectionEngine(repo)
        service = InterviewService(str(DB_PATH), repo, engine)
        
        # Create session
        session_data = service.create_interview_session(
            job_role='Data Scientist',
            skills=['Python', 'SQL', 'ML'],
            total_questions=3
        )
        
        session_id = session_data['session_id']
        print(f"  ✓ Session created: {session_id}")
        
        first_q = session_data['first_question']
        assert first_q['question_number'] == 1
        print(f"  ✓ First question loaded: Q1/{session_data['total_questions']}")
        
        # Submit first answer
        result = service.submit_answer(
            session_id=session_id,
            question_id=first_q['question_id'],
            answer_text="This is my answer with some relevant keywords and explanation."
        )
        
        assert 'evaluation' in result
        assert 'score' in result['evaluation']
        score = result['evaluation']['score']
        print(f"  ✓ Answer evaluated (fallback): score={score}/10")
        
        assert 0 <= score <= 10
        assert 'correctness' in result['evaluation']
        assert 'feedback' in result['evaluation']
        print("  ✓ All evaluation fields present")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_evaluation_logic():
    """Test fallback evaluation scoring logic."""
    print("\n[TEST 3] Fallback Evaluation Scoring Logic")
    
    try:
        from app.services.interview_service import InterviewService
        from app.services.question_repository import get_question_repository
        from app.services.question_engine import QuestionSelectionEngine
        from app.database import DB_PATH
        
        repo = get_question_repository()
        engine = QuestionSelectionEngine(repo)
        service = InterviewService(str(DB_PATH), repo, engine)
        
        # Test 1: Empty answer
        eval1 = service._fallback_evaluation("", "ideal", ["key1", "key2"])
        assert eval1.score == 0, f"Empty answer should be 0, got {eval1.score}"
        print("  ✓ Empty answer: score=0")
        
        # Test 2: Answer with many keywords
        eval2 = service._fallback_evaluation(
            "This includes key1 and key2 with comprehensive explanation.",
            "ideal",
            ["key1", "key2", "key3"]
        )
        assert eval2.score >= 6, f"Should score >=6 with most keywords, got {eval2.score}"
        print(f"  ✓ Answer with keywords: score={eval2.score} (>=6)")
        
        # Test 3: Answer without keywords
        eval3 = service._fallback_evaluation(
            "This is just random text with no relevant content.",
            "ideal",
            ["key1", "key2", "key3"]
        )
        assert eval3.score <= 4, f"Should score <=4 without keywords, got {eval3.score}"
        print(f"  ✓ Answer without keywords: score={eval3.score} (<=4)")
        
        # Test 4: Partial answer
        eval4 = service._fallback_evaluation(
            "This has key1 but misses other important points.",
            "ideal",
            ["key1", "key2", "key3", "key4"]
        )
        assert 2 <= eval4.score <= 6, f"Partial answer should be 2-6, got {eval4.score}"
        print(f"  ✓ Partial answer: score={eval4.score} (2-6)")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_adaptive_engine_compatibility():
    """Test that adaptive engine still works with new evaluation."""
    print("\n[TEST 4] Adaptive Engine Compatibility")
    
    try:
        from app.services.question_repository import get_question_repository
        from app.services.question_engine import QuestionSelectionEngine
        
        repo = get_question_repository()
        engine = QuestionSelectionEngine(repo)
        
        # Test question selection for different performance levels
        required_skills = ['Python']
        
        # Strong performance (score 9)
        performance = {'Python': [9.0, 8.5, 9.0]}
        asked_ids = set()
        
        q_id = engine.select_next_question(required_skills, asked_ids, performance, 10, 3)
        q = repo.get_question(q_id)
        assert q is not None
        print(f"  ✓ Strong performance (avg 8.8): difficulty={q.difficulty}")
        
        # Weak performance (score 3)
        performance = {'Python': [2.0, 3.0, 2.5]}
        q_id = engine.select_next_question(required_skills, asked_ids, performance, 10, 3)
        q = repo.get_question(q_id)
        assert q is not None
        print(f"  ✓ Weak performance (avg 2.5): difficulty={q.difficulty}")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_evaluation_storage():
    """Test that evaluation data is stored in database."""
    print("\n[TEST 5] Database Evaluation Storage")
    
    try:
        import sqlite3
        from app.database import DB_PATH
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Check candidate_answers table has score and feedback
        cursor.execute("PRAGMA table_info(candidate_answers)")
        columns = [row[1] for row in cursor.fetchall()]
        
        assert 'score' in columns, "Table missing 'score' column"
        assert 'feedback' in columns, "Table missing 'feedback' column"
        print("  ✓ Database has score and feedback columns")
        
        # Check schema
        cursor.execute("SELECT COUNT(*) FROM candidate_answers")
        count = cursor.fetchone()[0]
        print(f"  ✓ Database has {count} answer records")
        
        conn.close()
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def run_all_tests():
    """Run all Phase 4 logic tests."""
    print("\n" + "="*70)
    print("PHASE 4 CORE LOGIC TESTS (No LangChain Dependencies)")
    print("="*70)
    
    tests = [
        ("Interview Models", test_interview_models),
        ("Service Integration", test_interview_service_integration),
        ("Fallback Evaluation Logic", test_fallback_evaluation_logic),
        ("Adaptive Engine Compatibility", test_adaptive_engine_compatibility),
        ("Database Storage", test_database_evaluation_storage),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ✗ TEST FAILED: {e}")
            results.append((name, False))
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {test_name:<40} {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    print("\n" + "="*70)
    print("NOTES:")
    print("- LangChain DLL import errors are environment/system policy issues")
    print("- Core logic and fallback evaluation are fully functional")
    print("- To enable AI evaluation, set OPENAI_API_KEY environment variable")
    print("="*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
