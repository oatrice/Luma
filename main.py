#!/usr/bin/env python3
"""
🤖 Luma AI Architect V2 - Workflow Guardian
============================================
State-based Workflow Orchestrator with GitHub Project Integration
"""

import os
import sys
import argparse
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

MENU_ACTIONS = {
    "1": {"label": "📋 List Active Issues",          "valid_phases": "ALL"},
    "2": {"label": "📥 Select Issue (from Kanban)", "valid_phases": [WorkflowPhase.IDLE, WorkflowPhase.CODING]},
    "3": {"label": "🧬 Refine Issue (Analyst)",        "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
    "4": {"label": "🧐 Code Review (Local)",       "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.PR_PENDING]},
    "5": {"label": "📝 Update Docs",               "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.IDLE]},
    "6": {"label": "🚀 Create Pull Request",       "valid_phases": [WorkflowPhase.CODING]},
    "7": {"label": "📊 View Kanban Status",        "valid_phases": "ALL"},
    "8": {"label": "🔄 Refresh State",             "valid_phases": "ALL"},
    "9": {"label": "🔀 Switch Project",             "valid_phases": "ALL"},
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
    
    # Initialize
    project_key = args.project if args.project in PROJECTS else "1"
    project = PROJECTS[project_key]
    
    # Load state
    state = load_state(project["path"])
    state.project_key = project_key
    
    print("\n🚀 Starting Luma V2 Workflow Guardian...")
    
    while True:
        # Display UI
        ui.display_header(state, project)
        ui.display_menu(state)
        
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
            actions.action_refine_issue(state, project)

        elif choice == "4":
            actions.action_code_review(state, project)
        
        elif choice == "5":
            actions.action_update_docs(state, project)
        
        elif choice == "6":
            actions.action_create_pr(state, project)
        
        elif choice == "7":
            actions.action_view_kanban(project)
        
        elif choice == "8":
            state = load_state(project["path"])
            print("🔄 State refreshed")

        elif choice == "9":
            new_key = actions.action_switch_project(state)
            if new_key:
                save_state(state, project["path"])  # Save old state
                project_key = new_key
                project = PROJECTS[project_key]
                state = load_state(project["path"])
                state.project_key = project_key
        
        else:
            print("❌ Invalid option")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
