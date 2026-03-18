import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from . import config
from .state_manager import LumaState, load_state


_LOG_FILENAME = ".luma_ai_usage.jsonl"
_SESSION_ID = uuid.uuid4().hex[:8]
_LUMA_VERSION_CACHE: Optional[str] = None
_current_action: Optional[str] = None
_current_context: Optional[Dict[str, Any]] = None
_current_sub_action: Optional[str] = None


def set_action(action: Optional[str]) -> None:
    global _current_action
    _current_action = action


def set_sub_action(sub_action: Optional[str]) -> None:
    """
    Set a more fine-grained label for the current action.

    Example:
        action: "Auto Full Workflow"
        sub_action: "Planning/Spec", "Coding/Multi-Agent", "Create PR"
    """
    global _current_sub_action
    _current_sub_action = sub_action


def clear_action() -> None:
    global _current_action
    _current_action = None
    # Also clear any lingering sub_action when main action ends
    clear_sub_action()


def clear_sub_action() -> None:
    global _current_sub_action
    _current_sub_action = None


def set_context(state: Optional[LumaState] = None, project: Optional[Dict[str, Any]] = None) -> None:
    global _current_context
    if not state and not project:
        _current_context = None
        return
    _current_context = {"state": state, "project": project}


def clear_context() -> None:
    global _current_context
    _current_context = None


def get_log_path() -> str:
    luma_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(luma_root, _LOG_FILENAME)


def _get_luma_version() -> str:
    global _LUMA_VERSION_CACHE
    if _LUMA_VERSION_CACHE is not None:
        return _LUMA_VERSION_CACHE

    version = "unknown"
    try:
        luma_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        version_path = os.path.join(luma_root, "VERSION")
        if os.path.exists(version_path):
            with open(version_path, "r", encoding="utf-8") as f:
                parsed = f.read().strip()
                if parsed:
                    version = parsed
    except Exception:
        pass

    _LUMA_VERSION_CACHE = version
    return _LUMA_VERSION_CACHE


def _load_global_config() -> Dict[str, Any]:
    try:
        if os.path.exists(config.GLOBAL_CONFIG_FILE):
            with open(config.GLOBAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _resolve_project_from_state(state: LumaState) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    project_key = getattr(state, "project_key", None)
    if project_key and project_key in config.PROJECTS:
        return project_key, config.PROJECTS[project_key]
    return project_key, None


def _resolve_project_from_global_config() -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    cfg = _load_global_config()
    cwd = os.getcwd()
    project_key = None

    mapping = cfg.get("last_projects_by_path", {})
    if isinstance(mapping, dict):
        project_key = mapping.get(cwd)

    if not project_key:
        project_key = cfg.get("last_project")

    if project_key and project_key in config.PROJECTS:
        return project_key, config.PROJECTS[project_key]
    return project_key, None


def _build_context() -> Dict[str, Any]:
    state: Optional[LumaState] = None
    project: Optional[Dict[str, Any]] = None
    project_key: Optional[str] = None

    if _current_context:
        state = _current_context.get("state")
        project = _current_context.get("project")
        if state and not project:
            project_key, project = _resolve_project_from_state(state)

    if not project and not state:
        project_key, project = _resolve_project_from_global_config()
        if project and project.get("path"):
            state = load_state(project["path"])
        else:
            state_file = os.path.join(os.getcwd(), ".luma_state.json")
            if os.path.exists(state_file):
                state = load_state(os.getcwd())
                if state and not project:
                    project_key, project = _resolve_project_from_state(state)

    if not project_key and state:
        project_key = getattr(state, "project_key", None)

    ctx: Dict[str, Any] = {}
    if project_key:
        ctx["project_key"] = project_key
    if project:
        ctx["project_name"] = project.get("name")
        ctx["project_path"] = project.get("path")
        ctx["project_repo"] = project.get("repo")
    if state:
        phase = getattr(state, "phase", None)
        if phase:
            ctx["phase"] = phase.value if hasattr(phase, "value") else str(phase)
        if getattr(state, "active_branch", None):
            ctx["active_branch"] = state.active_branch
        issues = []
        for issue in getattr(state, "active_issues", []) or []:
            issues.append(
                {
                    "number": issue.number,
                    "title": issue.title,
                    "url": issue.html_url,
                }
            )
        if issues:
            ctx["issues"] = issues
            ctx["issue_numbers"] = [i["number"] for i in issues]
    return ctx


def record_llm_event(
    *,
    provider: Optional[str],
    model: Optional[str],
    status: str,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
    call_id: Optional[str] = None,
    chain_index: Optional[int] = None,
    chain_length: Optional[int] = None,
    model_type: Optional[str] = None,
    purpose: Optional[str] = None,
) -> None:
    event: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "llm_call",
        "status": status,
        "session_id": _SESSION_ID,
        "luma_version": _get_luma_version(),
    }

    if provider:
        event["provider"] = provider
    if model:
        event["model"] = model
    if model_type:
        event["model_type"] = model_type
    if purpose:
        event["purpose"] = purpose
    if duration_ms is not None:
        event["duration_ms"] = int(round(duration_ms))
    if error:
        event["error"] = str(error)[:500]
    if call_id:
        event["call_id"] = call_id
    if chain_index is not None:
        event["chain_index"] = chain_index
    if chain_length is not None:
        event["chain_length"] = chain_length
    if _current_action:
        event["action"] = _current_action
    if _current_sub_action:
        event["sub_action"] = _current_sub_action

    context = _build_context()
    for key, value in context.items():
        if key not in event and value is not None:
            event[key] = value

    log_path = get_log_path()
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # Best-effort logging only
        pass
