#!/usr/bin/env python3
"""
🤖 Luma AI Architect V2 - Workflow Guardian
============================================
State-based Workflow Orchestrator with GitHub Project Integration
"""

import os
import sys
import argparse
import unicodedata

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
        "name": "JarWise (Android)",
        "path": "/Users/oatrice/Software-projects/JarWise/Android",
        "repo": "oatrice/JarWise-Android",
        "kanban_number": 7,
        "kanban_id": "PVT_kwHOATfKEM4BMuLi",
    },
    "3": {
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

def clear_screen():
    """Clear the terminal screen"""
    # os.system('cls' if os.name == 'nt' else 'clear')
    pass

def _get_visual_width(s: str) -> int:
    """Approximate visual width of a string using unicodedata"""
    width = 0
    for char in s:
        # Zero-width characters (Nonspacing Mark, Enclosing Mark, Format)
        if unicodedata.category(char) in ('Mn', 'Me', 'Cf'):
            continue
        
        # East Asian Width (Wide and Fullwidth count as 2)
        # Hangel Jamo leads/vowels are tricky but usually covered by W/F or 
        # distinct Logic if needed. For now, W/F is standard.
        eaw = unicodedata.east_asian_width(char)
        if eaw in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width

def _print_boxed_line(content: str, width: int = 58):
    """Print a line within the box, auto-padding right side"""
    vis_len = _get_visual_width(content)
    # We want total inner width = width + 2 (1 space left, 1 space right)
    # The border is width+2 long.
    # content + padding should equal width.
    padding = width - vis_len
    if padding < 0:
        padding = 0
    
    print(f"║ {content}{' ' * padding} ║")

def display_header(state: LumaState, project: dict):
    """Display the state-aware header"""
    # Disable clear_screen as requested
    # clear_screen()
    
    emoji, phase_name, _ = get_phase_display(state.phase)
    
    BOX_WIDTH = 58
    INNER_WIDTH = BOX_WIDTH
    
    # Border
    print("\n" + "╔" + "═" * (BOX_WIDTH + 2) + "╗")
    
    # Title
    title_text = " 🤖 Luma AI Architect V2 - Workflow Guardian"
    _print_boxed_line(title_text, BOX_WIDTH)
    
    print("╠" + "═" * (BOX_WIDTH + 2) + "╣")
    
    # Content Rows
    # We define a standard label width to align values vertically
    # "  🎯 Task: " -> approx 11-12 vis chars
    
    def format_row(icon, label, value):
        # Format: "  {icon} {label}: {value}"
        # We assume icon is 2-char wide visually
        prefix = f"  {icon} {label}: "
        return f"{prefix}{value}"

    _print_boxed_line(format_row("📂", "Project", project['name']), BOX_WIDTH)
    _print_boxed_line(format_row("📍", "Phase  ", f"{emoji} {phase_name}"), BOX_WIDTH)
    
    if state.active_issue:
        # Truncate title
        max_title_len = 35 
        title = state.active_issue.title
        if len(title) > max_title_len:
            title = title[:max_title_len] + "..."
        
        task_info = f"#{state.active_issue.number} {title}"
        _print_boxed_line(format_row("🎯", "Task   ", task_info), BOX_WIDTH)
    
    if state.active_branch:
        # Truncate branch
        max_branch_len = 40
        branch = state.active_branch
        if len(branch) > max_branch_len:
            branch = branch[:max_branch_len] + "..."
            
        _print_boxed_line(format_row("🌿", "Branch ", branch), BOX_WIDTH)
    
    print("╠" + "═" * (BOX_WIDTH + 2) + "╣")
    
    next_step = get_next_step_recommendation(state)
    _print_boxed_line(f"  ➡️  {next_step}", BOX_WIDTH)
    
    print("╚" + "═" * (BOX_WIDTH + 2) + "╝")


def display_menu(state: LumaState):
    """Display context-sensitive menu"""
    # Color codes (Basic usage)
    DIM = "\033[90m"
    RESET = "\033[0m"
    
    actions = {
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
    
    print("\n📋 Actions:")
    for key, action in actions.items():
        is_valid = False
        if action["valid_phases"] == "ALL":
            is_valid = True
        elif state.phase in action["valid_phases"]:
            is_valid = True
            
        if is_valid:
            print(f"  [{key}] {action['label']}")
        else:
            # Show disabled option in dim color
            print(f"  {DIM}[{key}] {action['label']} (Not available){RESET}")


# =============================================================================
# Menu Actions
# =============================================================================

def action_select_issue(state: LumaState, project: dict) -> bool:
    """Select an issue from Kanban (Ready or In Progress)"""
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
    
    # Fetch all cards
    all_cards = fetch_kanban_cards(project["kanban_number"])
    
    # Filter for Ready or In Progress
    valid_statuses = ["Ready", "In Progress"]
    selectable_issues = []
    
    for card in all_cards:
        # Case-insensitive check
        if any(s.lower() == card.status.lower() for s in valid_statuses):
            selectable_issues.append(card)
            
    if not selectable_issues:
        print("📭 No 'Ready' or 'In Progress' issues found on Kanban.")
        return False

    # Sort: In Progress first, then Ready
    def sort_key(c):
        # 0 = In Progress, 1 = Ready
        prio = 0 if c.status.lower() == "in progress" else 1
        return (prio, c.issue_number)
        
    selectable_issues.sort(key=sort_key)
    
    print("\n--- 📋 Select Issue to Work On ---")
    for i, card in enumerate(selectable_issues, 1):
        status_icon = "🔥" if card.status.lower() == "in progress" else "✅"
        print(f"  [{i}] {status_icon} #{card.issue_number}: {card.title[:50]} ({card.status})")
    print("  [0] Cancel")
    
    choice = input("\nSelect issue: ").strip()
    
    if choice == "0":
        return False
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(selectable_issues):
            return _start_issue(state, selectable_issues[idx], project)
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
    try:
        from luma_core.agents.analyst import generate_branch_names
        suggestions = generate_branch_names(card.title, card.body or "", card.issue_number)
    except Exception as e:
        print(f"⚠️ AI Agent unavailable: {e}")
        slug = card.title.lower().replace(" ", "-").replace("[", "").replace("]", "")[:30]
        suggestions = [f"feat/{card.issue_number}-{slug}"]

    print("\n🌿 Suggested branches:")
    for i, name in enumerate(suggestions, 1):
        print(f"  [{i}] {name}")
    
    choice = input("Select [1-3] or type custom name: ").strip()
    
    branch_name = suggestions[0] # Default
    
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(suggestions):
            branch_name = suggestions[idx]
    elif choice:
        branch_name = choice
    
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


def action_list_active_issues(project: dict):
    """List all active issues (Backlog, Ready, In Progress)"""
    print(f"\n📋 Fetching Active Issues for {project['name']}...")
    
    cards = fetch_kanban_cards(project["kanban_number"])
    
    if not cards:
        print("📭 No cards found")
        return
    
    # Filter out Done/Closed
    ignored_statuses = ["Done", "Closed"]
    active_cards = [c for c in cards if c.status not in ignored_statuses]
    
    if not active_cards:
        print("✅ No active issues! All done.")
        return

    # Sort Logic: In Progress -> Ready -> Backlog -> Others
    priority = {"In Progress": 0, "Ready": 1, "Backlog": 2}
    
    def get_priority(card):
        return priority.get(card.status, 99)
    
    active_cards.sort(key=lambda c: (get_priority(c), c.issue_number))
    
    print(f"\n{'─' * 70}")
    print(f"{'#':<5} {'Title':<40} {'Status':<12} {'Repository'}")
    print(f"{'─' * 70}")
    
    for card in active_cards:
        # Title truncation
        title = card.title[:38] + ".." if len(card.title) > 40 else card.title
        
        # Colorize status (simulated with emojis)
        status_icon = ""
        if card.status == "In Progress": status_icon = "🔥 "
        elif card.status == "Ready": status_icon = "✅ "
        elif card.status == "Backlog": status_icon = "📥 "
        
        display_status = f"{status_icon}{card.status}"
        
        print(f"#{card.issue_number:<4} {title:<40} {display_status:<15} {card.repository.split('/')[-1]}")
    
    print(f"{'─' * 70}")
    print(f"Total Active: {len(active_cards)} issues")



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
        "target_dir": project["path"],
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


def action_code_review(state: LumaState, project: dict):
    """Run local code review agent"""
    print(f"\n🧐 Local Code Reviewer ({project['name']})")
    
    target_dir = project["path"]
    
    # 1. Get changed files
    try:
        file_list = get_git_changed_files("all", target_dir=target_dir)
        if not file_list:
            print("✅ No changes found (Clean vs origin/main).")
            return
            
        print(f"   🔎 Found {len(file_list)} changed files.")
        
        # Limit files
        if len(file_list) > 30:
            print(f"⚠️ Too many files ({len(file_list)}). Reviewing top 10.")
            file_list = file_list[:10]
        
        changes = {}
        for rel_path in file_list:
            full_path = os.path.join(target_dir, rel_path)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                # Skip binary/large files heuristic
                if rel_path.endswith(('.png', '.jpg', '.ico', '.pdf', '.jar')):
                    continue
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        changes[rel_path] = f.read()
                except:
                    pass
        
        if not changes:
            print("❌ No readable content to review.")
            return

        # 2. Run Reviewer
        print(f"🚀 Running Reviewer on {list(changes.keys())}...")
        
        review_state = {
            "task": "Review local code changes for bugs, security issues, and best practices.",
            "changes": changes,
            "iterations": 0,
            "test_errors": "",
            "skip_coder": False
        }
        
        result = reviewer_agent(review_state)
        
        if result.get("code_content"):
            print("\n📝 Reviewer Feedback:")
            print("--------------------------------------------------")
            print(result["code_content"])
            print("--------------------------------------------------")
        
        if result.get("test_suggestions"):
            print("\n🧪 Test Suggestions:")
            print(result["test_suggestions"])
            
        print("\n✅ Review Complete.")
        
    except Exception as e:
        print(f"❌ Error during code review: {e}")


def action_update_docs(state: LumaState, project: dict):
    """Update documentation (Changelog, Version, README)"""
    print("\n📝 Documentation Update")
    print(f"   Project: {project['name']}")
    
    # 1. Determine Scope (Single vs Multi-Repo)
    # Heuristic: If project name contains "Root", treated as Multi-Repo Coordinator
    is_multi_repo = "Root" in project.get("name", "")
    target_repos = [project]
    
    if is_multi_repo:
        print("   Mode: Multi-Repo (JarWise)")
        # In a real dynamic system, we'd lookup sibling projects from the config
        # For now, hardcoded safe-check or assume PROJECTS dictionary has them
        # We will iterate through PROJECTS to find related ones if strict naming
        pass 
    
    print("\n🚀 Ready to update:")
    for repo in target_repos:
        print(f"   - {repo['name']}")
        
    confirm = input("\nProceed with docs update? (y/N): ").lower()
    if confirm != 'y':
        return

    # 2. Run Update
    print("\n⏳ Updating docs (AI-powered)...")
    results = update_multi_repo_docs(target_repos, docs_agent_func=None)
    
    # 3. Summary
    print("\n" + "=" * 40)
    print("📊 Docs Update Summary:")
    print("=" * 40)
    
    for r in results:
        status = "✅" if r.get("success") else "⏩"
        msg = ', '.join(r.get('files_updated', [])) if r.get("success") else r.get('error')
        print(f"   {status} {r['name']}: {msg}")
        
    print("\n✅ Done.")


def action_refine_issue(state: LumaState, project: dict):
    """Run Analyst Agent to refine issue"""
    if not state.active_issue:
        print("❌ No active issue selected to refine.")
        return

    # Enable Analyst Agent
    try:
        from luma_core.agents.analyst import analyst_agent
    except ImportError:
        print("❌ Analyst agent not available.")
        return

    # Create temporary state
    analyst_state = {
        "task": state.active_issue.title,
        "issue_data": {
            "title": state.active_issue.title,
            "number": state.active_issue.number,
            "body": state.active_issue.body
        },
        "target_dir": project["path"]
    }

    print("\n🧠 Invoking Analyst Agent...")
    result = analyst_agent(analyst_state)
    
    if result.get("analysis_file"):
        print(f"\n✨ Analysis complete! Document saved to: {result['analysis_file']}")
        input("Press Enter to continue...")
    else:
        print("\n⚠️ Analysis failed or produced no output.")

def action_switch_project(state: LumaState) -> str:
    """Switch to different project"""
    print("\n🔀 Select Project:")
    for key, proj in PROJECTS.items():
        print(f"  [{key}] {proj['name']}")
    
    choice = input("\nSelect: ").strip()
    
    if choice in PROJECTS:
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
            action_list_active_issues(project)

        elif choice == "2":
            if action_select_issue(state, project):
                save_state(state, project["path"])
        
        elif choice == "3":
            action_refine_issue(state, project)

        elif choice == "4":
            action_code_review(state, project)
        
        elif choice == "5":
            action_update_docs(state, project)
        
        elif choice == "6":
            action_create_pr(state, project)
        
        elif choice == "7":
            action_view_kanban(project)
        
        elif choice == "8":
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
