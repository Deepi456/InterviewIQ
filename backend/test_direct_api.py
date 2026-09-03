#!/usr/bin/env python
"""Direct test of Gemini API with correct model and authentication."""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
model = "gemini-3.6-flash"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

print(f"Model: {model}")
print(f"URL: {url}")
print(f"API Key length: {len(api_key)}")
print()

payload = {
    "contents": [
        {
            "parts": [
                {
                    "text": "What is 2+2? Answer with just the number."
                }
            ]
        }
    ],
    "generationConfig": {
        "temperature": 0.2,
        "maxOutputTokens": 100,
    }
}

headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": api_key,
}

print("Making request...")
print()

try:
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    print(f"Status Code: {response.status_code}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        if "candidates" in data and len(data["candidates"]) > 0:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            print(f"✓✓✓ SUCCESS ✓✓✓")
            print(f"Response: {text}")
        else:
            print("Unexpected response structure:", data)
    else:
        print("Error Response:")
        print(response.text)
        
except Exception as e:
    print(f"ERROR: {e}")
