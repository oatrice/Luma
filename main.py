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
from contextlib import redirect_stdout

try:
    import importlib.metadata as importlib_metadata
except ImportError:  # pragma: no cover
    import importlib_metadata  # type: ignore[no-redef]


def ensure_importlib_metadata_compat(metadata_module=None):
    """Backfill Python 3.9's missing packages_distributions helper."""
    metadata_module = metadata_module or importlib_metadata
    if hasattr(metadata_module, "packages_distributions"):
        return False

    def packages_distributions():
        module_to_distributions = {}
        try:
            for distribution in metadata_module.distributions():
                try:
                    distribution_name = distribution.metadata.get("Name")
                except Exception:
                    distribution_name = None

                if not distribution_name:
                    continue

                for file_entry in getattr(distribution, "files", ()) or ():
                    parts = getattr(file_entry, "parts", None)
                    if not parts:
                        continue
                    module_to_distributions.setdefault(parts[0], []).append(
                        distribution_name
                    )
        except Exception:
            return {}

        return module_to_distributions

    metadata_module.packages_distributions = packages_distributions
    return True


ensure_importlib_metadata_compat()

# Ensure luma_core is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import luma_core.ui as ui
import luma_core.actions as actions
import luma_core.usage_tracker as usage_tracker
from luma_core.config import PROJECTS, detect_project_key_for_path, get_status_workflow
from luma_core.doc_updates import pending_doc_update_summary, refresh_pending_doc_updates
from luma_core.notifier import notify_task_complete

from luma_core.state_manager import (
    LumaState, WorkflowPhase,
    load_state, save_state, transition_to
)
from luma_core.tools import (
    get_project_git_info
)


# =============================================================================
# Configuration & Constants
# =============================================================================

GLOBAL_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".luma_global.json")
LUMA_ROOT = os.path.dirname(os.path.abspath(__file__))
STARTUP_GIT_INFO = get_project_git_info(LUMA_ROOT)


