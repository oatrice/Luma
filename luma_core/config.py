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

# =============================================================================
# Project Configuration
# =============================================================================

PROJECTS = {
    "1": {
        "name": "JarWise-Root",
        "path": "/Users/oatrice/Software-projects/JarWise",
        "repo": "oatrice/JarWise-Root",
        "kanban_number": 7,
        "kanban_id": "PVT_kwHOATfKEM4BMuLi",
        "type": "monorepo_root",
        "sibling_repos": ["2", "3", "4"],  # Web, Backend, Android
    },
    "2": {
        "name": "JarWise (Web)",
        "path": "/Users/oatrice/Software-projects/JarWise/Web",
        "repo": "oatrice/JarWise-Web",
        "kanban_number": 7,
        "kanban_id": "PVT_kwHOATfKEM4BMuLi",
    },
    "3": {
        "name": "JarWise (Backend)",
        "path": "/Users/oatrice/Software-projects/JarWise/backend",
        "repo": "oatrice/JarWise-Backend",
        "kanban_number": 7,
        "kanban_id": "PVT_kwHOATfKEM4BMuLi",
    },
    "4": {
        "name": "JarWise (Android)",
        "path": "/Users/oatrice/Software-projects/JarWise/Android",
        "repo": "oatrice/JarWise-Android",
        "kanban_number": 7,
        "kanban_id": "PVT_kwHOATfKEM4BMuLi",
    },
    "5": {
        "name": "Tetris Battle",
        "path": "/Users/oatrice/Software-projects/Tetris-Battle",
        "repo": "oatrice/Tetris-Battle",
        "kanban_number": 6,
        "kanban_id": "PVT_kwHOATfKEM4BKZK5",
    },
    # ==========================================================================
    # The Middle Way Project
    # ==========================================================================
    "6": {
        "name": "TheMiddleWay-Root",
        "path": "/Users/oatrice/Software-projects/The Middle Way -Metadata",
        "repo": "oatrice/TheMiddleWay-Metadata",
        "kanban_number": 8,
        "kanban_id": "PVT_kwHOATfKEM4BOWVD",
        "type": "monorepo_root",
        "sibling_repos": ["7", "8", "9", "10"],  # Web, Android, iOS, Backend
    },
    "7": {
        "name": "TheMiddleWay (Web)",
        "path": "/Users/oatrice/Software-projects/The Middle Way -Metadata/Platforms/Web",
        "repo": "oatrice/TheMiddleWay-Web",
        "kanban_number": 8,
        "kanban_id": "PVT_kwHOATfKEM4BOWVD",
    },
    "8": {
        "name": "TheMiddleWay (Android)",
        "path": "/Users/oatrice/Software-projects/The Middle Way -Metadata/Platforms/Android",
        "repo": "oatrice/TheMiddleWay-Android",
        "kanban_number": 8,
        "kanban_id": "PVT_kwHOATfKEM4BOWVD",
    },
    "9": {
        "name": "TheMiddleWay (iOS)",
        "path": "/Users/oatrice/Software-projects/The Middle Way -Metadata/Platforms/iOS",
        "repo": "oatrice/TheMiddleWay-IOS",
        "kanban_number": 8,
        "kanban_id": "PVT_kwHOATfKEM4BOWVD",
    },
    "10": {
        "name": "TheMiddleWay (Backend)",
        "path": "/Users/oatrice/Software-projects/The Middle Way -Metadata/Platforms/Backend",
        "repo": "oatrice/TheMiddleWay-Backend",
        "kanban_number": 8,
        "kanban_id": "PVT_kwHOATfKEM4BOWVD",
    },
}
