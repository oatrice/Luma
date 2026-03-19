import os
import re
import subprocess
from typing import Any, Dict, List, Optional

from luma_core.state_manager import LumaState

PENDING_DOC_UPDATES_KEY = "pending_doc_updates"

_DOC_FILES = ("CHANGELOG.md", "README.md")
_DOC_EXTENSIONS = (".md", ".rst", ".txt")
_IGNORED_PREFIXES = ("docs/", "tests/", "test/", ".github/", ".agent/", "schemas/")
_IGNORED_FILENAMES = {"LICENSE", ".gitignore", ".gitattributes"}
_VERSION_FILE_CANDIDATES = (
    "VERSION",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "app/build.gradle.kts",
    "app/build.gradle",
    "build.gradle.kts",
    "build.gradle",
)
_VERSION_KEY_PATTERN = re.compile(
    r'^\+\s*["\']?(version(?:Name|Code)?|VERSION)["\']?\s*[:=]',
    re.IGNORECASE,
)
_VERSION_FILE_LINE_PATTERN = re.compile(r"^\+\s*v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9._-]+)?\s*$")


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _run_git_command(repo_path: str, cmd: List[str]) -> str:
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _git_ref_exists(repo_path: str, ref: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_changed_files(repo_path: str) -> List[str]:
    files = set()

    if _git_ref_exists(repo_path, "origin/main"):
        committed = _run_git_command(
            repo_path,
            ["git", "diff", "--name-only", "--relative", "origin/main...HEAD"],
        )
        files.update(_normalize_path(line) for line in committed.splitlines() if line.strip())

    dirty = _run_git_command(
        repo_path,
        ["git", "diff", "--name-only", "--relative", "HEAD"],
    )
    files.update(_normalize_path(line) for line in dirty.splitlines() if line.strip())

    staged = _run_git_command(
        repo_path,
        ["git", "diff", "--cached", "--name-only", "--relative"],
    )
    files.update(_normalize_path(line) for line in staged.splitlines() if line.strip())

    untracked = _run_git_command(
        repo_path,
        ["git", "ls-files", "--others", "--exclude-standard"],
    )
    files.update(_normalize_path(line) for line in untracked.splitlines() if line.strip())

    return sorted(files)


def _detect_version_file(project: dict) -> Optional[str]:
    repo_path = project["path"]
    candidates = []
    explicit_version_file = project.get("version_file")
    if explicit_version_file:
        candidates.append(explicit_version_file)
    candidates.extend(_VERSION_FILE_CANDIDATES)

    seen = set()
    for candidate in candidates:
        normalized = _normalize_path(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)

        if os.path.exists(os.path.join(repo_path, normalized)):
            return normalized

    return None


def _is_meaningful_code_change(path: str, version_file: Optional[str]) -> bool:
    normalized = _normalize_path(path)
    basename = os.path.basename(normalized)

    if normalized in _DOC_FILES:
        return False
    if version_file and normalized == version_file:
        return False
    if basename in _IGNORED_FILENAMES:
        return False
    if normalized.startswith(_IGNORED_PREFIXES):
        return False
    if "/tests/" in f"/{normalized}" or "/test/" in f"/{normalized}":
        return False
    if basename.startswith("test_") or basename.endswith(("_test.py", ".spec.ts", ".test.ts", ".spec.js", ".test.js")):
        return False
    if os.path.splitext(basename)[1].lower() in _DOC_EXTENSIONS:
        return False

    return True


def _is_version_file_updated(repo_path: str, version_file: str) -> bool:
    diffs = []

    if _git_ref_exists(repo_path, "origin/main"):
        diffs.append(
            _run_git_command(repo_path, ["git", "diff", "origin/main...HEAD", "--", version_file])
        )

    diffs.append(_run_git_command(repo_path, ["git", "diff", "--", version_file]))
    diffs.append(_run_git_command(repo_path, ["git", "diff", "--cached", "--", version_file]))

    for line in "\n".join(diff for diff in diffs if diff).splitlines():
        if _VERSION_KEY_PATTERN.match(line):
            return True
        if os.path.basename(version_file).upper() == "VERSION" and _VERSION_FILE_LINE_PATTERN.match(line):
            return True

    return False


def detect_pending_doc_updates(project: dict) -> Dict[str, Any]:
    repo_path = project["path"]
    changed_files = _get_changed_files(repo_path)
    version_file = _detect_version_file(project)
    meaningful_files = [
        path for path in changed_files if _is_meaningful_code_change(path, version_file)
    ]

    pending = []
    if meaningful_files:
        for doc_file in _DOC_FILES:
            if os.path.exists(os.path.join(repo_path, doc_file)) and doc_file not in changed_files:
                pending.append(doc_file)

        if version_file and not _is_version_file_updated(repo_path, version_file):
            pending.append(version_file)

    return {
        "pending": pending,
        "changed_files": changed_files,
        "meaningful_files": meaningful_files,
        "version_file": version_file,
        "has_meaningful_changes": bool(meaningful_files),
    }


def refresh_pending_doc_updates(state: LumaState, project: dict) -> Dict[str, Any]:
    status = detect_pending_doc_updates(project)
    state.context[PENDING_DOC_UPDATES_KEY] = status
    return status


def get_pending_doc_updates(state: LumaState) -> Dict[str, Any]:
    return state.context.get(PENDING_DOC_UPDATES_KEY, {})


def has_pending_doc_updates(state: LumaState) -> bool:
    return bool(get_pending_doc_updates(state).get("pending"))


def pending_doc_update_summary(status: Dict[str, Any], max_items: int = 3) -> str:
    pending = status.get("pending", [])
    if not pending:
        return ""

    summary = ", ".join(pending[:max_items])
    remaining = len(pending) - max_items
    if remaining > 0:
        summary += f" +{remaining}"
    return summary
