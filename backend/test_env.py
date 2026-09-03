#!/usr/bin/env python
"""Test pydantic and cygrpc imports in various venv configurations."""

import sys
import os

print("=" * 60)
print("TESTING PYTHON ENVIRONMENT")
print("=" * 60)
print(f"Interpreter: {sys.executable}")
print(f"Python version: {sys.version.split()[0]}")
print()

# Test 1: Pydantic
print("TEST 1: Pydantic")
try:
    from pydantic import BaseModel, Field
    import pydantic
    print(f"  ✓ pydantic {pydantic.__version__}")
except Exception as e:
    print(f"  ✗ {str(e)[:100]}")
    sys.exit(1)

# Test 2: Pydantic Core
print("TEST 2: Pydantic Core")
try:
    import pydantic_core
    print(f"  ✓ pydantic_core {pydantic_core.__version__}")
except Exception as e:
    print(f"  ✗ {str(e)[:100]}")
    print("  (This is expected in environments with DLL policy blocks)")

# Test 3: LangChain
print("TEST 3: LangChain")
try:
    import langchain
    print(f"  ✓ langchain {langchain.__version__}")
except Exception as e:
    print(f"  ✗ {str(e)[:100]}")

# Test 4: LangChain Gemini
print("TEST 4: LangChain Gemini")
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    print(f"  ✓ langchain_google_genai available")
except Exception as e:
    print(f"  ✗ {str(e)[:100]}")
    print("  Attempting to continue anyway...")

# Test 5: FastAPI
print("TEST 5: FastAPI")
try:
    import fastapi
    print(f"  ✓ fastapi {fastapi.__version__}")
except Exception as e:
    print(f"  ✗ {str(e)[:100]}")

# Test 6: App imports
print("TEST 6: App Module Imports")
sys.path.insert(0, str(os.path.dirname(__file__)))
try:
    from app.services.evaluation_service import AnswerEvaluation
    print(f"  ✓ evaluation_service.AnswerEvaluation")
except Exception as e:
    print(f"  ✗ {str(e)[:100]}")

print()
print("=" * 60)
