#!/usr/bin/env python
"""Test Gemini API connectivity."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print(f"API Key length: {len(api_key) if api_key else 0}")
print(f"API Key starts with: {api_key[:10] if api_key else 'None'}...")
print()

# Test 1: Try the standard generativelanguage API endpoint
print("=" * 60)
print("TEST 1: Standard generativelanguage.googleapis.com endpoint")
print("=" * 60)

model = "gemini-1.5-flash"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

payload = {
    "contents": [
        {
            "parts": [
                {
                    "text": "Hello, what is 2+2?"
                }
            ]
        }
    ]
}

headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": api_key,
}

print(f"URL: {url}")
print(f"Headers: Content-Type + x-goog-api-key")
print()

try:
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:300]}")
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=" * 60)
print("TEST 2: Try URL parameter auth (legacy format)")
print("=" * 60)

url_with_key = f"{url}?key={api_key}"
headers_no_key = {
    "Content-Type": "application/json",
}

print(f"URL: {url_with_key[:80]}...")
print()

try:
    response = requests.post(url_with_key, json=payload, headers=headers_no_key, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:300]}")
except Exception as e:
    print(f"ERROR: {e}")
