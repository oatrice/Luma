import os
from luma_core import config

def ensure_artifact_gitignore(project_path: str) -> None:
    """Ensure that the project's .gitignore is ignoring AI Agent artifacts.
    
    If AUTO_UPDATE_GITIGNORE is enabled in config, this function will safely
    append the required patterns to the .gitignore file if they are missing.
    """
    if not getattr(config, "AUTO_UPDATE_GITIGNORE", True):
        return

    if not project_path or not os.path.isdir(project_path):
        return

    gitignore_path = os.path.join(project_path, ".gitignore")
    content = ""
    
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return

    missing_patterns = []
    
    # Check for .agents/ and docs/features/
    if ".agents" not in content:
        missing_patterns.append(".agents/")
        
    if "docs/features" not in content:
        missing_patterns.append("docs/features/")

    if not missing_patterns:
        return

    try:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            if content and not content.endswith("\n"):
                f.write("\n")
            f.write("\n# AI Agent Artifacts\n")
            for pattern in missing_patterns:
                f.write(f"{pattern}\n")
    except Exception as e:
        print(f"Warning: Failed to update .gitignore: {e}")
