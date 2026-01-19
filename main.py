#!/usr/bin/env python3
"""
🤖 Luma AI Architect V2 - Workflow Guardian
============================================
State-based Workflow Orchestrator with GitHub Project Integration
"""

import os
import sys
import argparse

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


# =============================================================================
# Project Configuration
# =============================================================================

PROJECTS = {
    "1": {
        "name": "JarWise",
        "path": "/Users/oatrice/Software-projects/JarWise",
        "repo": "oatrice/JarWise-Root",
        "kanban_number": 7,
        "kanban_id": "PVT_kwHOATfKEM4BMuLi",
    },
    "2": {
        "name": "Tetris Battle",
        "path": "/Users/oatrice/Software-projects/Tetris-Battle",
        "repo": "oatrice/Tetris-Battle",
        "kanban_number": 6,
        "kanban_id": "PVT_kwHOATfKEM4BKZK5",
    },

}


# =============================================================================
# Display Functions
# =============================================================================

def display_header(state: LumaState, project: dict):
    """Display the state-aware header"""
    emoji, phase_name, _ = get_phase_display(state.phase)
    
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║  🤖 Luma AI Architect V2 - Workflow Guardian" + " " * 12 + "║")
    print("╠" + "═" * 58 + "╣")
    print(f"║  📂 Project: {project['name']:<43} ║")
    print(f"║  📍 Phase: {emoji} {phase_name:<44} ║")
    
    if state.active_issue:
        title = state.active_issue.title[:35] + "..." if len(state.active_issue.title) > 38 else state.active_issue.title
        print(f"║  🎯 Task: #{state.active_issue.number} {title:<40} ║")
    
    if state.active_branch:
        branch = state.active_branch[:42] if len(state.active_branch) > 42 else state.active_branch
        print(f"║  🌿 Branch: {branch:<45} ║")
    
    print("╠" + "═" * 58 + "╣")
    
    next_step = get_next_step_recommendation(state)
    print(f"║  ➡️  {next_step[:52]:<52} ║")
    print("╚" + "═" * 58 + "╝")


def display_menu(state: LumaState):
    """Display context-sensitive menu"""
    print("\n📋 Actions:")
    print("  [1] 📥 Select Issue (from Kanban)")
    print("  [2] 🚀 Create Pull Request")
    print("  [3] 🧐 Code Review (Local)")
    print("  [4] 📝 Update Docs")
    print("  [5] 📊 View Kanban Status")
    print("  [6] 🔄 Refresh State")
    print("  [9] 🔀 Switch Project")
    print("  [0] ❌ Exit")


# =============================================================================
# Menu Actions
# =============================================================================

def action_select_issue(state: LumaState, project: dict) -> bool:
    """Select an issue from Kanban"""
    print("\n🔍 Fetching issues from Kanban...")
    
    # Handle Self-Test / Dummy Mode
    if project.get("kanban_id") == "dummy":
        print("🛠️  Self-Test Mode: Entering dummy issue data.")
        dummy_card = KanbanCard(
            issue_number=999,
            title="Self-Test Feature",
            url="http://github.com/oatrice/Luma/issues/999",
            body="Testing Pre-flight checker in dev mode",
            status="In Progress",
            item_id="dummy_item_id",
            repository="oatrice/Luma"
        )
        return _start_issue(state, dummy_card, project)
    
    ready_issues = get_ready_issues(project["kanban_number"])
    
    if not ready_issues:
        print("📭 No 'Ready' issues found on Kanban.")
        
        # Try In Progress
        current = get_current_in_progress(project["kanban_number"])
        if current:
            print(f"\n💡 You have an active task: #{current.issue_number} {current.title}")
            resume = input("Resume this task? (y/n): ").strip().lower()
            if resume == 'y':
                return _start_issue(state, current, project)
        return False
    
    print("\n--- 📋 Ready Issues ---")
    for i, card in enumerate(ready_issues, 1):
        print(f"  [{i}] #{card.issue_number}: {card.title[:50]}")
    print("  [0] Cancel")
    
    choice = input("\nSelect issue: ").strip()
    
    if choice == "0":
        return False
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(ready_issues):
            return _start_issue(state, ready_issues[idx], project)
    except ValueError:
        pass
    
    print("❌ Invalid selection")
    return False


def _start_issue(state: LumaState, card: KanbanCard, project: dict) -> bool:
    """Start working on an issue"""
    # Transition to selecting first
    if state.phase == WorkflowPhase.IDLE:
        transition_to(state, WorkflowPhase.SELECTING)
    
    # Create IssueData
    issue = IssueData(
        number=card.issue_number,
        title=card.title,
        html_url=card.url,
        body=card.body,
        project_item_id=card.item_id,
        project_id=project["kanban_id"],
        repository=card.repository
    )
    
    # Show Context
    print("\n🧠 Loading Project Context...")
    try:
        summarizer = ContextSummarizer(project["path"])
        reminders = summarizer.summarize_rules()
        if reminders:
            print("\n📝 Project Reminders & Rules:")
            for r in reminders:
                print(f"  {r}")
        else:
            print("  No specific rules found.")
    except Exception as e:
        print(f"⚠️ Failed to load context: {e}")
    
    # Suggest branch name
    slug = card.title.lower().replace(" ", "-").replace("[", "").replace("]", "")[:30]
    branch_name = f"feat/{card.issue_number}-{slug}"
    
    print(f"\n🌿 Suggested branch: {branch_name}")
    custom = input("Press Enter to accept or type custom name: ").strip()
    
    if custom:
        branch_name = custom
    
    # Transition to coding
    ok, msg = transition_to(
        state, 
        WorkflowPhase.CODING,
        active_issue=issue,
        active_branch=branch_name
    )
    
    if ok:
        print(f"\n✅ Started: #{card.issue_number} {card.title}")
        print(f"🌿 Branch: {branch_name}")
        
        # Sync Kanban
        if card.item_id and project.get("kanban_id"):
            print("🔄 Syncing Kanban status...")
            sync_kanban_on_action("select_issue", project["kanban_id"], card.item_id)
        
        return True
    else:
        print(f"❌ {msg}")
        return False


