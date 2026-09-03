#!/usr/bin/env python
"""Test script for InterviewIQ API Phase 2"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing GET /api/health...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_job_analyze_without_key():
    """Test job analysis endpoint without API key"""
    print("\n\nTesting POST /api/job/analyze (without OPENAI_API_KEY)...")
    try:
        payload = {
            "job_role": "AI/ML Intern",
            "job_description": """
            We are looking for an AI/ML Intern to join our team.
            Requirements:
            - Python programming experience
            - Understanding of Machine Learning basics
            - SQL knowledge
            - Pandas and NumPy experience
            - Scikit-learn experience
            """
        }
        response = requests.post(f"{BASE_URL}/api/job/analyze", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        if response.status_code == 500:
            print("✓ Correctly returns error when OPENAI_API_KEY is not set")
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("InterviewIQ Phase 2 API Test")
    print("=" * 60)
    
    health_ok = test_health()
    
    if health_ok:
        print("\n✓ Health check passed")
        print("\nTesting job analysis endpoint...")
        test_job_analyze_without_key()
    else:
        print("\n✗ Health check failed")
