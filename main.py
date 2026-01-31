#!/usr/bin/env python3
"""
🤖 Luma AI Architect V2 - Workflow Guardian
============================================
State-based Workflow Orchestrator with GitHub Project Integration
"""

import os
import sys
import json
import argparse

import luma_core.ui as ui
import luma_core.actions as actions
from luma_core.config import PROJECTS

# Ensure luma_core is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    suggest_version_from_git
)
from luma_core.agents.reviewer import reviewer_agent, docs_reviewer_agent


# =============================================================================
# Configuration & Constants
# =============================================================================

BOX_WIDTH = 58
GLOBAL_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".luma_global.json")


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
    """Save global config"""
    try:
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except:
        pass

MENU_ACTIONS = {
    "1": {"label": "📋 List Active Issues",          "valid_phases": "ALL"},
    "2": {"label": "📥 Select Issue (from Kanban)", "valid_phases": [WorkflowPhase.IDLE, WorkflowPhase.CODING]},
    "3": {"label": "🧬 Generate Spec (The What)",   "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "P": {"label": "📐 Generate Plan (The How)",    "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "4": {"label": "🧐 Code Review (Local)",       "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PR_PENDING]},
    "5": {"label": "📝 Update Docs",               "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.IDLE]},
    "6": {"label": "🚀 Create Pull Request",       "valid_phases": [WorkflowPhase.CODING]},
    "7": {"label": "📊 View Kanban Status",        "valid_phases": "ALL"},
    "8": {"label": "🔄 Refresh State",             "valid_phases": "ALL"},
    "9": {"label": "🔀 Switch Project",             "valid_phases": "ALL"},
    "R": {"label": "🧬 Refine Issue (Analyst)",    "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "S": {"label": "📋 Generate SBE Specs (Old)",  "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "D": {"label": "📑 Draft Code Review",         "valid_phases": [WorkflowPhase.CODING]},
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
    if args.project == "1" and stored_project in PROJECTS:
        project_key = stored_project
    else:
        project_key = args.project if args.project in PROJECTS else "1"
    project = PROJECTS[project_key]
    
    # Load state
    state = load_state(project["path"])
    state.project_key = project_key
    
    print("\n🚀 Starting Luma V2 Workflow Guardian...")
    
    while True:
        # Display UI
        ui.display_header(state, project)
        ui.display_menu(state, MENU_ACTIONS)
        
        choice = input("\n👉 Select: ").strip()
        
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
        
        elif choice == "3":
            actions.action_generate_spec(state, project)

        elif choice.upper() == "R":
            actions.action_refine_issue(state, project)

        elif choice == "4":
            actions.action_code_review(state, project)
        
        elif choice == "5":
            actions.action_update_docs(state, project)
        
        elif choice == "6":
            actions.action_create_pr(state, project)
            save_state(state, project["path"])
        
        elif choice == "7":
            actions.action_view_kanban(project)
        
        elif choice == "8":
            state = load_state(project["path"])
            
            # Auto-detect merged PR
            if state.phase == WorkflowPhase.PR_PENDING and state.pr_url:
                from luma_core.github_project import check_pr_merged, sync_kanban_on_action
                print(f"🔍 Checking PR status: {state.pr_url}")
                pr_status = check_pr_merged(state.pr_url)
                
                if pr_status["merged"]:
                    print("✅ PR has been merged!")
                    
                    # Move Kanban to Done
                    if state.active_issue and state.active_issue.project_item_id:
                        sync_kanban_on_action(
                            "pr_merged",
                            state.active_issue.project_id,
                            state.active_issue.project_item_id
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

        elif choice == "9":
            new_key = actions.action_switch_project(state)
            if new_key:
                save_state(state, project["path"])  # Save old state
                project_key = new_key
                project = PROJECTS[project_key]
                state = load_state(project["path"])
                state.project_key = project_key
                # Save last project to global config
                global_config["last_project"] = project_key
                save_global_config(global_config)
        

        
        elif choice.upper() == "P":
            actions.action_generate_plan(state, project)

        elif choice.upper() == "S":
            actions.action_generate_sbe(state, project)
        
        elif choice.upper() == "D":
            actions.action_generate_draft(state, project)
        
        else:
            print("❌ Invalid option")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
