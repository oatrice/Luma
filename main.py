#!/usr/bin/env python3
"""
🤖 Luma AI Architect V2 - Workflow Guardian
============================================
State-based Workflow Orchestrator with GitHub Project Integration
"""

import os
import sys
import json
import time
import argparse
import platform
import subprocess
from contextlib import redirect_stdout
from typing import Optional

# Import first so Python 3.9 importlib metadata compatibility is installed
# before other project modules import third-party dependencies.
from luma_core.importlib_compat import ensure_importlib_metadata_compat

import luma_core.ui as ui
import luma_core.actions as actions
import luma_core.usage_tracker as usage_tracker
from luma_core.config import PROJECTS, detect_project_key_for_path, get_status_workflow, CANONICAL_KANBAN_BY_REPO
from luma_core.doc_updates import pending_doc_update_summary, refresh_pending_doc_updates
from luma_core.notifier import notify_task_complete

from luma_core.state_manager import (
    LumaState, WorkflowPhase,
    load_state, save_state, transition_to
)
from luma_core.tools import (
    get_current_version,
    get_project_git_info,
    repair_invalid_branch,
)


# =============================================================================
# Configuration & Constants
# =============================================================================

GLOBAL_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".luma_global.json")
LUMA_ROOT = os.path.dirname(os.path.abspath(__file__))
CONTRACT_VERSION = "2.0"
SUPPORTED_HEADLESS_ACTIONS = ("code_review", "create_pr", "bootstrap", "create_issue", "auto_workflow")
STARTUP_GIT_INFO = get_project_git_info(LUMA_ROOT)
_PAYLOAD_UNSET = object()


class CLIError(Exception):
    """Base error for CLI contract handling."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class CLIArgumentError(CLIError):
    """Raised when CLI argument validation fails."""


class ProjectSelectorError(CLIArgumentError):
    """Raised when a headless project selector is invalid or cannot be resolved."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        error_details: Optional[dict] = None,
        resolved_target=None,
        exit_code: int = 2,
    ):
        super().__init__(message, exit_code=exit_code)
        self.error_code = error_code
        self.error_details = error_details or {}
        self.resolved_target = resolved_target


class LumaArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises instead of exiting for custom JSON errors."""

    def error(self, message):
        raise CLIArgumentError(message, exit_code=2)


def build_parser() -> argparse.ArgumentParser:
    parser = LumaArgumentParser(description="Luma AI Architect V2")
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Project key (for example 1=JarWise-Root, 12=Luma)",
    )
    parser.add_argument(
        "--issue",
        type=str,
        default=None,
        help="Issue number(s) for bootstrap (comma-separated for multi-select)",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Title for create_issue action",
    )
    parser.add_argument(
        "--body",
        type=str,
        default=None,
        help="Body for create_issue action",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default=None,
        help="Optional branch name for bootstrap",
    )
    parser.add_argument(
        "--auto",
        "--headless",
        action="store_true",
        dest="auto",
        help="Run without the interactive menu",
    )
    parser.add_argument(
        "--action",
        type=str,
        default=None,
        help="Headless action name to execute",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume the workflow from the last checkpoint",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json",
        help="Emit machine-readable JSON to stdout",
    )
    parser.add_argument(
        "--meta",
        action="store_true",
        help="Emit machine-readable metadata for external consumers",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force the current operation",
    )
    parser.add_argument(
        "--caller",
        type=str,
        default=None,
        help="Optional caller identifier for headless telemetry",
    )
    # Create Issue specific args
    parser.add_argument(
        "--issue-title",
        type=str,
        default=None,
        help="Issue title (for create_issue action)",
    )
    parser.add_argument(
        "--issue-body",
        type=str,
        default=None,
        help="Issue body markdown (for create_issue action)",
    )
    parser.add_argument(
        "--issue-labels",
        type=str,
        nargs="+",
        default=[],
        help="Labels to add (for create_issue action)",
    )
    parser.add_argument(
        "--related",
        type=str,
        nargs="+",
        default=[],
        dest="related_links",
        help="Cross-repo links (e.g., oatrice/Zenith#19)",
    )
    return parser


def _extract_flag_value(argv, flag_name: str):
    try:
        index = argv.index(flag_name)
    except ValueError:
        return None

    if index + 1 >= len(argv):
        return None
    return argv[index + 1]


def parse_cli_args(argv=None):
    argv = list(argv or [])
    parser = build_parser()
    args = parser.parse_args(argv)

    headless_requested = (
        args.auto
        or args.action is not None
        or args.json
        or args.meta
        or args.caller is not None
        or args.resume
    )
    if args.meta:
        if not args.json:
            raise CLIArgumentError(
                "--meta requires --json.",
                exit_code=2,
            )
        if args.action is not None or args.auto:
            raise CLIArgumentError(
                "--meta cannot be combined with --action, --auto, or --headless.",
                exit_code=2,
            )
    elif headless_requested and not args.action:
        # Default to auto_workflow if --resume is used without explicit --action
        if args.resume:
            args.action = "auto_workflow"
        else:
            raise CLIArgumentError(
                "--action is required when using headless mode.",
                exit_code=2,
            )

    if args.project is not None:
        parse_project_selector(args.project)

    return args


def is_headless_mode(args) -> bool:
    return bool(args.auto or args.action or args.json or args.meta)


def emit_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def build_success_payload(
    action_name: str,
    requested_project: str,
    result,
    resolved_target=_PAYLOAD_UNSET,
) -> dict:
    payload = {
        "status": "success",
        "action": action_name,
        "project": requested_project,
        "result": result,
    }
    if resolved_target is not _PAYLOAD_UNSET:
        payload["resolved_target"] = resolved_target
    return payload


def build_error_payload(
    action_name: str,
    requested_project: str,
    error_message: str,
    *,
    resolved_target=_PAYLOAD_UNSET,
    error_code: Optional[str] = None,
    error_details: Optional[dict] = None,
) -> dict:
    payload = {
        "status": "error",
        "action": action_name,
        "project": requested_project,
        "error": error_message,
    }
    if resolved_target is not _PAYLOAD_UNSET:
        payload["resolved_target"] = resolved_target
    if error_code is not None:
        payload["error_code"] = error_code
    if error_details is not None:
        payload["error_details"] = error_details
    return payload


def is_git_dirty(repo_path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return False

    return bool(result.stdout.strip())


def build_metadata_result() -> dict:
    git_info = get_project_git_info(LUMA_ROOT)
    version = (
        get_current_version(LUMA_ROOT, "VERSION")
        or get_current_version(LUMA_ROOT)
        or "unknown"
    )

    return {
        "version": version,
        "git_commit": git_info.get("hash") or "unknown",
        "dirty": is_git_dirty(LUMA_ROOT),
        "contract_version": CONTRACT_VERSION,
        "supported_actions": list(SUPPORTED_HEADLESS_ACTIONS),
        "python_version": platform.python_version(),
    }


def build_metadata_payload() -> dict:
    return {
        "status": "success",
        "mode": "metadata",
        "result": build_metadata_result(),
    }

def check_luma_outdated():
    """Check if the current running Luma is outdated compared to the code on disk."""
    current_disk_info = get_project_git_info(LUMA_ROOT)

    if STARTUP_GIT_INFO["hash"] != current_disk_info["hash"]:
        return True, current_disk_info
    return False, None


def _detect_repo_and_kanban(project_path: str) -> tuple[Optional[str], Optional[int], Optional[str]]:
    """
    Detect VCS repo and kanban info from project path.

    Returns:
        Tuple of (detected_repo, kanban_number, kanban_id)
    """
    detected_repo = None
    try:
        res = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_path, capture_output=True, text=True
        )
        if res.returncode == 0:
            remote = res.stdout.strip()
            if "github.com" in remote:
                path_part = remote.split("github.com")[-1].lstrip(":").lstrip("/")
                detected_repo = path_part.replace(".git", "")
            elif "gitlab.com" in remote:
                path_part = remote.split("gitlab.com")[-1].lstrip(":").lstrip("/")
                detected_repo = path_part.replace(".git", "")
    except Exception:
        pass

    # Lookup kanban info from canonical mapping if repo detected
    kanban_info = CANONICAL_KANBAN_BY_REPO.get(detected_repo, {})
    return (
        detected_repo,
        kanban_info.get("kanban_number"),
        kanban_info.get("kanban_id")
    )


def _selector_error(
    message: str,
    *,
    error_code: str,
    selector_type: Optional[str] = None,
    selector_input: Optional[str] = None,
    reason: Optional[str] = None,
    candidates: Optional[list] = None,
    resolved_target=None,
) -> ProjectSelectorError:
    error_details = {}
    if selector_type is not None:
        error_details["selector_type"] = selector_type
    if selector_input is not None:
        error_details["selector_input"] = selector_input
    if reason is not None:
        error_details["reason"] = reason
    if candidates is not None:
        error_details["candidates"] = candidates
    return ProjectSelectorError(
        message,
        error_code=error_code,
        error_details=error_details,
        resolved_target=resolved_target,
    )


def build_menu_title(is_outdated: bool, pending_summary: str = "") -> str:
    """Build the interactive menu title, including restart notice when needed."""
    lines = []
    if is_outdated:
        lines.append("⚠️  LUMA CODE UPDATED ON DISK! Please RESTART Luma to apply changes.")
    if pending_summary:
        lines.append(f"📝 Pending docs/version update: {pending_summary}")
    lines.append("👉 Select an action:")
    return "\n".join(lines)


def load_global_config():
    """Load global config (last project, etc)"""
    if os.path.exists(GLOBAL_CONFIG_FILE):
        try:
            with open(GLOBAL_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_project": "1"}


def save_global_config(config):
    """Save global config, preserving existing keys like LLM_PROVIDER"""
    try:
        current_config = {}
        if os.path.exists(GLOBAL_CONFIG_FILE):
             with open(GLOBAL_CONFIG_FILE, "r") as f:
                  current_config = json.load(f)

        # Merge nested maps so we do not clobber file updates that happened
        # after the caller loaded an older in-memory snapshot.
        for key, value in config.items():
            if isinstance(value, dict) and isinstance(current_config.get(key), dict):
                merged_value = current_config[key].copy()
                merged_value.update(value)
                current_config[key] = merged_value
            else:
                current_config[key] = value
        
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            json.dump(current_config, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save global config: {e}")


def parse_project_selector(raw_selector: Optional[str], projects: dict = None) -> Optional[dict]:
    """Parse a single project selector from CLI input."""
    if raw_selector is None:
        return None

    projects = projects or PROJECTS

    if raw_selector in projects:
        return {
            "selector_type": "key",
            "selector_input": raw_selector,
            "selector_value": raw_selector,
            "legacy": True,
        }

    if raw_selector.isdigit():
        return {
            "selector_type": "key",
            "selector_input": raw_selector,
            "selector_value": raw_selector,
            "legacy": True,
        }

    prefix, separator, raw_value = raw_selector.partition(":")
    if separator and prefix in {"key", "repo", "path", "slug"}:
        if not raw_value:
            raise _selector_error(
                f"Project selector '{raw_selector}' is invalid.",
                error_code="project_selector_invalid",
                selector_type=prefix,
                selector_input=raw_selector,
                reason="Selector value is required.",
                resolved_target=None,
            )

        if prefix == "path":
            if not os.path.isabs(raw_value):
                raise _selector_error(
                    f"Project selector '{raw_selector}' is invalid.",
                    error_code="project_selector_invalid",
                    selector_type="path",
                    selector_input=raw_selector,
                    reason="Path selectors must use absolute paths.",
                    resolved_target=None,
                )
            normalized_path = os.path.abspath(raw_value)
            if not os.path.isdir(normalized_path):
                raise _selector_error(
                    f"Project selector '{raw_selector}' is invalid.",
                    error_code="project_selector_invalid",
                    selector_type="path",
                    selector_input=raw_selector,
                    reason="Path selector must point to an existing directory.",
                    resolved_target=None,
                )
            selector_value = normalized_path
        else:
            selector_value = raw_value

        return {
            "selector_type": prefix,
            "selector_input": raw_selector,
            "selector_value": selector_value,
            "legacy": False,
        }

    if os.path.isdir(raw_selector):
        return {
            "selector_type": "path",
            "selector_input": raw_selector,
            "selector_value": os.path.abspath(raw_selector),
            "legacy": True,
        }

    raise CLIArgumentError(
        f"Unknown project key or invalid path '{raw_selector}'.",
        exit_code=2,
    )


def _serialize_project_candidate(project_key: str, project: dict) -> dict:
    return {
        "project_key": project_key,
        "repo": project.get("repo"),
        "path": project.get("path"),
        "slug": project.get("slug"),
    }


def _build_resolved_target(
    *,
    selector_type: str,
    selector_input: str,
    project_key,
    project: dict,
    resolution_source: str,
) -> dict:
    return {
        "selector_type": selector_type,
        "selector_input": selector_input,
        "project_key": project_key,
        "repo": project.get("repo"),
        "path": project.get("path"),
        "slug": project.get("slug"),
        "resolution_source": resolution_source,
    }


def _build_dynamic_project(project_path: str) -> dict:
    normalized_path = os.path.abspath(project_path)
    detected_repo, kanban_number, kanban_id = _detect_repo_and_kanban(normalized_path)
    return {
        "name": os.path.basename(normalized_path) or "Current Project",
        "path": normalized_path,
        "repo": detected_repo,
        "slug": None,
        "kanban_number": kanban_number,
        "kanban_id": kanban_id,
    }


def _find_exact_project_key_for_path(project_path: str, projects: dict = None):
    projects = projects or PROJECTS
    normalized_path = os.path.realpath(project_path)
    for project_key, project in projects.items():
        configured_path = project.get("path")
        if not configured_path:
            continue
        if os.path.realpath(configured_path) == normalized_path:
            return project_key
    return None


def _resolve_explicit_headless_project_selector(selector: dict, projects: dict = None):
    projects = projects or PROJECTS
    selector_type = selector["selector_type"]
    selector_input = selector["selector_input"]
    selector_value = selector["selector_value"]

    if selector_type == "path":
        exact_key = _find_exact_project_key_for_path(selector_value, projects)
        if exact_key and exact_key in projects:
            project = projects[exact_key]
            return (
                exact_key,
                project,
                _build_resolved_target(
                    selector_type="path",
                    selector_input=selector_input,
                    project_key=exact_key,
                    project=project,
                    resolution_source="local_registry",
                ),
            )

        project = _build_dynamic_project(selector_value)
        return (
            "dynamic",
            project,
            _build_resolved_target(
                selector_type="path",
                selector_input=selector_input,
                project_key=None,
                project=project,
                resolution_source="direct_path",
            ),
        )

    matches = []
    if selector_type == "key":
        if selector_value in projects:
            matches.append((selector_value, projects[selector_value]))
    elif selector_type == "repo":
        matches = [
            (project_key, project)
            for project_key, project in projects.items()
            if project.get("repo") == selector_value
        ]
        if not matches:
            # Fallback: case-insensitive repo name only match
            selector_name = selector_value.split("/")[-1].lower()
            matches = [
                (project_key, project)
                for project_key, project in projects.items()
                if project.get("repo", "").split("/")[-1].lower() == selector_name
            ]
    elif selector_type == "slug":
        matches = [
            (project_key, project)
            for project_key, project in projects.items()
            if project.get("slug") == selector_value
        ]

    matches = sorted(matches, key=lambda item: item[0])

    if not matches:
        raise _selector_error(
            f"Project selector '{selector_input}' did not match any local project.",
            error_code="project_selector_not_found",
            selector_type=selector_type,
            selector_input=selector_input,
            reason="No local project matched the selector.",
            resolved_target=None,
        )

    if len(matches) > 1:
        raise _selector_error(
            f"Project selector '{selector_input}' is ambiguous.",
            error_code="project_selector_ambiguous",
            selector_type=selector_type,
            selector_input=selector_input,
            candidates=[
                _serialize_project_candidate(project_key, project)
                for project_key, project in matches
            ],
            resolved_target=None,
        )

    project_key, project = matches[0]
    return (
        project_key,
        project,
        _build_resolved_target(
            selector_type=selector_type,
            selector_input=selector_input,
            project_key=project_key,
            project=project,
            resolution_source="local_registry",
        ),
    )


def resolve_headless_project_target(
    cli_project_key: str,
    stored_project: str,
    current_cwd: str,
    cli_project_explicit: bool = False,
):
    """Resolve a headless project request to a concrete local target."""
    if cli_project_explicit:
        selector = parse_project_selector(cli_project_key)
        return _resolve_explicit_headless_project_selector(selector)

    if stored_project and stored_project in PROJECTS:
        project = PROJECTS[stored_project]
        return (
            stored_project,
            project,
            _build_resolved_target(
                selector_type="key",
                selector_input=stored_project,
                project_key=stored_project,
                project=project,
                resolution_source="stored_project",
            ),
        )

    inferred_project = detect_project_key_for_path(current_cwd)
    if inferred_project and inferred_project in PROJECTS:
        project = PROJECTS[inferred_project]
        return (
            inferred_project,
            project,
            _build_resolved_target(
                selector_type="path",
                selector_input=os.path.abspath(current_cwd),
                project_key=inferred_project,
                project=project,
                resolution_source="cwd_inference",
            ),
        )

    project = _build_dynamic_project(current_cwd)
    return (
        "dynamic",
        project,
        _build_resolved_target(
            selector_type="path",
            selector_input=os.path.abspath(current_cwd),
            project_key=None,
            project=project,
            resolution_source="direct_path",
        ),
    )


def resolve_project_key(
    cli_project_key: str,
    stored_project: str,
    current_cwd: str,
    cli_project_explicit: bool = False,
) -> str:
    """Resolve project key from CLI arg, saved mapping, cwd inference, then fallback."""
    if cli_project_explicit and cli_project_key in PROJECTS:
        return cli_project_key

    # If it's an explicit path, try to match with known projects first
    if cli_project_key and os.path.isdir(cli_project_key):
        detected_key = detect_project_key_for_path(cli_project_key)
        if detected_key and detected_key in PROJECTS:
            return detected_key
        return "dynamic"

    if cli_project_key and cli_project_key != "1" and cli_project_key in PROJECTS:
        return cli_project_key

    if stored_project and stored_project in PROJECTS:
        return stored_project

    inferred_project = detect_project_key_for_path(current_cwd)
    if inferred_project and inferred_project in PROJECTS:
        return inferred_project

    # NEW: Only return "dynamic" if we are truly in an unknown directory
    # and no project was explicitly requested.
    return "dynamic"


def _get_requested_project_value(args, resolved_project_key: str) -> str:
    return args.project or resolved_project_key


def _resolve_headless_action(args, action_name: str):
    if action_name == "code_review":
        return lambda state, project: actions.action_code_review(
            state,
            project,
            headless=True,
        )
    
    if action_name == "create_pr":
        return lambda state, project: actions.action_create_pr(
            state,
            project,
            auto_approve=True,
            force=args.force
        )
    
    if action_name == "create_issue":
        # Parse headless args for create_issue
        headless_args = {
            "title": getattr(args, "issue_title", ""),
            "body": getattr(args, "issue_body", ""),
            "labels": getattr(args, "issue_labels", []),
            "related_links": getattr(args, "related_links", []),
        }
        return lambda state, project: actions.action_create_issue(
            state,
            project,
            headless=True,
            headless_args=headless_args,
        )

    if action_name == "bootstrap":
        if not args.issue:
            raise CLIArgumentError("--issue <number> is required for bootstrap action.", exit_code=2)
        
        try:
            issue_numbers = [int(i.strip()) for i in args.issue.split(",")]
        except ValueError:
            raise CLIArgumentError("Invalid issue format. Use numbers (e.g. --issue 40 or --issue 40,41).", exit_code=2)
            
        return lambda state, project: actions.bootstrap_issue(
            state,
            project,
            issue_numbers=issue_numbers,
            branch_name=args.branch
        )

    if action_name == "create_issue":
        return lambda state, project: actions.action_create_issue(
            state,
            project,
            title=args.title,
            body=args.body,
            headless=True
        )

    if action_name == "auto_workflow":
        return lambda state, project: actions.action_guided_workflow(
            state,
            project,
            headless=True
        )

    raise CLIError(f"Action '{action_name}' not found.", exit_code=1)


def run_headless(args) -> int:
    if args.meta:
        emit_json(build_metadata_payload())
        return 0

    start_time = time.perf_counter()
    current_cwd = os.getcwd()
    global_config = load_global_config()
    project_map = global_config.get("last_projects_by_path", {})
    stored_project = project_map.get(current_cwd)
    
    action_name = args.action
    requested_project = args.project or stored_project or "1"
    exit_code = 0
    error_message = None
    resolved_target = _PAYLOAD_UNSET

    try:
        project_key, project, resolved_target = resolve_headless_project_target(
            args.project,
            stored_project,
            current_cwd,
            cli_project_explicit=args.project is not None,
        )

        state = load_state(project["path"])
        state.project_key = project_key

        if args.resume:
            print(f"🔄 Resuming workflow for project {requested_project}...")
            # We already loaded the state from disk above.
            # If it's IDLE, then resume might not make sense unless they provided --issue
            if state.phase == WorkflowPhase.IDLE and args.issue:
                 # Auto-bootstrap if resuming from idle with issue
                 pass

        usage_tracker.clear_action()
        usage_tracker.clear_context()
        usage_tracker.set_action(action_name)
        usage_tracker.set_context(state, project)

        with redirect_stdout(sys.stderr):
            print(f"DEBUG: Executing action '{action_name}' with project: {project['name']} at {project['path']}")
            action_runner = _resolve_headless_action(args, action_name)
            result = action_runner(state, project)

        if args.json:
            emit_json(
                build_success_payload(
                    action_name,
                    requested_project,
                    result,
                    resolved_target=resolved_target,
                )
            )
        else:
            print(f"✅ {action_name} completed for project {requested_project}")
        return 0
    except CLIError as exc:
        exit_code = exc.exit_code
        error_message = str(exc)
        if args.json:
            emit_json(
                build_error_payload(
                    args.action,
                    requested_project,
                    error_message,
                    resolved_target=getattr(exc, "resolved_target", resolved_target),
                    error_code=getattr(exc, "error_code", None),
                    error_details=getattr(exc, "error_details", None),
                )
            )
        else:
            print(error_message, file=sys.stderr)
        return exit_code
    except Exception as exc:
        exit_code = 2
        error_message = str(exc)
        if args.json:
            emit_json(
                build_error_payload(
                    args.action,
                    requested_project,
                    error_message,
                    resolved_target=resolved_target,
                )
            )
        else:
            print(error_message, file=sys.stderr)
        return exit_code
    finally:
        usage_tracker.record_action_event(
            mode="headless",
            action=action_name,
            project=requested_project,
            status="success" if exit_code == 0 else "error",
            exit_code=exit_code,
            duration_ms=(time.perf_counter() - start_time) * 1000,
            error=error_message,
            caller=args.caller,
        )
        usage_tracker.clear_action()
        usage_tracker.clear_context()

MENU_ACTIONS = {
    "0": {"label": "❌ Exit",                      "valid_phases": "ALL"},
    "A": {"label": "⚡ Auto Full Workflow",         "valid_phases": "ALL"},
    "K": {"label": "📊 View Kanban Status",        "valid_phases": "ALL"},
    "1": {"label": "📋 List Active Issues",          "valid_phases": "ALL"},
    "N": {"label": "🆕 Create New Issue",           "valid_phases": "ALL"},
    "2": {"label": "📥 Select Issue (from Kanban)", "valid_phases": [WorkflowPhase.IDLE, WorkflowPhase.CODING]},
    "+": {"label": "➕ Add Issue (to session)",     "valid_phases": "ALL"},
    "-": {"label": "➖ Remove Issue (from session)", "valid_phases": "ALL"},
    "3": {"label": "🧬 Refine Issue (Analyst)",    "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "4": {"label": "📝 Generate Spec + SBE",        "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "5": {"label": "📐 Generate Plan (The How)",    "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "6": {"label": "🧐 Code Review (Local)",       "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PR_PENDING, WorkflowPhase.REVIEWING]},
    "7": {"label": "📝 Update Docs",               "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.IDLE, WorkflowPhase.PR_PENDING, WorkflowPhase.REVIEWING]},
    "B": {"label": "🧠 Sync AI Agent Brain",       "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT, WorkflowPhase.REVIEWING]},
    "P": {"label": "🚀 Create/Sync PRs",           "valid_phases": "ALL"},
    "8": {"label": "🚀 Create Pull Request",       "valid_phases": "ALL"},
    "U": {"label": "🗺️  Update Roadmap",           "valid_phases": "ALL"},
    "L": {"label": "📊 View Usage Log",            "valid_phases": "ALL"},
    "D": {"label": "📊 Usage & Metrics Dashboard",  "valid_phases": "ALL"},
    "T": {"label": "🧪 Test Telegram Notification", "valid_phases": "ALL"},
    "M": {"label": "📏 Track Issue Metrics",       "valid_phases": "ALL"},
    "G": {"label": "📊 Generate Project Report",    "valid_phases": "ALL"},
    "Q": {"label": "🐙 Audit & Sync GitHub Metrics", "valid_phases": "ALL"},
    "R": {"label": "🔄 Refresh State",             "valid_phases": "ALL"},
    "S": {"label": "🔀 Switch Project",             "valid_phases": "ALL"},
    "O": {"label": "⚙️ Settings",                  "valid_phases": "ALL"}
}




# =============================================================================
# Display Functions (Moved to luma_core.ui)
# =============================================================================

pass


# =============================================================================
# Menu Actions (Moved to luma_core.actions)
# =============================================================================

pass


def run_with_notify(action_label: str, project_name: str, func, *args, **kwargs):
    """Run an action and send Telegram notification on completion."""
    start = time.time()
    state_arg = next((a for a in args if isinstance(a, LumaState)), None)
    project_arg = next(
        (a for a in args if isinstance(a, dict) and "path" in a and "name" in a),
        None,
    )
    usage_tracker.set_action(action_label)
    usage_tracker.set_context(state_arg, project_arg)
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        notify_task_complete(
            project=project_name,
            task=action_label,
            status="success",
            duration=f"{elapsed:.0f}s",
        )
        return result
    except Exception as e:
        elapsed = time.time() - start
        notify_task_complete(
            project=project_name,
            task=action_label,
            status="failure",
            duration=f"{elapsed:.0f}s",
            message=str(e)[:200],
        )
        raise
    finally:
        # Ensure we always clear both high-level action and any nested sub_action
        usage_tracker.clear_action()
        usage_tracker.clear_context()


# =============================================================================
# Main Loop
# =============================================================================

def run_interactive(args) -> int:
    # Load global config for last project
    global_config = load_global_config()

    current_cwd = os.getcwd()
    # Migration: Support old format
    if "last_project" in global_config and "last_projects_by_path" not in global_config:
        global_config["last_projects_by_path"] = {}
        # We don't know the path for the old single value, so just ignore or set default
    
    project_map = global_config.get("last_projects_by_path", {})
    stored_project = project_map.get(current_cwd)
    
    # Resolve project: check if args.project is a path first
    if args.project and os.path.isdir(args.project):
        project_key = "dynamic"
        project_path = os.path.abspath(args.project)
        detected_repo, kanban_number, kanban_id = _detect_repo_and_kanban(project_path)
        project = {
            "name": os.path.basename(project_path) or "Current Project",
            "path": project_path,
            "repo": detected_repo,
            "kanban_number": kanban_number,
            "kanban_id": kanban_id
        }
    else:
        project_key = resolve_project_key(
            args.project,
            stored_project,
            current_cwd,
            cli_project_explicit=args.project is not None,
        )
        # Handle dynamic project (unknown directory not in PROJECTS)
        if project_key == "dynamic":
            project_path = os.path.abspath(args.project) if args.project else current_cwd
            detected_repo, kanban_number, kanban_id = _detect_repo_and_kanban(project_path)
            project = {
                "name": os.path.basename(project_path) or "Current Project",
                "path": project_path,
                "repo": detected_repo,
                "kanban_number": kanban_number,
                "kanban_id": kanban_id
            }
        else:
            project = PROJECTS[project_key]
    
    # Save initial mapping if not exists
    if current_cwd not in project_map or project_map[current_cwd] != project_key:
        project_map[current_cwd] = project_key
        global_config["last_projects_by_path"] = project_map
        save_global_config(global_config)
    
    # Load state
    state = load_state(project["path"])
    state.project_key = project_key

    # --- CRITICAL BRANCH REPAIR ON STARTUP ---
    print(f"🔄 Debug: Current branch in state is '{state.active_branch}'")
    if repair_invalid_branch(state, project["path"]):
        print("🔄 Debug: Saving repaired state...")
        # CRITICAL: state must be first, path must be second
        save_state(state, project["path"])
    # -----------------------------------------
    
    print("\n🚀 Starting Luma V2 Workflow Guardian...")
    
    while True:
        # --- LUMA SELF-UPDATE CHECK ---
        is_outdated, _disk_info = check_luma_outdated()
        pending_status = refresh_pending_doc_updates(state, project)
        menu_title = build_menu_title(
            is_outdated,
            pending_doc_update_summary(pending_status),
        )
        # ------------------------------

        # Check and print Gemini CLI LLM session metrics from the previous action
        try:
            import luma_core.llm
            if getattr(luma_core.llm, '_session_gemini_cli_time', 0.0) > 0:
                print(f"\n📊 [Session Usage] Gemini CLI Timeout Spent: {luma_core.llm._session_gemini_cli_time:.2f}s | Est. Tokens: {luma_core.llm._session_gemini_cli_tokens}")
                # Reset metrics for next action
                luma_core.llm._session_gemini_cli_time = 0.0
                luma_core.llm._session_gemini_cli_tokens = 0
        except Exception:
            pass

        # Display UI
        ui.display_header(state, project)
        
        # Interactive Menu
        try:
            choice = ui.select_menu_option(state, MENU_ACTIONS, title=menu_title)
            # print(f"Selected: {choice}") # Optional feedback
        except Exception as e:
            # Fallback for environments where simple-term-menu might fail
            print(f"⚠️ Interactive menu unavailable: {e}")
            # ui.display_menu(state, MENU_ACTIONS) # StartLine 111 in ui.py was defined legacy
            choice = ui.safe_input(f"\n{menu_title}\n👉 Select: ")
        
        if choice == "0":
            # Save state before exit
            save_state(state, project["path"])
            print("\n👋 State saved. Goodbye!")
            return 0
        
        elif choice == "1":
            actions.action_list_active_issues(project)

        elif choice.upper() == "N":
            actions.action_create_issue(state, project)

        elif choice == "2":
            if actions.action_select_issue(state, project):
                save_state(state, project["path"])
        
        elif choice == "+":
            if actions.action_add_issue(state, project):
                save_state(state, project["path"])
        
        elif choice == "-":
            if actions.action_remove_issue(state, project):
                save_state(state, project["path"])
        
        elif choice.upper() == "N":
            # Create New Issue with cross-repo link support
            if actions.action_create_issue(state, project, headless=False):
                # No state change needed for creating issue
                pass
        
        elif choice == "3":
            run_with_notify("Refine Issue", project["name"], actions.action_refine_issue, state, project)
            
        elif choice == "4":
            run_with_notify("Generate Spec", project["name"], actions.action_generate_spec, state, project)

        elif choice == "5":
            run_with_notify("Generate Plan", project["name"], actions.action_generate_plan, state, project)

        elif choice == "6":
            run_with_notify("Code Review", project["name"], actions.action_code_review, state, project)
        
        elif choice == "7":
            run_with_notify("Update Docs", project["name"], actions.action_update_docs, state, project)
            save_state(state, project["path"])
            
        elif choice.upper() == "B":
            run_with_notify("Sync AI Brain", project["name"], actions.action_sync_ai_brain, state, project)
            
        elif choice == "P": # Create/Sync PRs
            run_with_notify("Create/Sync PRs", project["name"], actions.action_create_pr, state, project)
            save_state(state, project["path"])
        
        elif choice == "8":
            run_with_notify("Create PR", project["name"], actions.action_create_pr, state, project)
            save_state(state, project["path"])
        
        elif choice.upper() == "U":
            actions.action_update_roadmap(state, project)

        elif choice.upper() == "A":
            run_with_notify("Auto Full Workflow", project["name"], actions.action_guided_workflow, state, project)
            save_state(state, project["path"])

        elif choice.upper() == "K":
            actions.action_view_kanban(project)

        elif choice.upper() == "L":
            actions.action_view_stats_files(state, project)

        elif choice.upper() == "D":
            actions.action_view_dashboard(state, project)

        elif choice.upper() == "T":
            actions.action_test_telegram_notification(state, project)

        elif choice.upper() == "M":
            actions.action_manage_issue_metrics(state, project)

        elif choice.upper() == "G":
            actions.action_generate_project_report(state, project)

        elif choice.upper() == "Q":
            from luma_core.issue_metrics import sync_github_metrics_for_project
            from luma_core.actions.utils import prompt_missing_post_story_points
            print(f"\n🐙 Audit & Sync GitHub Metrics - {project['name']}")
            result = sync_github_metrics_for_project(
                project["path"],
                project.get("name"),
                project.get("repo"),
            )
            if result['updated'] > 0:
                print(f"   ✅ Synced {result['updated']} issue records from GitHub.")
            else:
                print("   ✅ GitHub metrics are already up-to-date.")

            if result.get("errors", 0) > 0:
                print(f"   ⚠️  Encountered {result['errors']} errors during sync.")
            if result.get("paradoxes_fixed", 0) > 0:
                print(f"   ⏱️  Fixed {result['paradoxes_fixed']} Time Paradox(es).")
            
            # Suggest and prompt for post story points for newly completed issues
            prompt_missing_post_story_points(project)
        
        elif choice.upper() == "R":
            print("🔄 Refreshing state...")
            state = load_state(project["path"])
            changes_detected = False
            
            # --- AUTO-FIX STUCK STATE ---
            if state.phase == WorkflowPhase.PREFLIGHT and not state.pr_url:
                print("⚠️ State was stuck in Pre-flight (interrupted?). Reverting to CODING.")
                transition_to(state, WorkflowPhase.CODING)
                save_state(state, project["path"])
                changes_detected = True
            # ----------------------------
            
            # --- AUTO-DETECT PR OUTSIDE LUMA ---
            if state.phase in [WorkflowPhase.CODING, WorkflowPhase.REVIEWING, WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING] and state.active_branch:
                try:
                    from luma_core.platform_detector import get_open_pr_unified, detect_repo_platform
                    
                    # Only auto-detect if we don't already have a PR URL
                    # This prevents overriding existing merged PR URLs
                    if not state.pr_url:
                        repo_name = project.get("repo", "")
                        detect_repo_platform(repo_name)
                        
                        # Try to find existing PR/MR for the current branch
                        existing_pr = get_open_pr_unified(repo_name, state.active_branch)
                        
                        if existing_pr and existing_pr.get("url"):
                            pr_url = existing_pr["url"]
                            print(f"📡 Detected PR/MR outside Luma: {pr_url}")
                            if state.phase != WorkflowPhase.PR_PENDING:
                                state.phase = WorkflowPhase.PR_PENDING
                            state.pr_url = pr_url
                            save_state(state, project["path"])
                            changes_detected = True
                except Exception:
                    # If auto-detection fails, continue silently
                    pass
            # -----------------------------------
            
            # Auto-detect merged PR
            if state.phase in [WorkflowPhase.REVIEWING, WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING] and state.pr_url:
                from luma_core.github_project import sync_kanban_on_action
                from luma_core.platform_detector import check_pr_status_unified
                print(f"🔍 Checking PR status: {state.pr_url}")
                # Self-healing enabled by default for VCS migration scenarios
                pr_status = check_pr_status_unified(state.pr_url)
                
                if pr_status["merged"]:
                    print("✅ PR has been merged!")
                    
                    # Move Kanban to Done
                    if state.active_issues:
                        for ai_issue in state.active_issues:
                            if ai_issue.project_id and ai_issue.project_item_id:
                                sync_kanban_on_action(
                                    "pr_merged",
                                    ai_issue.project_id,
                                    ai_issue.project_item_id,
                                    get_status_workflow(project).get("action_status_map"),
                                )
                    
                    # Reset state to IDLE
                    state = LumaState(project_key=state.project_key)
                    save_state(state, project["path"])
                    print("🎉 State reset to IDLE. Ready for next task!")
                    changes_detected = True
                elif pr_status["error"]:
                    print(f"⚠️ Could not check PR: {pr_status['error']}")
                else:
                    print(f"📋 PR status: {pr_status['state']} (not merged yet)")
            
            if not changes_detected:
                print("🔄 State refreshed (no changes detected)")
            else:
                print("✨ State refreshed and updated")

        elif choice.upper() == "S":
            new_key = actions.action_switch_project(state)
            if new_key:
                save_state(state, project["path"])  # Save old state
                project_key = new_key
                project = PROJECTS[project_key]
                state = load_state(project["path"])
                state.project_key = project_key
                
                # Update map based on current CWD
                if "last_projects_by_path" not in global_config:
                    global_config["last_projects_by_path"] = {}
                
                global_config["last_projects_by_path"][current_cwd] = project_key
                save_global_config(global_config)
        
        elif choice.upper() == "O":
            actions.action_settings()
            
        else:
            print("❌ Invalid option")
        
        ui.safe_input("\nPress Enter to continue...")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    try:
        args = parse_cli_args(argv)
    except CLIArgumentError as exc:
        if "--json" in argv:
            emit_json(
                build_error_payload(
                    _extract_flag_value(argv, "--action"),
                    _extract_flag_value(argv, "--project") or "1",
                    str(exc),
                    resolved_target=getattr(exc, "resolved_target", _PAYLOAD_UNSET),
                    error_code=getattr(exc, "error_code", None),
                    error_details=getattr(exc, "error_details", None),
                )
            )
        else:
            parser = build_parser()
            parser.print_usage(sys.stderr)
            print(str(exc), file=sys.stderr)
        return exc.exit_code

    if is_headless_mode(args):
        return run_headless(args)

    return run_interactive(args)


if __name__ == "__main__":
    raise SystemExit(main())
