import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import json

# --- Config ---
GLOBAL_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".luma_global.json"
)

# Default values
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini_cli")
AGENT_CLI = os.getenv("AGENT_CLI", "gemini_cli")
FALLBACK_ACTIVE_INDEX = 0
FALLBACK_LAST_RESET = 0.0

# Gemini CLI Model Selection
AVAILABLE_GEMINI_CLI_MODELS = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3-pro-preview",
    "gemini-2.5-flash-lite",
]
GEMINI_CLI_MODEL = os.getenv("GEMINI_CLI_MODEL", "gemini-3-flash-preview")

# Load overrides from global config
if os.path.exists(GLOBAL_CONFIG_FILE):
    try:
        with open(GLOBAL_CONFIG_FILE, "r") as f:
            _global_cfg = json.load(f)
            LLM_PROVIDER = _global_cfg.get("LLM_PROVIDER", LLM_PROVIDER)
            AGENT_CLI = _global_cfg.get("AGENT_CLI", AGENT_CLI)
            GEMINI_CLI_MODEL = _global_cfg.get("GEMINI_CLI_MODEL", GEMINI_CLI_MODEL)
            # Global fallbacks as ultimate backup
            FALLBACK_ACTIVE_INDEX = _global_cfg.get("FALLBACK_ACTIVE_INDEX", 0)
            FALLBACK_LAST_RESET = _global_cfg.get("FALLBACK_LAST_RESET", 0.0)
    except Exception:
        pass


def get_fallback_info(project_path: str = None):
    """Get fallback index and reset time, preferring local project config"""
    # 1. Try local project config first
    if project_path:
        local_cfg_path = os.path.join(project_path, ".luma_dev.json")
        if os.path.exists(local_cfg_path):
            try:
                with open(local_cfg_path, "r") as f:
                    local_cfg = json.load(f)
                    return local_cfg.get("FALLBACK_ACTIVE_INDEX", 0), local_cfg.get(
                        "FALLBACK_LAST_RESET", 0.0
                    )
            except Exception:
                pass

    # 2. Fallback to global variables loaded at startup
    return FALLBACK_ACTIVE_INDEX, FALLBACK_LAST_RESET


def save_fallback_index(index: int, project_path: str = None):
    """Save the fallback index to local project config or global config"""
    import time

    global FALLBACK_ACTIVE_INDEX, FALLBACK_LAST_RESET
    FALLBACK_ACTIVE_INDEX = index
    FALLBACK_LAST_RESET = time.time()

    # 1. Save to Local Project Config (Recommended)
    if project_path:
        try:
            local_cfg_path = os.path.join(project_path, ".luma_dev.json")
            local_config = {}
            if os.path.exists(local_cfg_path):
                with open(local_cfg_path, "r") as f:
                    local_config = json.load(f)

            local_config["FALLBACK_ACTIVE_INDEX"] = index
            local_config["FALLBACK_LAST_RESET"] = FALLBACK_LAST_RESET

            with open(local_cfg_path, "w") as f:
                json.dump(local_config, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save local fallback index: {e}")

    # 2. Also sync to global for cross-project consistency if no local path provided
    try:
        current_config = {}
        if os.path.exists(GLOBAL_CONFIG_FILE):
            with open(GLOBAL_CONFIG_FILE, "r") as f:
                current_config = json.load(f)

        current_config["FALLBACK_ACTIVE_INDEX"] = index
        current_config["FALLBACK_LAST_RESET"] = FALLBACK_LAST_RESET
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            json.dump(current_config, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save global fallback index: {e}")


def save_gemini_cli_model(model: str):
    """Save the selected Gemini CLI model to global config and update runtime."""
    global GEMINI_CLI_MODEL
    GEMINI_CLI_MODEL = model

    try:
        current_config = {}
        if os.path.exists(GLOBAL_CONFIG_FILE):
            with open(GLOBAL_CONFIG_FILE, "r") as f:
                current_config = json.load(f)

        current_config["GEMINI_CLI_MODEL"] = model
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            json.dump(current_config, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save Gemini CLI model: {e}")


# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_CODE_MODEL = "qwen/qwen3-coder:free"
OPENROUTER_GENERAL_MODEL = "mistralai/mistral-7b-instruct:free"

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o"

# Gemini Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_CODE_MODEL = "gemini-2.5-pro"
GEMINI_GENERAL_MODEL = "gemini-2.5-pro"
GEMINI_API_FALLBACK_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Akasa Notification Configuration
AKASA_API_URL = os.getenv("AKASA_API_URL", "http://localhost:8000")
AKASA_API_KEY = os.getenv("AKASA_API_KEY", "default-dev-key")
AKASA_CHAT_ID = os.getenv("AKASA_CHAT_ID", "")

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
    # ==========================================================================
    # Default Custom Projects
    # ==========================================================================
    "11": {
        "name": "Akasa",
        "path": "/Users/oatrice/Software-projects/Akasa",
        "repo": "oatrice/Akasa",
        "kanban_number": 9,
        "kanban_id": "PVT_kwHOATfKEM4BQ-3x",
    },
}

# --- Load Custom Projects from Global Config ---
try:
    if os.path.exists(GLOBAL_CONFIG_FILE):
        with open(GLOBAL_CONFIG_FILE, "r") as f:
            _cfg = json.load(f)
            custom_projects_data = _cfg.get("custom_projects", {})
            # Merge custom projects into PROJECTS dictionary
            # Custom projects might overwrite existing keys if not careful,
            # ideally keys are unique or sequential.
            for key, val in custom_projects_data.items():
                PROJECTS[key] = val
except Exception:
    pass
