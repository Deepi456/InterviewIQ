#!/usr/bin/env python
"""Quick validation script for interview questions dataset."""

from backend.app.services.question_repository import get_question_repository

repo = get_question_repository()
report = repo.validate_dataset()

print("\n" + "="*60)
print("DATASET VALIDATION REPORT")
print("="*60)
print(f"Total Questions: {report['total_questions']}")
print(f"Status: {report['status']}")
print("\nBy Difficulty:")
for diff, count in sorted(report['by_difficulty'].items()):
    print(f"  {diff}: {count}")
print("\nBy Category:")
for cat, count in sorted(report['by_category'].items()):
    print(f"  {cat}: {count}")

if report['issues']:
    print("\nIssues (showing first 5):")
    for issue in report['issues'][:5]:
        print(f"  - {issue}")
else:
    print("\n✓ No issues found!")
print("="*60)
