import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Config ---
# Select Provider: "gemini" or "openrouter"
LLM_PROVIDER = "gemini" 

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_CODE_MODEL = "qwen/qwen3-coder:free"
OPENROUTER_GENERAL_MODEL = "mistralai/mistral-7b-instruct:free"

# Gemini Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_CODE_MODEL = "gemini-2.5-pro"
GEMINI_GENERAL_MODEL = "gemini-2.5-pro"

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Default to current directory if not dynamically overridden
TARGET_DIR = os.getcwd()
