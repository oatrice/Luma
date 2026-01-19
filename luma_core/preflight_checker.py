import os
import json
import re
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import Enum

@dataclass
class PreflightCheckResult:
    check_id: str
    name: str
    passed: bool
    message: str
    details: Optional[str] = None

class CheckType(Enum):
    FILE_MODIFIED = "file_modified"
    FILE_EXISTS = "file_exists"
    VERSION_UPDATED = "version_updated"
    COMMAND = "command"

class PreflightChecker:
    def __init__(self, project_path: str, rules_file: str = ".luma_rules.json"):
        self.project_path = project_path
        self.rules_path = os.path.join(project_path, rules_file)
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.rules_path):
            return []
        
        try:
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("preflight_checks", [])
        except Exception as e:
            print(f"Error loading rules: {e}")
            return []

    def check_file_exists(self, path: str) -> bool:
        full_path = os.path.join(self.project_path, path)
        # Handle glob patterns if needed, but for now simple path
        # If path contains *, simplistic glob check could be added
        if "*" in path:
            import glob
            return len(glob.glob(full_path)) > 0
        return os.path.exists(full_path)

    def check_file_modified(self, path: str) -> bool:
        """Check if file has modifications in git (staged or unstaged)"""
        try:
            # Check for unstaged changes
            cmd = ["git", "diff", "--name-only", path]
            result = subprocess.run(cmd, cwd=self.project_path, capture_output=True, text=True)
            if result.stdout.strip():
                return True
                
            # Check for staged changes
            cmd_staged = ["git", "diff", "--cached", "--name-only", path]
            result_staged = subprocess.run(cmd_staged, cwd=self.project_path, capture_output=True, text=True)
            if result_staged.stdout.strip():
                return True
                
            return False
        except Exception as e:
            print(f"Git check failed: {e}")
            return False

    def check_version_updated(self, path: str) -> bool:
        """Check if version has been bumped in the file"""
        try:
            # Check diff for "version" string modification
            cmd = ["git", "diff", path]
            result = subprocess.run(cmd, cwd=self.project_path, capture_output=True, text=True)
            
            # Also check staged
            cmd_staged = ["git", "diff", "--cached", path]
            result_staged = subprocess.run(cmd_staged, cwd=self.project_path, capture_output=True, text=True)
            
            combined_diff = (result.stdout + "\n" + result_staged.stdout)
            
            # Robust regex to match version keys:
            # Matches lines starting with + 
            # Followed by optional whitespace
            # Followed by optional quotes
            # Followed by version, versionName, versionCode, or VERSION
            # Followed by optional quotes
            # Followed by optional whitespace
            # Followed by : or =
            version_pattern = re.compile(r'^\+\s*["\']?(version(?:Name|Code)?|VERSION)["\']?\s*[:=]', re.IGNORECASE)

            for line in combined_diff.splitlines():
                if version_pattern.match(line):
                    return True
            
            return False
        except Exception:
            return False

    def check_command(self, command: str) -> bool:
        try:
            # careful with shell=True, but needed for complex commands
            result = subprocess.run(command, cwd=self.project_path, shell=True, capture_output=True)
            return result.returncode == 0
        except Exception:
            return False

    def run_single_check(self, rule: Dict[str, Any]) -> PreflightCheckResult:
        check_type = rule.get("type")
        check_id = rule.get("id", "unknown")
        name = rule.get("name", check_id)
        path = rule.get("path", "")
        required = rule.get("required", False)
        message = rule.get("message", "Check failed")
        
        passed = False
        
        if check_type == "file_exists":
            passed = self.check_file_exists(path)
        elif check_type == "file_modified":
            passed = self.check_file_modified(path)
        elif check_type == "command":
            passed = self.check_command(rule.get("command", ""))
        elif check_type == "version_updated":
            passed = self.check_version_updated(path)
        else:
            # Unknown check type
            passed = True # Pass by default or Fail? Warning?
            message = f"Unknown check type: {check_type}"

        if passed:
            message = "OK"

        return PreflightCheckResult(
            check_id=check_id,
            name=name,
            passed=passed,
            message=message
        )

    def run_checks(self) -> List[PreflightCheckResult]:
        results = []
        for rule in self.rules:
            results.append(self.run_single_check(rule))
        return results
