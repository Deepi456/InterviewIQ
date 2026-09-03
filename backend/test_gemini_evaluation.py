#!/usr/bin/env python
"""Test real Gemini AI evaluation."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.services.evaluation_service import EvaluationService

print('=' * 80)
print('GEMINI AI EVALUATION TEST')
print('=' * 80)
print()

try:
    service = EvaluationService()
except Exception as e:
    print(f'✗ Failed to initialize EvaluationService: {e}')
    sys.exit(1)

# Test questions from the dataset
test_cases = [
    {
        'name': 'Test 1: Clearly Correct Answer',
        'question': 'What is the difference between a list and a tuple in Python?',
        'ideal_answer': 'A list is mutable (can be modified after creation) while a tuple is immutable (cannot be changed). Lists use [] and tuples use (). Both are sequences but tuples are hashable and can be used as dictionary keys.',
        'keywords': ['mutable', 'immutable', 'list', 'tuple', 'brackets', 'parentheses'],
        'candidate_answer': 'A list is mutable and can be changed after creation, using square brackets []. A tuple is immutable and cannot be modified, using parentheses (). Tuples can be used as dictionary keys because they are hashable, while lists cannot.',
        'skill': 'Python Basics',
        'difficulty': 'Easy',
        'expected_score_range': (7, 10)
    },
    {
        'name': 'Test 2: Partially Correct Answer',
        'question': 'What is the difference between a list and a tuple in Python?',
        'ideal_answer': 'A list is mutable (can be modified after creation) while a tuple is immutable (cannot be changed). Lists use [] and tuples use (). Both are sequences but tuples are hashable and can be used as dictionary keys.',
        'keywords': ['mutable', 'immutable', 'list', 'tuple'],
        'candidate_answer': 'Lists use [] and tuples use (). Lists are mutable but I\'m not sure about tuples.',
        'skill': 'Python Basics',
        'difficulty': 'Easy',
        'expected_score_range': (3, 6)
    },
    {
        'name': 'Test 3: Clearly Incorrect Answer',
        'question': 'What is the difference between a list and a tuple in Python?',
        'ideal_answer': 'A list is mutable (can be modified after creation) while a tuple is immutable (cannot be changed). Lists use [] and tuples use (). Both are sequences but tuples are hashable and can be used as dictionary keys.',
        'keywords': ['mutable', 'immutable', 'list', 'tuple'],
        'candidate_answer': 'Lists and tuples are the same thing in Python. They both use square brackets and are completely interchangeable.',
        'skill': 'Python Basics',
        'difficulty': 'Easy',
        'expected_score_range': (0, 2)
    },
    {
        'name': 'Test 4: Off-Topic Answer',
        'question': 'What is the difference between a list and a tuple in Python?',
        'ideal_answer': 'A list is mutable (can be modified after creation) while a tuple is immutable (cannot be changed). Lists use [] and tuples use (). Both are sequences but tuples are hashable and can be used as dictionary keys.',
        'keywords': ['mutable', 'immutable', 'list', 'tuple'],
        'candidate_answer': 'Python is a programming language developed by Guido van Rossum. It is used for web development and data science.',
        'skill': 'Python Basics',
        'difficulty': 'Easy',
        'expected_score_range': (0, 3)
    }
]

print()
results = []
for i, test_case in enumerate(test_cases, 1):
    print(f"--- {test_case['name']} ---")
    print(f"Question: {test_case['question'][:70]}...")
    print(f"Candidate: {test_case['candidate_answer'][:70]}...")
    print()
    
    try:
        evaluation = service.evaluate_answer(
            question=test_case['question'],
            ideal_answer=test_case['ideal_answer'],
            keywords=test_case['keywords'],
            candidate_answer=test_case['candidate_answer'],
            skill=test_case['skill'],
            difficulty=test_case['difficulty']
        )
        
        min_score, max_score = test_case['expected_score_range']
        in_range = min_score <= evaluation.score <= max_score
        status = '✓' if in_range else '⚠'
        
        print(f"{status} Score: {evaluation.score}/10 (expected {min_score}-{max_score})")
        print(f"  Correctness: {evaluation.correctness}")
        print(f"  Relevance: {evaluation.relevance}")
        print(f"  Completeness: {evaluation.completeness}")
        print(f"  Feedback: {evaluation.feedback[:60]}...")
        print(f"  Recommended: {evaluation.recommended_difficulty}")
        print()
        
        results.append({
            'test': test_case['name'],
            'score': evaluation.score,
            'passed': in_range,
            'evaluation': evaluation
        })
    
    except Exception as e:
        print(f"✗ ERROR: {str(e)[:120]}")
        print()
        results.append({
            'test': test_case['name'],
            'score': None,
            'passed': False,
            'error': str(e)
        })

print('=' * 80)
print('TEST SUMMARY')
print('=' * 80)
passed = sum(1 for r in results if r['passed'])
total = len(results)
print(f"Passed: {passed}/{total}")
print()
for r in results:
    status = '✓' if r['passed'] else '✗'
    print(f"{status} {r['test']}")
    if r['score'] is not None:
        print(f"   Score: {r['score']}")
    if 'error' in r:
        print(f"   Error: {r['error'][:80]}")

if passed == total:
    print()
    print('✓✓✓ ALL GEMINI EVALUATION TESTS PASSED ✓✓✓')
    sys.exit(0)
else:
    print()
    print(f'⚠ {total - passed} test(s) failed or errored')
    sys.exit(1)
