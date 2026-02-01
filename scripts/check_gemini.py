#!/usr/bin/env python3
"""
🔍 Gemini Model Checker
=======================
Lists available models from Google AI Studio and verifies the configured model.
"""

import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# Ensure parent directory is in path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from luma_core.config import GEMINI_CODE_MODEL, GEMINI_GENERAL_MODEL
except ImportError:
    # Fallback if config import fails
    GEMINI_CODE_MODEL = "gemini-2.5-pro"
    GEMINI_GENERAL_MODEL = "gemini-2.5-pro"

# Load env
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")

def main():
    print("\n🔍 Checking Gemini API Connectivity...\n")

    if not API_KEY:
        print("❌ Error: GOOGLE_API_KEY not found in environment variables.")
        return

    try:
        genai.configure(api_key=API_KEY)
        
        print(f"🔑 API Key found: {API_KEY[:4]}...{API_KEY[-4:]}")
        print("-" * 60)
        print(f"{'Model Name':<40} | {'Methods'}")
        print("-" * 60)

        found_code_model = False
        found_general_model = False
        
        # List models
        for m in genai.list_models():
            # Filter for generateContent support
            if 'generateContent' in m.supported_generation_methods:
                model_name = m.name.replace("models/", "")
                methods = ", ".join(m.supported_generation_methods)
                print(f"{model_name:<40} | {methods}")

                if model_name == GEMINI_CODE_MODEL:
                    found_code_model = True
                if model_name == GEMINI_GENERAL_MODEL:
                    found_general_model = True

        print("-" * 60)
        
        # Verify Configured Models
        print("\n📋 Configuration Check:")
        
        if found_code_model:
            print(f"✅ Code Model:    '{GEMINI_CODE_MODEL}' is AVAILABLE.")
        else:
            print(f"⚠️  Code Model:    '{GEMINI_CODE_MODEL}' NOT FOUND in list.")

        if found_general_model:
             if GEMINI_GENERAL_MODEL != GEMINI_CODE_MODEL:
                print(f"✅ General Model: '{GEMINI_GENERAL_MODEL}' is AVAILABLE.")
        else:
             if GEMINI_GENERAL_MODEL != GEMINI_CODE_MODEL:
                print(f"⚠️  General Model: '{GEMINI_GENERAL_MODEL}' NOT FOUND in list.")

        # Quick Test
        print("\n🧪 Running Pulse Test...")
        model = genai.GenerativeModel(GEMINI_CODE_MODEL)
        response = model.generate_content("Hello! concise response please.")
        print(f"🤖 Response: {response.text.strip()}")
        print("\n✅ System Ready.")

    except Exception as e:
        print(f"\n❌ API Error: {e}")

if __name__ == "__main__":
    main()
