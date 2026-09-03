"""
Phase 6 Automation Tests - Simplified
Tests n8n integration, email delivery automation, and core functionality.
"""

import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.services.automation_service import AutomationService
from app.config import settings


def test_automation_config():
    """Test that automation configuration is loaded."""
    print("\n[TEST 1] Automation Configuration")
    try:
        assert hasattr(settings, 'n8n_webhook_url'), "n8n_webhook_url not in settings"
        assert hasattr(settings, 'app_base_url'), "app_base_url not in settings"
        print(f"  [OK] Settings configured correctly")
        print(f"    - n8n_webhook_url: {settings.n8n_webhook_url if settings.n8n_webhook_url else '(empty)'}")
        print(f"    - app_base_url: {settings.app_base_url}")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_automation_service_initialization():
    """Test AutomationService initializes correctly."""
    print("\n[TEST 2] AutomationService Initialization")
    try:
        service = AutomationService()
        assert service.webhook_url is not None
        print(f"  [OK] AutomationService initialized")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_email_validation_valid():
    """Test email validation logic - VALID emails."""
    print("\n[TEST 3] Email Validation - Valid Emails")
    try:
        service = AutomationService()
        
        # Valid emails
        valid_emails = [
            "user@example.com",
            "test.user@company.co.uk",
            "user+tag@example.com",
            "a@b.co"
        ]
        for email in valid_emails:
            assert service._is_valid_email(email), f"Should accept {email}"
        print(f"  [OK] Valid emails accepted: {len(valid_emails)}")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_email_validation_invalid():
    """Test email validation logic - INVALID emails."""
    print("\n[TEST 4] Email Validation - Invalid Emails")
    try:
        service = AutomationService()
        
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
            result = service._is_valid_email(email)
            assert not result, f"Should reject {email}, got {result}"
        print(f"  [OK] Invalid emails rejected: {len(invalid_emails)}")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_payload_generation():
    """Test that automation payload is generated correctly."""
    print("\n[TEST 5] Automation Payload Generation")
    try:
        service = AutomationService()
        
        report = {
            'overall_score': 78.5,
            'performance_level': 'Developing',
            'summary': 'Good performance with room for improvement',
            'strengths': [
                {'skill': 'Python', 'reason': 'Strong fundamentals'}
            ],
            'weak_areas': [
                {'skill': 'SQL', 'reason': 'Needs optimization practice', 'priority': 'High'}
            ],
            'recommendations': [
                {'skill': 'SQL', 'topic': 'Indexes', 'action': 'Practice query optimization', 'priority': 'High'}
            ]
        }
        
        payload = service.get_report_payload(
            session_id='test123',
            job_role='Backend Engineer',
            candidate_email='candidate@example.com',
            report=report,
            pdf_download_url='http://localhost:8000/api/interview/test123/report/pdf'
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
        
        # Verify score is converted to int (rounded via banker's rounding in Python 3)
        # 78.5 rounds to 78 (nearest even number) per Python's round()
        assert payload['overall_score'] == int(round(78.5)), f"Score conversion mismatch"
        
        print(f"  [OK] Payload generated correctly")
        print(f"    - session_id: {payload['session_id']}")
        print(f"    - overall_score: {payload['overall_score']} (rounded)")
        print(f"    - performance_level: {payload['performance_level']}")
        print(f"    - strengths: {len(payload['strengths'])} items")
        print(f"    - weak_areas: {len(payload['weak_areas'])} items")
        print(f"    - recommendations: {len(payload['recommendations'])} items")
        
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_n8n_http_request_success():
    """Test successful n8n HTTP request with mocked endpoint."""
    print("\n[TEST 6] n8n HTTP Request (Mocked Success)")
    try:
        service = AutomationService(webhook_url="http://mock-n8n.example.com/webhook")
        
        report = {
            'overall_score': 78,
            'performance_level': 'Developing',
            'summary': 'Good performance',
            'strengths': [],
            'weak_areas': [],
            'recommendations': []
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"automation_status": "queued"}).encode()
        mock_response.json.return_value = {"automation_status": "queued"}
        
        with patch('requests.post', return_value=mock_response) as mock_post:
            with patch('app.services.automation_service.AutomationService.update_automation_status'):
                result = service.send_report_to_n8n(
                    session_id='test123',
                    job_role='Python Developer',
                    candidate_email='candidate@example.com',
                    report=report,
                    pdf_download_url='http://localhost:8000/api/interview/test123/report/pdf'
                )
        
        assert result['success'] == True
        assert result['automation_status'] in ['queued', 'sent']
        assert mock_post.called
        
        print(f"  [OK] n8n HTTP request successful (mocked)")
        print(f"    - Result: {result['automation_status']}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_n8n_http_request_timeout():
    """Test n8n timeout handling."""
    print("\n[TEST 7] n8n HTTP Request (Timeout)")
    try:
        service = AutomationService(webhook_url="http://mock-n8n.example.com/webhook")
        
        report = {
            'overall_score': 78,
            'performance_level': 'Developing',
            'summary': 'Good',
            'strengths': [],
            'weak_areas': [],
            'recommendations': []
        }
        
        import requests
        with patch('requests.post', side_effect=requests.exceptions.Timeout("Timed out")):
            try:
                result = service.send_report_to_n8n(
                    session_id='test123',
                    job_role='Python Developer',
                    candidate_email='candidate@example.com',
                    report=report,
                    pdf_download_url='http://localhost:8000/api/interview/test123/report/pdf'
                )
                print(f"  ✗ Should have raised TimeoutError")
                return False
            except TimeoutError as e:
                print(f"  [OK] Timeout handled correctly: {e}")
                return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_n8n_http_request_failure():
    """Test n8n HTTP error handling."""
    print("\n[TEST 8] n8n HTTP Request (Failure)")
    try:
        service = AutomationService(webhook_url="http://mock-n8n.example.com/webhook")
        
        report = {
            'overall_score': 78,
            'performance_level': 'Developing',
            'summary': 'Good',
            'strengths': [],
            'weak_areas': [],
            'recommendations': []
        }
        
        import requests
        with patch('requests.post', side_effect=requests.exceptions.ConnectionError("Connection failed")):
            try:
                result = service.send_report_to_n8n(
                    session_id='test123',
                    job_role='Python Developer',
                    candidate_email='candidate@example.com',
                    report=report,
                    pdf_download_url='http://localhost:8000/api/interview/test123/report/pdf'
                )
                print(f"  ✗ Should have raised RuntimeError")
                return False
            except RuntimeError as e:
                print(f"  [OK] HTTP error handled correctly: {e}")
                return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_missing_webhook_url():
    """Test handling of missing webhook URL."""
    print("\n[TEST 9] Missing Webhook URL")
    try:
        service = AutomationService(webhook_url="")  # Empty webhook
        
        report = {
            'overall_score': 78,
            'performance_level': 'Developing',
            'summary': 'Good',
            'strengths': [],
            'weak_areas': [],
            'recommendations': []
        }
        
        try:
            result = service.send_report_to_n8n(
                session_id='test123',
                job_role='Python Developer',
                candidate_email='candidate@example.com',
                report=report,
                pdf_download_url='http://localhost:8000/api/interview/test123/report/pdf'
            )
            print(f"  [FAIL] Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"  [OK] Missing webhook URL handled: {e}")
            return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_invalid_email_in_request():
    """Test handling of invalid email in request."""
    print("\n[TEST 10] Invalid Email in Request")
    try:
        service = AutomationService(webhook_url="http://mock-n8n.example.com/webhook")
        
        report = {
            'overall_score': 78,
            'performance_level': 'Developing',
            'summary': 'Good',
            'strengths': [],
            'weak_areas': [],
            'recommendations': []
        }
        
        try:
            result = service.send_report_to_n8n(
                session_id='test123',
                job_role='Python Developer',
                candidate_email='notanemail',
                report=report,
                pdf_download_url='http://localhost:8000/api/interview/test123/report/pdf'
            )
            print(f"  [FAIL] Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"  [OK] Invalid email rejected: {e}")
            return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def main():
    """Run all Phase 6 automation tests."""
    print("\n" + "="*80)
    print("PHASE 6 AUTOMATION TESTS - UNIT LEVEL")
    print("="*80)
    
    tests = [
        test_automation_config,
        test_automation_service_initialization,
        test_email_validation_valid,
        test_email_validation_invalid,
        test_payload_generation,
        test_n8n_http_request_success,
        test_n8n_http_request_timeout,
        test_n8n_http_request_failure,
        test_missing_webhook_url,
        test_invalid_email_in_request,
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
        print("\n[OK] ALL PHASE 6 UNIT TESTS PASSED")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
