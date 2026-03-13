import os
import shutil
import filecmp
import json
from typing import Optional, List, Dict

class AntigravityBrain:
    DEFAULT_BRAIN_PATH = os.path.expanduser("~/.gemini/antigravity/brain/")
    ARTIFACTS = ["task.md", "implementation_plan.md", "walkthrough.md"]

    @classmethod
    def get_latest_session(cls, project_dir: Optional[str] = None, issue_number: Optional[int] = None) -> Optional[str]:
        """Fetch the most recent session directory correctly, with optional content matching."""
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
            
        valid_paths.sort(key=os.path.getmtime, reverse=True)
        
        # If no matching criteria provided, return newest
        if not project_dir and not issue_number:
            return valid_paths[0]
            
        project_name = os.path.basename(project_dir.rstrip("/")) if project_dir else None
        issue_str = str(issue_number) if issue_number else None
        
        for path in valid_paths:
            task_file = os.path.join(path, "task.md")
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                match_project = True if not project_name else (project_name.lower() in content.lower())
                match_issue = True if not issue_str else (issue_str in content)
                
                if match_project or match_issue:
                    return path
            except Exception:
                continue
                
        # Fallback to newest if no strict match
        return valid_paths[0]

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
    def _should_skip_file(cls, filename: str) -> bool:
        """Check if a file should be skipped during sync.
        
        Skips:
        - Hidden files (starting with '.')
        - .resolve.* files
        - *.metadata.json files
        - *.resolved and *.resolved.N files
        """
        import re
        if filename.startswith("."):
            return True
        if filename.endswith(".metadata.json"):
            return True
        if re.search(r'\.resolved(\.\d+)?$', filename):
            return True
        return False

    @classmethod
    def sync_to_repo(cls, project_dir: str, issue_number: int, session_path: Optional[str] = None) -> List[str]:
        """Syncs brain artifacts into the project dir. Uses session_path if given, else auto-detects latest matching."""
        if session_path:
            if not os.path.isdir(session_path):
                return []
        else:
            session_path = cls.get_latest_session(project_dir, issue_number)
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
            # Skip unwanted files (hidden, .resolve.*, .metadata.json, .resolved)
            if cls._should_skip_file(entry):
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

class GeminiCLIBrain:
    DEFAULT_SESSION_PATH = os.path.expanduser("~/.gemini/tmp/luma/chats/")

    @classmethod
    def get_latest_session(cls, project_dir: Optional[str] = None, issue_number: Optional[int] = None) -> Optional[str]:
        """Fetch the most recent session JSON file, with optional content matching."""
        if not os.path.exists(cls.DEFAULT_SESSION_PATH):
            return None

        files = [os.path.join(cls.DEFAULT_SESSION_PATH, f) for f in os.listdir(cls.DEFAULT_SESSION_PATH) if f.endswith(".json")]
        if not files:
            return None
            
        files.sort(key=os.path.getmtime, reverse=True)
        
        if not project_dir and not issue_number:
            return files[0]
            
        project_name = os.path.basename(project_dir.rstrip("/")) if project_dir else None
        issue_str = str(issue_number) if issue_number else None
        
        for path in files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                match_project = True if not project_name else (project_name.lower() in content.lower())
                match_issue = True if not issue_str else (issue_str in content)
                
                if match_project or match_issue:
                    return path
            except Exception:
                continue
                
        return files[0]

    @classmethod
    def get_all_sessions(cls) -> List[Dict]:
        """Return all valid sessions sorted by mtime (newest first), with preview."""
        if not os.path.exists(cls.DEFAULT_SESSION_PATH):
            return []

        sessions = []
        for f in os.listdir(cls.DEFAULT_SESSION_PATH):
            if not f.endswith(".json"):
                continue
            path = os.path.join(cls.DEFAULT_SESSION_PATH, f)
            
            # Read first user message as preview
            try:
                with open(path, "r", encoding="utf-8") as tf:
                    data = json.load(tf)
                    messages = data.get("messages", [])
                    preview = "(empty session)"
                    if messages:
                        first_msg = messages[0]
                        if isinstance(first_msg.get("content"), list):
                            preview = first_msg["content"][0].get("text", "")[:100]
                        else:
                            preview = str(first_msg.get("content", ""))[:100]
            except Exception:
                preview = "(unreadable)"

            sessions.append({
                "path": path,
                "session_id": f.replace("session-", "").replace(".json", ""),
                "preview": preview,
                "mtime": os.path.getmtime(path),
            })

        sessions.sort(key=lambda s: s["mtime"], reverse=True)
        return sessions

    @classmethod
    def _extract_chat_log(cls, session_path: str) -> str:
        """Convert JSON session messages into a readable Markdown log."""
        try:
            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            output = [f"# Gemini CLI Session Log: {data.get('sessionId', 'Unknown')}\n"]
            output.append(f"Start Time: {data.get('startTime', 'Unknown')}\n")
            output.append("-" * 20 + "\n")

            for msg in data.get("messages", []):
                role = msg.get("type", "unknown").upper()
                content = ""
                
                # Extract text from content list
                if isinstance(msg.get("content"), list):
                    content = "\n".join([c.get("text", "") for c in msg["content"] if isinstance(c, dict)])
                else:
                    content = str(msg.get("content", ""))

                output.append(f"### {role}\n\n{content}\n")
                
                # Include thoughts if available
                if msg.get("thoughts"):
                    output.append("#### Thoughts:\n")
                    for thought in msg["thoughts"]:
                        output.append(f"- **{thought.get('subject')}**: {thought.get('description')}\n")
                
                output.append("\n---\n")

            return "\n".join(output)
        except Exception as e:
            return f"Error extracting session artifacts: {str(e)}"

    @classmethod
    def sync_to_repo(cls, project_dir: str, issue_number: int, session_path: Optional[str] = None) -> List[str]:
        """Syncs Gemini CLI session artifacts into the project dir."""
        if not session_path:
            session_path = cls.get_latest_session(project_dir, issue_number)
            if not session_path:
                return []

        # Find target directory
        feature_dir = AntigravityBrain._find_feature_dir(project_dir, issue_number)
        if not feature_dir:
            features_root = os.path.join(project_dir, "docs", "features")
            feature_dir = os.path.join(features_root, f"{issue_number}_issue-{issue_number}")

        target_dir = os.path.join(feature_dir, "ai_brain")
        os.makedirs(target_dir, exist_ok=True)

        chat_log_content = cls._extract_chat_log(session_path)
        chat_log_filename = "gemini_chat_log.md"
        dst = os.path.join(target_dir, chat_log_filename)
        
        # Simple versioning if needed or just overwrite for chat log?
        # Let's use versioned copy from AntigravityBrain but with content directly
        # Since we need to write the content we just extracted
        
        temp_src = os.path.join(target_dir, ".temp_chat_log.md")
        with open(temp_src, "w", encoding="utf-8") as f:
            f.write(chat_log_content)
            
        final_dst = AntigravityBrain._versioned_copy(temp_src, target_dir, chat_log_filename)
        os.remove(temp_src)
        
        if final_dst:
            return [os.path.relpath(final_dst, project_dir)]
        return []
