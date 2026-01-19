
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load API Key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ GOOGLE_API_KEY not found in .env")
else:
    print(f"🔑 Using API Key: ...{api_key[-5:]}")
    try:
        genai.configure(api_key=api_key)
        print("📡 Fetching available models...")
        
        models = genai.list_models()
        found = False
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                found = True
        
        if not found:
            print("⚠️ No models found with 'generateContent' capability.")
            
    except Exception as e:
        print(f"❌ Error fetching models: {e}")
