import os
import shutil
from typing import Optional, List

class AntigravityBrain:
    DEFAULT_BRAIN_PATH = os.path.expanduser("~/.gemini/antigravity/brain/")
    ARTIFACTS = ["task.md", "implementation_plan.md", "walkthrough.md"]

    @classmethod
    def get_latest_session(cls) -> Optional[str]:
        """Fetch the most recent session directory correctly."""
        if not os.path.exists(cls.DEFAULT_BRAIN_PATH):
            return None

        paths = []
        for f in os.listdir(cls.DEFAULT_BRAIN_PATH):
            path = os.path.join(cls.DEFAULT_BRAIN_PATH, f)
            if os.path.isdir(path):
                paths.append(path)
        
        # Keep only dirs containing at least a task.md (meaning we started actual work)
        valid_paths = [p for p in paths if os.path.exists(os.path.join(p, "task.md"))]
        
        if not valid_paths:
            return None
            
        return max(valid_paths, key=os.path.getmtime)

    @classmethod
    def sync_to_repo(cls, project_dir: str, issue_number: int) -> List[str]:
        """Syncs latest brain artifacts into the project dir and returns relative paths to the added files."""
        session_path = cls.get_latest_session()
        if not session_path:
            return []

        target_dir = os.path.join(project_dir, "docs", "ai_brain", f"issue-{issue_number}")
        os.makedirs(target_dir, exist_ok=True)

        synced_files = []
        for artifact in cls.ARTIFACTS:
            src = os.path.join(session_path, artifact)
            if os.path.exists(src):
                dst = os.path.join(target_dir, artifact)
                shutil.copy2(src, dst)
                # Return relative path for git ops
                rel_path = os.path.relpath(dst, project_dir)
                synced_files.append(rel_path)

        return synced_files
