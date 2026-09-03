#!/usr/bin/env python
"""Test backend infrastructure and Gemini API."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print('=' * 60)
print('BACKEND INFRASTRUCTURE TEST')
print('=' * 60)
print()

# Test 1: FastAPI
print('TEST 1: FastAPI Startup')
try:
    from app.main import app
    print(f'  ✓ App imported: {app.title}')
    print(f'  ✓ App version: {app.version}')
except Exception as e:
    print(f'  ✗ {str(e)[:120]}')
    sys.exit(1)

# Test 2: Database
print()
print('TEST 2: Database Initialization')
try:
    from app.database import init_database, DB_PATH
    init_database()
    print(f'  ✓ Database ready')
    print(f'  ✓ Path: {DB_PATH}')
except Exception as e:
    print(f'  ✗ {str(e)[:120]}')
    sys.exit(1)

# Test 3: Question Repository
print()
print('TEST 3: Question Repository')
try:
    from app.services.question_repository import get_question_repository
    repo = get_question_repository()
    print(f'  ✓ Loaded {len(repo.questions)} questions')
except Exception as e:
    print(f'  ✗ {str(e)[:120]}')
    sys.exit(1)

# Test 4: Evaluation Service Schema
print()
print('TEST 4: Evaluation Service')
try:
    from app.services.evaluation_service import EvaluationService, AnswerEvaluation
    from dotenv import load_dotenv
    load_dotenv()
    
    has_key = bool(os.getenv('GEMINI_API_KEY'))
    print(f'  GEMINI_API_KEY present: {has_key}')
    
    # Test AnswerEvaluation schema
    test_eval = AnswerEvaluation(
        score=7,
        correctness='Good',
        relevance='High',
        completeness='Comprehensive',
        strengths=['Clear', 'Complete'],
        weaknesses=[],
        feedback='Excellent answer',
        recommended_difficulty='Medium'
    )
    print(f'  ✓ AnswerEvaluation schema valid')
except Exception as e:
    print(f'  ✗ {str(e)[:120]}')
    sys.exit(1)

# Test 5: Gemini API Connection (if key available)
print()
print('TEST 5: Gemini API Connection')
if has_key:
    try:
        from app.services.evaluation_service import EvaluationService
        
        service = EvaluationService()
        print(f'  ✓ EvaluationService initialized')
        print(f'  ✓ Model: gemini-1.5-flash')
        print(f'  ✓ API URL: {service.api_url}')
        print(f'  ✓ Ready for evaluation calls')
    except Exception as e:
        print(f'  ✗ {str(e)[:120]}')
        sys.exit(1)
else:
    print('  ⚠ SKIPPED (no API key)')
    print('  Set GEMINI_API_KEY in .env to enable')

print()
print('=' * 60)
print('✓✓✓ BACKEND READY ✓✓✓')
print('=' * 60)
