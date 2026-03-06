import os
import shutil
import filecmp
from typing import Optional, List, Dict

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
        
        valid_paths = [p for p in paths if os.path.exists(os.path.join(p, "task.md"))]
        
        if not valid_paths:
            return None
            
        return max(valid_paths, key=os.path.getmtime)

    @classmethod
    def get_all_sessions(cls) -> List[Dict]:
        """Return all valid sessions sorted by mtime (newest first), with preview."""
        if not os.path.exists(cls.DEFAULT_BRAIN_PATH):
            return []

        sessions = []
        for f in os.listdir(cls.DEFAULT_BRAIN_PATH):
            path = os.path.join(cls.DEFAULT_BRAIN_PATH, f)
            task_file = os.path.join(path, "task.md")
            if os.path.isdir(path) and os.path.exists(task_file):
                # Read first line as preview
                try:
                    with open(task_file, "r", encoding="utf-8") as tf:
                        preview = tf.readline().strip()
                except Exception:
                    preview = "(unreadable)"

                sessions.append({
                    "path": path,
                    "session_id": os.path.basename(path),
                    "preview": preview,
                    "mtime": os.path.getmtime(path),
                })

        sessions.sort(key=lambda s: s["mtime"], reverse=True)
        return sessions

    @classmethod
    def _find_feature_dir(cls, project_dir: str, issue_number: int) -> Optional[str]:
        """Find existing feature directory for an issue under docs/features/."""
        features_root = os.path.join(project_dir, "docs", "features")
        if not os.path.exists(features_root):
            return None
        for d in os.listdir(features_root):
            if d.startswith(f"{issue_number}_") or f"issue-{issue_number}" in d:
                return os.path.join(features_root, d)
        return None

    @classmethod
    def _versioned_copy(cls, src: str, target_dir: str, filename: str, session_path: Optional[str] = None) -> Optional[str]:
        """Copy src to target_dir/filename with versioning. Returns dest path or None if skipped."""
        name, ext = os.path.splitext(filename)
        dst = os.path.join(target_dir, filename)
        
        # Read content if it's a markdown file to replace absolute paths with relative ones
        content_to_write = None
        if ext.lower() == ".md" and session_path:
            try:
                with open(src, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Replace absolute brain session path with relative `./`
                # Covers both plain text paths and file:// paths used in markdown
                content_to_write = content.replace(f"file://{session_path}/", "./")
                content_to_write = content_to_write.replace(f"{session_path}/", "./")
            except Exception:
                pass

        if os.path.exists(dst):
            # Compare based on parsed content if available, else use filecmp
            identical = False
            if content_to_write is not None:
                try:
                    with open(dst, "r", encoding="utf-8") as f:
                        identical = f.read() == content_to_write
                except Exception:
                    pass
            else:
                identical = filecmp.cmp(src, dst, shallow=False)
                
            if identical:
                return None
                
            version = 2
            while os.path.exists(os.path.join(target_dir, f"{name}_v{version}{ext}")):
                version += 1
            dst = os.path.join(target_dir, f"{name}_v{version}{ext}")

        if content_to_write is not None:
            with open(dst, "w", encoding="utf-8") as f:
                f.write(content_to_write)
        else:
            shutil.copy2(src, dst)
            
        return dst

    @classmethod
    def sync_to_repo(cls, project_dir: str, issue_number: int, session_path: Optional[str] = None) -> List[str]:
        """Syncs brain artifacts into the project dir. Uses session_path if given, else auto-detects latest."""
        if session_path:
            if not os.path.isdir(session_path):
                return []
        else:
            session_path = cls.get_latest_session()
            if not session_path:
                return []

        feature_dir = cls._find_feature_dir(project_dir, issue_number)
        if not feature_dir:
            features_root = os.path.join(project_dir, "docs", "features")
            feature_dir = os.path.join(features_root, f"{issue_number}_issue-{issue_number}")

        target_dir = os.path.join(feature_dir, "ai_brain")
        os.makedirs(target_dir, exist_ok=True)

        synced_files = []
        for entry in os.listdir(session_path):
            # Skip hidden files/dirs and .resolve.* files
            if entry.startswith(".") or entry.startswith(".resolve."):
                continue
            src = os.path.join(session_path, entry)
            # Skip subdirectories — only sync files
            if not os.path.isfile(src):
                continue
            dst = cls._versioned_copy(src, target_dir, entry, session_path)
            if dst:
                rel_path = os.path.relpath(dst, project_dir)
                synced_files.append(rel_path)

        return synced_files