def action_view_kanban(project: dict):
    """View Kanban status"""
    print(f"\n📊 Fetching {project['name']} Kanban...")
    
    cards = fetch_kanban_cards(project["kanban_number"])
    
    if not cards:
        print("📭 No cards found")
        return
    
    # Group by status
    by_status = {}
    for card in cards:
        status = card.status
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(card)
    
    print(f"\n{'─' * 60}")
    for status, items in by_status.items():
        print(f"\n📌 {status} ({len(items)})")
        for card in items[:5]:
            print(f"   #{card.issue_number}: {card.title[:45]}")
        if len(items) > 5:
            print(f"   ... and {len(items) - 5} more")
    print(f"\n{'─' * 60}")
    print(f"Total: {len(cards)} cards")


from luma_core.preflight_checker import PreflightChecker

def action_create_pr(state: LumaState, project: dict):
    """Create Pull Request with Pre-flight Checks"""
    if state.phase != WorkflowPhase.CODING:
        print(f"❌ Cannot create PR in '{state.phase.value}' phase")
        print("💡 Start coding first by selecting an issue")
        return
    
    if not state.active_issue or not state.active_branch:
        print("❌ No active issue/branch")
        return
    
    # 1. Transition to PREFLIGHT
    print("\n🔄 Transitioning to PREFLIGHT phase...")
    ok, msg = transition_to(state, WorkflowPhase.PREFLIGHT)
    if not ok:
        print(msg)
        return

    # 2. Run Pre-flight Checks
    print("🛫 Running Pre-flight Checks...")
    checker = PreflightChecker(project["path"])
    results = checker.run_checks()
    
    passed_all = True
    print("-" * 50)
    for res in results:
        icon = "✅" if res.passed else "❌"
        status = "PASS" if res.passed else "FAIL"
        print(f"{icon} [{status}] {res.name}: {res.message}")
        
        if not res.passed:
            passed_all = False
            
    print("-" * 50)
    
    if not passed_all:
        print("\n❌ One or more pre-flight checks failed.")
        print("💡 Please fix the issues above and try again.")
        
        override = input("⚠️ Force create PR anyways? (y/N): ").strip().lower()
        if not override:
            override = 'n'
            
        if override != 'y':
            # Revert to CODING
            transition_to(state, WorkflowPhase.CODING)
            return

    # 3. Proceed to Create PR
    print("\n🚀 Pre-flight checks passed (or overridden). Creating PR...")
    print(f"   Issue: #{state.active_issue.number} {state.active_issue.title}")
    print(f"   Branch: {state.active_branch}")
    
    # Enable GitHub Tools
    try:
        from luma_core.agents.publisher import publisher_agent
    except ImportError:
        print("❌ Publisher agent not available.")
        transition_to(state, WorkflowPhase.CODING)
        return
    
    # Construct a temporary state for the publisher
    pub_state = {
        "task": state.active_issue.title,
        "issue_data": {
            "title": state.active_issue.title,
            "number": state.active_issue.number
        },
        "repo": project["repo"],
        "test_suggestions": ""
    }
    
    print("\n📤 invoking Publisher Agent...")
    result = publisher_agent(pub_state)
    pr_url = result.get("pr_url")
    
    if pr_url:
        print(f"\n✅ PR Created: {pr_url}")
        ok, msg = transition_to(state, WorkflowPhase.PR_PENDING, pr_url=pr_url)
        if ok:
             print("🔄 State updated to PR_PENDING")
        else:
             print(f"⚠️ Failed to update state: {msg}")
    else:
        print("\n⚠️ Publisher finished but no PR URL returned.")
        # Revert to CODING so they can retry
        transition_to(state, WorkflowPhase.CODING)



def action_switch_project(state: LumaState) -> str:
    """Switch to different project"""
    print("\n🔀 Select Project:")
    for key, proj in PROJECTS.items():
        print(f"  [{key}] {proj['name']}")
    
    choice = input("\nSelect: ").strip()
    
    if choice in PROJECTS:
        # Reset state if switching
        if state.phase != WorkflowPhase.IDLE:
            confirm = input("⚠️ You have active work. Reset state? (y/n): ").strip().lower()
            if confirm == 'y':
                transition_to(state, WorkflowPhase.IDLE)
        return choice
    
    return None


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
        display_header(state, project)
        display_menu(state)
        
        choice = input("\n👉 Select: ").strip()
        
        if choice == "0":
            # Save state before exit
            save_state(state, project["path"])
            print("\n👋 State saved. Goodbye!")
            break
        
        elif choice == "1":
            if action_select_issue(state, project):
                save_state(state, project["path"])
        
        elif choice == "2":
            action_create_pr(state, project)
        
        elif choice == "3":
            print("\n🧐 Code Review - Use V1 for now")
            print("💡 python3 v1_legacy/main.py")
        
        elif choice == "4":
            print("\n📝 Update Docs - Use V1 for now")
            print("💡 python3 v1_legacy/main.py")
        
        elif choice == "5":
            action_view_kanban(project)
        
        elif choice == "6":
            state = load_state(project["path"])
            print("🔄 State refreshed")
        
        elif choice == "9":
            new_key = action_switch_project(state)
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
