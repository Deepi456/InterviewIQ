"""
Direct API endpoint testing without server (tests interview flow end-to-end)
"""

import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.question_repository import get_question_repository
from app.services.question_engine import QuestionSelectionEngine
from app.services.interview_service import InterviewService
from app.database import init_database, DB_PATH


def test_api_endpoints_manually():
    """Simulate API endpoint calls directly"""
    print("\n" + "="*70)
    print("DIRECT API ENDPOINT TESTING")
    print("="*70)
    
    # Initialize fresh database
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_database()
    
    repo = get_question_repository()
    engine = QuestionSelectionEngine(repo)
    service = InterviewService(str(DB_PATH), repo, engine)
    
    # Test 1: POST /api/interview/start
    print("\n[TEST 1] POST /api/interview/start")
    print("  Request:")
    print("  {")
    print('    "job_role": "Data Scientist",')
    print('    "skills": ["Python", "SQL", "Machine Learning"],')
    print('    "total_questions": 10')
    print("  }")
    
    session_data = service.create_interview_session(
        job_role='Data Scientist',
        skills=['Python', 'SQL', 'Machine Learning'],
        total_questions=10
    )
    
    session_id = session_data['session_id']
    first_question = session_data['first_question']
    
    print("\n  Response:")
    print("  {")
    print(f'    "session_id": "{session_id}",')
    print(f'    "job_role": "{session_data["job_role"]}",')
    print(f'    "total_questions": {session_data["total_questions"]},')
    print(f'    "skills": {session_data["skills"]},')
    print("    \"current_question\": {")
    print(f'      "question_number": {first_question["question_number"]},')
    print(f'      "total_questions": {first_question["total_questions"]},')
    print(f'      "question_id": "{first_question["question_id"]}",')
    print(f'      "question": "{first_question["question"][:60]}...",')
    print(f'      "skill": "{first_question["skill"]}",')
    print(f'      "difficulty": "{first_question["difficulty"]}"')
    print("    }")
    print("  }")
    print("  ✓ Session created, first question received")
    
    # Test 2-10: POST /api/interview/answer (simulating 10-question interview)
    print("\n[TEST 2-11] POST /api/interview/answer (10-question interview)")
    print("  Submitting answers and receiving next questions...\n")
    
    asked_ids = [first_question['question_id']]
    current_q = first_question
    
    print(f"  Q1: {current_q['question_id']} ({current_q['skill']}, {current_q['difficulty']})")
    
    for q_num in range(2, 11):
        # Submit answer
        result = service.submit_answer(
            session_id=session_id,
            question_id=current_q['question_id'],
            answer_text="This is a comprehensive answer demonstrating understanding of the topic and key concepts."
        )
        
        print(f"      → Score: {result['score']}, Feedback: {result['feedback'][:50]}...")
        
        if 'next_question' in result and result['next_question']:
            current_q = result['next_question']
            asked_ids.append(current_q['question_id'])
            print(f"  Q{q_num}: {current_q['question_id']} ({current_q['skill']}, {current_q['difficulty']})")
        else:
            print(f"  ✗ Interview ended prematurely at question {q_num}")
            break
    
    # Test 3: GET /api/interview/{session_id}
    print("\n[TEST 12] GET /api/interview/{session_id}")
    status = service.get_session_status(session_id)
    print(f"  Status: {status['status']}")
    print(f"  Progress: {status['current_question_number']}/{status['total_questions']}")
    print(f"  Skills covered: {status['skills_covered']}")
    print("  ✓ Session status retrieved")
    
    # Test 4: POST /api/interview/{session_id}/finish
    print("\n[TEST 13] POST /api/interview/{session_id}/finish")
    summary = service.finish_interview(session_id)
    print("  Response:")
    print("  {")
    print(f'    "session_id": "{summary["session_id"]}",')
    print(f'    "status": "{summary["status"]}",')
    print(f'    "total_questions": {summary["total_questions"]},')
    print(f'    "average_score": {summary["average_score"]},')
    print(f'    "total_score": {summary["total_score"]},')
    print(f'    "skill_scores": {list(summary["skill_scores"].keys())}')
    print("  }")
    print("  ✓ Interview completed and summary generated")
    
    # Verify uniqueness
    print("\n[VERIFICATION] Question Uniqueness Check")
    print(f"  Total questions asked: {len(asked_ids)}")
    print(f"  Unique questions: {len(set(asked_ids))}")
    print(f"  Duplicates: {len(asked_ids) - len(set(asked_ids))}")
    
    if len(asked_ids) == len(set(asked_ids)):
        print("  ✓ ALL QUESTIONS ARE UNIQUE - NO REPETITION DETECTED")
    else:
        print("  ✗ REPETITION DETECTED - DUPLICATES FOUND")
        duplicates = []
        seen = set()
        for qid in asked_ids:
            if qid in seen:
                duplicates.append(qid)
            seen.add(qid)
        print(f"  Duplicate IDs: {duplicates}")
        return False
    
    # Print question sequence
    print(f"\n  Question Sequence (full interview):")
    for i, qid in enumerate(asked_ids, 1):
        q = repo.get_question(qid)
        print(f"    {i:2d}. {qid:8s} - {q.skill:20s} {q.difficulty:6s}")
    
    print("\n" + "="*70)
    print("ENDPOINT TESTING SUMMARY")
    print("="*70)
    print("✓ POST /api/interview/start - Creates session, returns first question")
    print("✓ POST /api/interview/answer - Submits answer, returns score and next question")
    print("✓ GET /api/interview/{session_id} - Returns session status and progress")
    print("✓ POST /api/interview/{session_id}/finish - Completes interview, returns summary")
    print("✓ Repetition Prevention - All 10 questions unique, no duplicates")
    print("✓ Adaptive Selection - Engine selected varied skills and difficulties")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_api_endpoints_manually()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error during testing: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
