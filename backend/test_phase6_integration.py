"""
Phase 6 Integration Test - API Endpoint Testing
Tests the send-report endpoint with mocked n8n responses.
"""

import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

import warnings
warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_database, DB_PATH
from app.services.question_repository import get_question_repository
from app.services.question_engine import QuestionSelectionEngine
from app.services.interview_service import InterviewService
from app.database import get_connection


def setup_complete_interview():
    """Create a complete interview session for testing."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_database()
    
    repo = get_question_repository()
    engine = QuestionSelectionEngine(repo)
    service = InterviewService(str(DB_PATH), repo, engine)
    
    session_data = service.create_interview_session(
        job_role='Python Developer',
        skills=['Python', 'SQL'],
        total_questions=2
    )
    
    session_id = session_data['session_id']
    
    # Complete the interview
    current = session_data['first_question']
    for i in range(2):
        try:
            result = service.submit_answer(
                session_id=session_id,
                question_id=current['question_id'],
                answer_text=f"Test answer {i+1} with relevant keywords about the topic."
            )
            if i < 1:
                current = result['next_question']
        except Exception:
            pass
    
    # Mark as completed
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE interview_sessions SET status = 'completed' WHERE session_id = ?",
        (session_id,)
    )
    conn.commit()
    conn.close()
    
    return session_id


def test_send_report_endpoint_success():
    """Test successful send-report endpoint call with mocked n8n."""
    print("\n[TEST 1] Send Report Endpoint - Success (Mocked n8n)")
    try:
        session_id = setup_complete_interview()
        client = TestClient(app)
        
        # Mock the n8n webhook POST request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"automation_status": "queued"}).encode()
        mock_response.json.return_value = {"automation_status": "queued"}
        
        with patch('requests.post', return_value=mock_response):
            response = client.post(
                f"/api/interview/{session_id}/send-report",
                json={"candidate_email": "test@example.com"}
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data['success'] == True
        assert data['automation_status'] in ['queued', 'sent']
        
        print(f"  [OK] Endpoint returned success")
        print(f"    - HTTP Status: {response.status_code}")
        print(f"    - Automation Status: {data['automation_status']}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_send_report_endpoint_invalid_email():
    """Test send-report endpoint with invalid email."""
    print("\n[TEST 2] Send Report Endpoint - Invalid Email")
    try:
        session_id = setup_complete_interview()
        client = TestClient(app)
        
        response = client.post(
            f"/api/interview/{session_id}/send-report",
            json={"candidate_email": "notanemail"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert 'detail' in data
        
        print(f"  [OK] Invalid email rejected")
        print(f"    - HTTP Status: {response.status_code}")
        print(f"    - Error: {data['detail']}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_send_report_endpoint_missing_session():
    """Test send-report endpoint with non-existent session."""
    print("\n[TEST 3] Send Report Endpoint - Missing Session")
    try:
        client = TestClient(app)
        
        response = client.post(
            f"/api/interview/nonexistent-session/send-report",
            json={"candidate_email": "test@example.com"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert 'detail' in data
        
        print(f"  [OK] Missing session rejected")
        print(f"    - HTTP Status: {response.status_code}")
        print(f"    - Error: {data['detail']}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_pdf_retrieval_endpoint():
    """Test PDF retrieval endpoint."""
    print("\n[TEST 4] PDF Retrieval Endpoint")
    try:
        session_id = setup_complete_interview()
        client = TestClient(app)
        
        # First get the report to ensure it's generated
        response = client.get(f"/api/interview/{session_id}/report")
        assert response.status_code == 200
        
        # Now test PDF retrieval
        response = client.get(f"/api/interview/{session_id}/report/pdf")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.headers['content-type'] == 'application/pdf'
        assert len(response.content) > 0
        
        print(f"  [OK] PDF retrieved successfully")
        print(f"    - HTTP Status: {response.status_code}")
        print(f"    - Content-Type: {response.headers['content-type']}")
        print(f"    - Size: {len(response.content)} bytes")
        
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_generation_endpoint():
    """Test report generation endpoint."""
    print("\n[TEST 5] Report Generation Endpoint")
    try:
        session_id = setup_complete_interview()
        client = TestClient(app)
        
        response = client.get(f"/api/interview/{session_id}/report")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify report structure
        required_fields = [
            'job_role', 'overall_score', 'performance_level', 'summary',
            'skill_scores', 'strengths', 'weak_areas', 'recommendations',
            'preparation_plan', 'generated_at'
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"  [OK] Report generated successfully")
        print(f"    - HTTP Status: {response.status_code}")
        print(f"    - Job Role: {data['job_role']}")
        print(f"    - Overall Score: {data['overall_score']}")
        print(f"    - Performance Level: {data['performance_level']}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_automation_status_in_database():
    """Test that automation status is persisted to database."""
    print("\n[TEST 6] Automation Status Persistence in Database")
    try:
        session_id = setup_complete_interview()
        client = TestClient(app)
        
        # Send report via API with mocked n8n
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"automation_status": "queued"}).encode()
        mock_response.json.return_value = {"automation_status": "queued"}
        
        with patch('requests.post', return_value=mock_response):
            response = client.post(
                f"/api/interview/{session_id}/send-report",
                json={"candidate_email": "test@example.com"}
            )
        
        assert response.status_code == 200
        
        # Verify database was updated
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT automation_status, delivery_email FROM interview_reports WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None, "Report not found in database"
        assert row['automation_status'] in ['QUEUED', 'SENT'], f"Unexpected status: {row['automation_status']}"
        assert row['delivery_email'] == 'test@example.com'
        
        print(f"  [OK] Automation status persisted correctly")
        print(f"    - Status: {row['automation_status']}")
        print(f"    - Email: {row['delivery_email']}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 6 integration tests."""
    print("\n" + "="*80)
    print("PHASE 6 INTEGRATION TESTS - API ENDPOINTS")
    print("="*80)
    
    tests = [
        test_send_report_endpoint_success,
        test_send_report_endpoint_invalid_email,
        test_send_report_endpoint_missing_session,
        test_pdf_retrieval_endpoint,
        test_report_generation_endpoint,
        test_automation_status_in_database,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\nUnexpected error in {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "="*80)
    print("INTEGRATION TEST SUMMARY")
    print("="*80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n[OK] ALL PHASE 6 INTEGRATION TESTS PASSED")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