class CLIError(Exception):
    """Base error for CLI contract handling."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class CLIArgumentError(CLIError):
    """Raised when CLI argument validation fails."""


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
        "--auto",
        action="store_true",
        help="Run without the interactive menu",
    )
    parser.add_argument(
        "--action",
        type=str,
        default=None,
        help="Headless action name to execute",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json",
        help="Emit machine-readable JSON to stdout",
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

    headless_requested = args.auto or args.action is not None or args.json
    if headless_requested and not args.action:
        raise CLIArgumentError(
            "--action is required when using headless mode.",
            exit_code=2,
        )

    if args.project is not None and args.project not in PROJECTS:
        raise CLIArgumentError(
            f"Unknown project key '{args.project}'.",
            exit_code=2,
        )

    return args


def is_headless_mode(args) -> bool:
    return bool(args.auto or args.action or args.json)


def emit_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def build_success_payload(action_name: str, requested_project: str, result: dict) -> dict:
    return {
        "status": "success",
        "action": action_name,
        "project": requested_project,
        "result": result,
    }


def build_error_payload(action_name: str, requested_project: str, error_message: str) -> dict:
    return {
        "status": "error",
        "action": action_name,
        "project": requested_project,
        "error": error_message,
    }

def check_luma_outdated():
    """Check if the current running Luma is outdated compared to the code on disk."""
    current_disk_info = get_project_git_info(LUMA_ROOT)
    
    if STARTUP_GIT_INFO["hash"] != current_disk_info["hash"]:
        return True, current_disk_info
    return False, None


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


def resolve_project_key(cli_project_key: str, stored_project: str, current_cwd: str) -> str:
    """Resolve project key from CLI arg, saved mapping, cwd inference, then fallback."""
    if cli_project_key and cli_project_key in PROJECTS:
        return cli_project_key

    if stored_project and stored_project in PROJECTS:
        return stored_project

    inferred_project = detect_project_key_for_path(current_cwd)
    if inferred_project and inferred_project in PROJECTS:
        return inferred_project

    return "1"


def _get_requested_project_value(args, resolved_project_key: str) -> str:
    return args.project or resolved_project_key


def _resolve_headless_action(action_name: str):
    if action_name == "code_review":
        return lambda state, project: actions.action_code_review(
            state,
            project,
            headless=True,
        )

    raise CLIError(f"Action '{action_name}' not found.", exit_code=1)


def run_headless(args) -> int:
    current_cwd = os.getcwd()
    global_config = load_global_config()
    project_map = global_config.get("last_projects_by_path", {})
    stored_project = project_map.get(current_cwd)

    try:
        project_key = resolve_project_key(args.project, stored_project, current_cwd)
        requested_project = _get_requested_project_value(args, project_key)
        action_name = args.action

        with redirect_stdout(sys.stderr):
            project = PROJECTS[project_key]
            state = load_state(project["path"])
            state.project_key = project_key
            action_runner = _resolve_headless_action(action_name)
            result = action_runner(state, project)

        if args.json:
            emit_json(build_success_payload(action_name, requested_project, result))
        else:
            print(f"✅ {action_name} completed for project {requested_project}")
        return 0
    except CLIError as exc:
        requested_project = _get_requested_project_value(
            args,
            args.project or "1",
        )
        if args.json:
            emit_json(build_error_payload(args.action, requested_project, str(exc)))
        else:
            print(str(exc), file=sys.stderr)
        return exc.exit_code
    except Exception as exc:
        requested_project = _get_requested_project_value(
            args,
            args.project or "1",
        )
        if args.json:
            emit_json(build_error_payload(args.action, requested_project, str(exc)))
        else:
            print(str(exc), file=sys.stderr)
        return 2

MENU_ACTIONS = {
    "1": {"label": "📋 List Active Issues",          "valid_phases": "ALL"},
    "2": {"label": "📥 Select Issue (from Kanban)", "valid_phases": [WorkflowPhase.IDLE, WorkflowPhase.CODING]},
    "+": {"label": "➕ Add Issue (to session)",     "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]},
    "-": {"label": "➖ Remove Issue (from session)", "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]},
    "3": {"label": "🧬 Refine Issue (Analyst)",    "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "4": {"label": "📝 Generate Spec + SBE",        "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "5": {"label": "📐 Generate Plan (The How)",    "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "6": {"label": "🧐 Code Review (Local)",       "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PR_PENDING, WorkflowPhase.REVIEWING]},
    "7": {"label": "📝 Update Docs",               "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.IDLE, WorkflowPhase.PR_PENDING, WorkflowPhase.REVIEWING]},
    "B": {"label": "🧠 Sync AI Agent Brain",       "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT, WorkflowPhase.REVIEWING]},
    "P": {"label": "🚀 Create/Sync PRs",           "valid_phases": "ALL"},
    "8": {"label": "🚀 Create Pull Request",       "valid_phases": [WorkflowPhase.CODING]},
    "U": {"label": "🗺️  Update Roadmap",           "valid_phases": "ALL"},
    "A": {"label": "⚡ Auto Full Workflow",         "valid_phases": "ALL"},
    "K": {"label": "📊 View Kanban Status",        "valid_phases": "ALL"},
    "L": {"label": "📊 View Usage Log",            "valid_phases": "ALL"},
    "D": {"label": "📊 Usage & Metrics Dashboard",  "valid_phases": "ALL"},
    "T": {"label": "🧪 Test Telegram Notification", "valid_phases": "ALL"},
    "M": {"label": "📏 Track Issue Metrics",       "valid_phases": "ALL"},
    "G": {"label": "📊 Generate Project Report",    "valid_phases": "ALL"},
    "Q": {"label": "🐙 Audit & Sync GitHub Metrics", "valid_phases": "ALL"},
    "R": {"label": "🔄 Refresh State",             "valid_phases": "ALL"},
    "S": {"label": "🔀 Switch Project",             "valid_phases": "ALL"},
    "O": {"label": "⚙️ Settings",                  "valid_phases": "ALL"},
    "0": {"label": "❌ Exit",                      "valid_phases": "ALL"}
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
    
    project_key = resolve_project_key(args.project, stored_project, current_cwd)

    project = PROJECTS[project_key]
    
    # Save initial mapping if not exists
    if current_cwd not in project_map or project_map[current_cwd] != project_key:
        project_map[current_cwd] = project_key
        global_config["last_projects_by_path"] = project_map
        save_global_config(global_config)
    
    # Load state
    state = load_state(project["path"])
    state.project_key = project_key
    
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

        elif choice == "2":
            if actions.action_select_issue(state, project):
                save_state(state, project["path"])
        
        elif choice == "+":
            if actions.action_add_issue(state, project):
                save_state(state, project["path"])
        
        elif choice == "-":
            if actions.action_remove_issue(state, project):
                save_state(state, project["path"])
        
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
                import subprocess
                try:
                    res = subprocess.run(
                        ["gh", "pr", "list", "--head", state.active_branch, "--state", "all", "--limit", "1", "--json", "url,state"],
                        cwd=project["path"], capture_output=True, text=True
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        import json
                        prs = json.loads(res.stdout)
                        if prs and len(prs) > 0:
                            pr_info = prs[0]
                            pr_state = pr_info.get("state")
                            pr_url = pr_info.get("url")
                            
                            if pr_state in ["OPEN", "MERGED"] and state.phase != WorkflowPhase.PR_PENDING:
                                print(f"📡 Detected PR '{pr_state}' outside Luma: {pr_url}")
                                state.phase = WorkflowPhase.PR_PENDING
                                state.pr_url = pr_url
                                save_state(state, project["path"])
                                changes_detected = True
                            elif pr_state in ["OPEN", "MERGED"] and state.phase == WorkflowPhase.PR_PENDING and not state.pr_url:
                                state.pr_url = pr_url
                                save_state(state, project["path"])
                                changes_detected = True
                except Exception:
                    pass
            # -----------------------------------
            
            # Auto-detect merged PR
            if state.phase in [WorkflowPhase.REVIEWING, WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING] and state.pr_url:
                from luma_core.github_project import check_pr_merged, sync_kanban_on_action
                print(f"🔍 Checking PR status: {state.pr_url}")
                pr_status = check_pr_merged(state.pr_url)
                
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
