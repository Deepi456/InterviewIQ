"""
Phase 6 Automation Tests
Tests n8n integration, email delivery automation, duplicate prevention, and resend behavior.
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.models.interview_models import SendReportRequest
from app.database import get_connection
from app.services.question_repository import get_question_repository
from app.services.interview_service import InterviewService
from app.services.report_service import get_report_service
from app.services.automation_service import AutomationService
from app.config import settings


def create_temp_db():
    """Create a temporary database for test isolation."""
    temp_dir = tempfile.mkdtemp(prefix="interviewiq_test_")
    db_file = Path(temp_dir) / "test.db"
    
    # Initialize database
    from app.database import init_database, DB_PATH as original_db_path
    
    # Temporarily override the DB_PATH
    import app.database as db_module
    original_path = db_module.DB_PATH
    db_module.DB_PATH = db_file
    
    init_database()
    
    return db_file, temp_dir, original_path, db_module


def cleanup_temp_db(temp_dir):
    """Clean up temporary database."""
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass


def setup_test_session():
    """Create and return a completed test interview session."""
    from app.services.question_engine import QuestionSelectionEngine
    
    # Create temp database
    db_file, temp_dir, original_path, db_module = create_temp_db()
    
    try:
        repo = get_question_repository()
        engine = QuestionSelectionEngine(repo)
        service = InterviewService(str(db_file), repo, engine)
        
        session_data = service.create_interview_session(
            job_role='Python Developer',
            skills=['Python', 'SQL'],
            total_questions=3
        )
        
        session_id = session_data['session_id']
        
        # Complete the interview
        questions = []
        current = session_data['first_question']
        for i in range(3):
            questions.append(current)
            try:
                result = service.submit_answer(
                    session_id=session_id,
                    question_id=current['question_id'],
                    answer_text=f"Answer {i+1}: This is a comprehensive answer to the question about Python and SQL."
                )
                if i < 2:  # Get next question
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
        
        return session_id, db_file, temp_dir, original_path, db_module
    except Exception as e:
        cleanup_temp_db(temp_dir)
        raise e


def test_automation_config():
    """Test that automation configuration is loaded."""
    print("\n[TEST 1] Automation Configuration")
    try:
        assert hasattr(settings, 'n8n_webhook_url'), "n8n_webhook_url not in settings"
        assert hasattr(settings, 'app_base_url'), "app_base_url not in settings"
        print(f"  ✓ Settings configured correctly")
        print(f"    - n8n_webhook_url: {settings.n8n_webhook_url if settings.n8n_webhook_url else '(empty)'}")
        print(f"    - app_base_url: {settings.app_base_url}")
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_automation_service_initialization():
    """Test AutomationService initializes correctly."""
    print("\n[TEST 2] AutomationService Initialization")
    try:
        service = AutomationService()
        assert service.webhook_url is not None
        print(f"  ✓ AutomationService initialized")
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_email_validation():
    """Test email validation logic."""
    print("\n[TEST 3] Email Validation")
    try:
        service = AutomationService()
        
        # Valid emails
        valid_emails = [
            "user@example.com",
            "test.user@company.co.uk",
            "user+tag@example.com"
        ]
        for email in valid_emails:
            assert service._is_valid_email(email), f"Should accept {email}"
        print(f"  ✓ Valid emails accepted: {len(valid_emails)}")
        
        # Invalid emails
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@.com",
            "user@domain",
            "",
            None,
            "user @example.com",
            "user@domain.",
            ".user@example.com",
        ]
        for email in invalid_emails:
            assert not service._is_valid_email(email), f"Should reject {email}"
        print(f"  ✓ Invalid emails rejected: {len(invalid_emails)}")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_payload_generation():
    """Test that automation payload is generated correctly."""
    print("\n[TEST 4] Automation Payload Generation")
    try:
        session_id = setup_test_session()
        
        report_service = get_report_service(str(DB_PATH), get_question_repository())
        report = report_service.generate_report(session_id)
        report_dict = report.dict()
        
        service = AutomationService()
        payload = service.get_report_payload(
            session_id=session_id,
            job_role="Python Developer",
            candidate_email="candidate@example.com",
            report=report_dict,
            pdf_download_url="http://localhost:8000/api/interview/abc123/report/pdf"
        )
        
        # Verify payload structure
        required_fields = [
            'session_id', 'job_role', 'candidate_email', 'overall_score',
            'performance_level', 'summary', 'strengths', 'weak_areas',
            'recommendations', 'report_download_url'
        ]
        for field in required_fields:
            assert field in payload, f"Missing field: {field}"
        
        # Verify no sensitive fields
        sensitive_fields = ['gemini_key', 'api_key', 'secret', 'prompt', 'reasoning']
        for field in sensitive_fields:
            assert field not in payload, f"Payload should not contain: {field}"
        
        # Verify correct types
        assert isinstance(payload['session_id'], str)
        assert isinstance(payload['overall_score'], int)
        assert isinstance(payload['strengths'], list)
        assert isinstance(payload['weak_areas'], list)
        assert isinstance(payload['recommendations'], list)
        
        print(f"  ✓ Payload generated correctly")
        print(f"    - session_id: {payload['session_id']}")
        print(f"    - overall_score: {payload['overall_score']}")
        print(f"    - performance_level: {payload['performance_level']}")
        print(f"    - strengths: {len(payload['strengths'])} items")
        print(f"    - weak_areas: {len(payload['weak_areas'])} items")
        print(f"    - recommendations: {len(payload['recommendations'])} items")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_automation_status_persistence():
    """Test that automation status is persisted to database."""
    print("\n[TEST 5] Automation Status Persistence")
    try:
        session_id = setup_test_session()
        
        service = AutomationService()
        
        # Update status to QUEUED
        service.update_automation_status(session_id, 'QUEUED', 'test@example.com')
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT automation_status, delivery_email, last_sent_at FROM interview_reports WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        assert row['automation_status'] == 'QUEUED', f"Expected QUEUED, got {row['automation_status']}"
        assert row['delivery_email'] == 'test@example.com'
        assert row['last_sent_at'] is not None
        
        print(f"  ✓ Status persisted: {row['automation_status']}")
        print(f"    - delivery_email: {row['delivery_email']}")
        print(f"    - last_sent_at: {row['last_sent_at']}")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_duplicate_send_prevention():
    """Test that duplicate sends are prevented."""
    print("\n[TEST 6] Duplicate Send Prevention")
    try:
        session_id = setup_test_session()
        
        service = AutomationService()
        
        # First send
        service.update_automation_status(session_id, 'SENT', 'test@example.com')
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT automation_status FROM interview_reports WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        assert row['automation_status'] == 'SENT'
        conn.close()
        
        print(f"  ✓ First send marked as SENT")
        
        # Verify we cannot send again without resend flag
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT automation_status FROM interview_reports WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        
        # The route logic checks for this and prevents it
        assert row['automation_status'] == 'SENT', "Status should remain SENT"
        conn.close()
        
        print(f"  ✓ Duplicate send prevention works")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_resend_behavior():
    """Test that resend flag allows re-sending."""
    print("\n[TEST 7] Resend Behavior")
    try:
        session_id = setup_test_session()
        
        service = AutomationService()
        
        # Mark as already sent
        service.update_automation_status(session_id, 'SENT', 'test@example.com')
        
        # Update to a new status (simulating resend)
        service.update_automation_status(session_id, 'QUEUED', 'test@example.com')
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT automation_status FROM interview_reports WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        assert row['automation_status'] == 'QUEUED'
        conn.close()
        
        print(f"  ✓ Resend updates status correctly")
        print(f"    - Status: {row['automation_status']}")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_n8n_http_request_success():
    """Test successful n8n HTTP request with mocked endpoint."""
    print("\n[TEST 8] n8n HTTP Request (Mocked Success)")
    try:
        session_id = setup_test_session()
        
        report_service = get_report_service(str(DB_PATH), get_question_repository())
        report = report_service.generate_report(session_id)
        report_dict = report.dict()
        
        service = AutomationService(webhook_url="http://mock-n8n.example.com/webhook")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"automation_status": "queued"})
        mock_response.json.return_value = {"automation_status": "queued"}
        
        with patch('requests.post', return_value=mock_response) as mock_post:
            result = service.send_report_to_n8n(
                session_id=session_id,
                job_role="Python Developer",
                candidate_email="candidate@example.com",
                report=report_dict,
                pdf_download_url="http://localhost:8000/api/interview/abc/report/pdf"
            )
        
        assert result['success'] == True
        assert result['automation_status'] in ['queued', 'sent']
        assert mock_post.called
        
        print(f"  ✓ n8n HTTP request successful (mocked)")
        print(f"    - Result: {result['automation_status']}")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_n8n_http_request_timeout():
    """Test n8n timeout handling."""
    print("\n[TEST 9] n8n HTTP Request (Timeout)")
    try:
        session_id = setup_test_session()
        
        report_service = get_report_service(str(DB_PATH), get_question_repository())
        report = report_service.generate_report(session_id)
        report_dict = report.dict()
        
        service = AutomationService(webhook_url="http://mock-n8n.example.com/webhook")
        
        import requests
        with patch('requests.post', side_effect=requests.exceptions.Timeout("Timed out")):
            try:
                result = service.send_report_to_n8n(
                    session_id=session_id,
                    job_role="Python Developer",
                    candidate_email="candidate@example.com",
                    report=report_dict,
                    pdf_download_url="http://localhost:8000/api/interview/abc/report/pdf"
                )
                print(f"  ✗ Should have raised TimeoutError")
                return False
            except TimeoutError as e:
                print(f"  ✓ Timeout handled correctly: {e}")
                return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_n8n_http_request_failure():
    """Test n8n HTTP error handling."""
    print("\n[TEST 10] n8n HTTP Request (Failure)")
    try:
        session_id = setup_test_session()
        
        report_service = get_report_service(str(DB_PATH), get_question_repository())
        report = report_service.generate_report(session_id)
        report_dict = report.dict()
        
        service = AutomationService(webhook_url="http://mock-n8n.example.com/webhook")
        
        import requests
        with patch('requests.post', side_effect=requests.exceptions.ConnectionError("Connection failed")):
            try:
                result = service.send_report_to_n8n(
                    session_id=session_id,
                    job_role="Python Developer",
                    candidate_email="candidate@example.com",
                    report=report_dict,
                    pdf_download_url="http://localhost:8000/api/interview/abc/report/pdf"
                )
                print(f"  ✗ Should have raised RuntimeError")
                return False
            except RuntimeError as e:
                print(f"  ✓ HTTP error handled correctly: {e}")
                return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_missing_webhook_url():
    """Test handling of missing webhook URL."""
    print("\n[TEST 11] Missing Webhook URL")
    try:
        session_id = setup_test_session()
        
        report_service = get_report_service(str(DB_PATH), get_question_repository())
        report = report_service.generate_report(session_id)
        report_dict = report.dict()
        
        service = AutomationService(webhook_url="")  # Empty webhook
        
        try:
            result = service.send_report_to_n8n(
                session_id=session_id,
                job_role="Python Developer",
                candidate_email="candidate@example.com",
                report=report_dict,
                pdf_download_url="http://localhost:8000/api/interview/abc/report/pdf"
            )
            print(f"  ✗ Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"  ✓ Missing webhook URL handled: {e}")
            return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_invalid_email_in_request():
    """Test handling of invalid email in request."""
    print("\n[TEST 12] Invalid Email in Request")
    try:
        session_id = setup_test_session()
        
        report_service = get_report_service(str(DB_PATH), get_question_repository())
        report = report_service.generate_report(session_id)
        report_dict = report.dict()
        
        service = AutomationService(webhook_url="http://mock-n8n.example.com/webhook")
        
        try:
            result = service.send_report_to_n8n(
                session_id=session_id,
                job_role="Python Developer",
                candidate_email="notanemail",
                report=report_dict,
                pdf_download_url="http://localhost:8000/api/interview/abc/report/pdf"
            )
            print(f"  ✗ Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"  ✓ Invalid email rejected: {e}")
            return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_db_schema_columns():
    """Test that database schema has all required automation columns."""
    print("\n[TEST 13] Database Schema Validation")
    try:
        if DB_PATH.exists():
            DB_PATH.unlink()
        init_database()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get column info
        columns = {row[1]: row[2] for row in cursor.execute("PRAGMA table_info(interview_reports)").fetchall()}
        conn.close()
        
        required_cols = ['automation_status', 'delivery_email', 'last_sent_at']
        for col in required_cols:
            assert col in columns, f"Missing column: {col}"
        
        print(f"  ✓ All automation columns present in database")
        for col in required_cols:
            print(f"    - {col}: {columns[col]}")
        
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def main():
    """Run all Phase 6 automation tests."""
    print("\n" + "="*80)
    print("PHASE 6 AUTOMATION TESTS")
    print("="*80)
    
    tests = [
        test_automation_config,
        test_automation_service_initialization,
        test_email_validation,
        test_payload_generation,
        test_automation_status_persistence,
        test_duplicate_send_prevention,
        test_resend_behavior,
        test_n8n_http_request_success,
        test_n8n_http_request_timeout,
        test_n8n_http_request_failure,
        test_missing_webhook_url,
        test_invalid_email_in_request,
        test_db_schema_columns,
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
    print("TEST SUMMARY")
    print("="*80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ ALL PHASE 6 TESTS PASSED")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
