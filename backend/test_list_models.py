#!/usr/bin/env python
"""List available Gemini models."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')

print("Testing available models...")
print()

# List available models
url = "https://generativelanguage.googleapis.com/v1beta/models"
headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": api_key,
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        if "models" in data:
            print(f"Available models ({len(data['models'])} total):")
            for model in data['models']:
                print(f"  - {model['name']}")
                if 'displayName' in model:
                    print(f"    Display: {model['displayName']}")
                if 'supportedGenerationMethods' in model:
                    print(f"    Methods: {', '.join(model['supportedGenerationMethods'])}")
        else:
            print("Response:", data)
    else:
        print("Error:", response.text[:300])
except Exception as e:
    print(f"ERROR: {e}")
