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

# Ensure luma_core is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import luma_core.ui as ui
import luma_core.actions as actions
import luma_core.usage_tracker as usage_tracker
from luma_core.config import PROJECTS
from luma_core.notifier import notify_task_complete

from luma_core.state_manager import (
    LumaState, IssueData, WorkflowPhase,
    load_state, save_state, transition_to,
    format_state_header, get_next_step_recommendation,
    get_phase_display
)
from luma_core.context_summarizer import ContextSummarizer
from luma_core.github_project import (
    fetch_kanban_cards, get_ready_issues, get_current_in_progress,
    display_kanban_cards, get_project_config, sync_kanban_on_action,
    KanbanCard
)
from luma_core.workflow import build_graph
from luma_core.tools import (
    get_git_changed_files,
    update_multi_repo_docs,
    update_android_version_logic,
    suggest_version_from_git,
    get_project_git_info
)
from luma_core.agents.reviewer import reviewer_agent, docs_reviewer_agent


# =============================================================================
# Configuration & Constants
# =============================================================================

GLOBAL_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".luma_global.json")
LUMA_ROOT = os.path.dirname(os.path.abspath(__file__))
STARTUP_GIT_INFO = get_project_git_info(LUMA_ROOT)

def check_luma_outdated():
    """Check if the current running Luma is outdated compared to the code on disk."""
    current_disk_info = get_project_git_info(LUMA_ROOT)
    
    if STARTUP_GIT_INFO["hash"] != current_disk_info["hash"]:
        return True, current_disk_info
    return False, None


def build_menu_title(is_outdated: bool) -> str:
    """Build the interactive menu title, including restart notice when needed."""
    if is_outdated:
        return (
            "⚠️  LUMA CODE UPDATED ON DISK! Please RESTART Luma to apply changes.\n"
            "👉 Select an action:"
        )
    return "👉 Select an action:"


def load_global_config():
    """Load global config (last project, etc)"""
    if os.path.exists(GLOBAL_CONFIG_FILE):
        try:
            with open(GLOBAL_CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"last_project": "1"}


def save_global_config(config):
    """Save global config, preserving existing keys like LLM_PROVIDER"""
    try:
        current_config = {}
        if os.path.exists(GLOBAL_CONFIG_FILE):
             with open(GLOBAL_CONFIG_FILE, "r") as f:
                  current_config = json.load(f)
        
        # Merge new config into current
        current_config.update(config)
        
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            json.dump(current_config, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save global config: {e}")

MENU_ACTIONS = {
    "1": {"label": "📋 List Active Issues",          "valid_phases": "ALL"},
    "2": {"label": "📥 Select Issue (from Kanban)", "valid_phases": [WorkflowPhase.IDLE, WorkflowPhase.CODING]},
    "+": {"label": "➕ Add Issue (to session)",     "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]},
    "-": {"label": "➖ Remove Issue (from session)", "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]},
    "3": {"label": "🧬 Refine Issue (Analyst)",    "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "4": {"label": "📝 Generate Spec + SBE",        "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "5": {"label": "📐 Generate Plan (The How)",    "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "6": {"label": "🧐 Code Review (Local)",       "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PR_PENDING]},
    "7": {"label": "📝 Update Docs",               "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.IDLE, WorkflowPhase.PR_PENDING]},
    "B": {"label": "🧠 Sync AI Agent Brain",       "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]},
    "P": {"label": "🚀 Create/Sync PRs",           "valid_phases": "ALL"},
    "8": {"label": "🚀 Create Pull Request",       "valid_phases": [WorkflowPhase.CODING]},
    "U": {"label": "🗺️  Update Roadmap",           "valid_phases": "ALL"},
    "A": {"label": "⚡ Auto Full Workflow",         "valid_phases": "ALL"},
    "K": {"label": "📊 View Kanban Status",        "valid_phases": "ALL"},
    "L": {"label": "📊 View Usage Log",            "valid_phases": "ALL"},
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

def main():
    parser = argparse.ArgumentParser(description="Luma AI Architect V2")
    parser.add_argument("--project", type=str, default="1", help="Project key (1=JarWise, 2=Tetris)")
    args = parser.parse_args()
    
    # Load global config for last project
    global_config = load_global_config()
    stored_project = global_config.get("last_project", "1")
    
    # Initialize - use stored project if no CLI arg provided
    
    current_cwd = os.getcwd()
    # Migration: Support old format
    if "last_project" in global_config and "last_projects_by_path" not in global_config:
        global_config["last_projects_by_path"] = {}
        # We don't know the path for the old single value, so just ignore or set default
    
    project_map = global_config.get("last_projects_by_path", {})
    stored_project = project_map.get(current_cwd)
    
    # Priority: CLI Arg > CWD Map > Default "1"
    if args.project != "1":
        project_key = args.project
    elif stored_project and stored_project in PROJECTS:
        project_key = stored_project
    else:
        project_key = "1"
        
    # Validation
    if project_key not in PROJECTS:
        project_key = "1"

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
        menu_title = build_menu_title(is_outdated)
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
            choice = input(f"\n{menu_title}\n👉 Select: ").strip()
        
        if choice == "0":
            # Save state before exit
            save_state(state, project["path"])
            print("\n👋 State saved. Goodbye!")
            break
        
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
        
        elif choice.upper() == "R":
            state = load_state(project["path"])
            
            # --- AUTO-FIX STUCK STATE ---
            if state.phase == WorkflowPhase.PREFLIGHT and not state.pr_url:
                print("⚠️ State was stuck in Pre-flight (interrupted?). Reverting to CODING.")
                transition_to(state, WorkflowPhase.CODING)
                save_state(state, project["path"])
            # ----------------------------
            
            # --- AUTO-DETECT PR OUTSIDE LUMA ---
            if state.phase in [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING] and state.active_branch:
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
                                print(f"🔄 Detected PR '{pr_state}' outside Luma: {pr_url}")
                                state.phase = WorkflowPhase.PR_PENDING
                                state.pr_url = pr_url
                                save_state(state, project["path"])
                            elif pr_state in ["OPEN", "MERGED"] and state.phase == WorkflowPhase.PR_PENDING and not state.pr_url:
                                state.pr_url = pr_url
                                save_state(state, project["path"])
                except Exception as e:
                    pass
            # -----------------------------------
            
            # Auto-detect merged PR
            if state.phase == WorkflowPhase.PR_PENDING and state.pr_url:
                from luma_core.github_project import check_pr_merged, sync_kanban_on_action
                print(f"🔍 Checking PR status: {state.pr_url}")
                pr_status = check_pr_merged(state.pr_url)
                
                if pr_status["merged"]:
                    print("✅ PR has been merged!")
                    
                    # Move Kanban to Done
                    if state.active_issues:
                        for ai_issue in state.active_issues:
                            if ai_issue.project_item_id:
                                sync_kanban_on_action(
                                    "pr_merged",
                                    ai_issue.project_id,
                                    ai_issue.project_item_id
                                )
                    
                    # Reset state to IDLE
                    state = LumaState(project_key=state.project_key)
                    save_state(state, project["path"])
                    print("🎉 State reset to IDLE. Ready for next task!")
                elif pr_status["error"]:
                    print(f"⚠️ Could not check PR: {pr_status['error']}")
                    print("🔄 State refreshed")
                else:
                    print(f"📋 PR status: {pr_status['state']} (not merged yet)")
                    print("🔄 State refreshed")
            else:
                print("🔄 State refreshed")

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
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
