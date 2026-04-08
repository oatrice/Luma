import re
from luma_core.ui import safe_input
from luma_core.state_manager import LumaState, WorkflowPhase, IssueData
from .utils import (
    fetch_kanban_cards,
    get_status_workflow,
    _get_selectable_cards,
    _status_key,
    _status_priority,
    _get_status_icon,
    _display_selection_blockers,
    _start_issues,
    sync_kanban_on_action,
    KanbanCard
)
from .quality_actions import sync_roadmap_for_closed_issues, sync_roadmap_for_new_issues
from luma_core.github_client import create_issue
from luma_core.github_project import add_issue_to_project
from .create_issue_action import (
    detect_zenith_issues_from_text,
    detect_zenith_issues_from_branch,
)

def action_create_issue(state: LumaState, project: dict, title: str = None, body: str = None, headless: bool = False) -> dict:
    """Create a new GitHub issue (First-class action)"""
    if not headless:
        print("\n➕ Create New GitHub Issue")
        if not title:
            title = safe_input("   Issue Title: ").strip()
        if not title:
            print("   ❌ Title cannot be empty.")
            return {"success": False, "error": "Title cannot be empty"}

        if not body:
            print("   Issue Body (enter for default template):")
            body = safe_input("   > ").strip()

    # Ensure title and body are present for headless
    if headless and not title:
        return {"success": False, "error": "Missing --title for create_issue action"}

    # Mandatory ## Related section logic
    related_tag = "## Related"
    if not body:
        body = f"\n\n{related_tag}: #"
    elif related_tag not in body:
        body = body.rstrip() + f"\n\n{related_tag}: #"

    repo_name = project.get("repo")
    if not repo_name:
        error_msg = f"No repository configured for project '{project['name']}'"
        if not headless:
            print(f"   ❌ {error_msg}")
        return {"success": False, "error": error_msg}

    if not headless:
        print(f"   🚀 Creating issue in {repo_name}...")

    result = create_issue(repo_name, title, body)

    if result.get("success"):
        # Auto-add to Kanban if project has kanban_number
        kanban_number = project.get("kanban_number")
        if kanban_number and result.get("url"):
            if not headless:
                print(f"   🔄 Adding to Kanban (Project #{kanban_number})...")
            item_id = add_issue_to_project(kanban_number, result["url"])
            if item_id:
                if not headless:
                    print("   ✅ Added to Kanban")
                result["project_item_id"] = item_id
            else:
                if not headless:
                    print("   ⚠️ Could not add to Kanban (may need manual addition)")
        
        if not headless:
            print(f"   ✅ Created: {result['url']}")
        return result
    else:
        if not headless:
            print(f"   ❌ Failed: {result.get('error')}")
        return result

def action_select_issue(state: LumaState, project: dict) -> bool:
    """Select an issue from Kanban (Ready or In Progress)"""
    print("\n💡 เช็ค gh cli, Roadmap.md ว่าต้องทำ issue ไหนต่อ")
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
            repository="oatrice/Luma",
        )
        return _start_issues(state, [dummy_card], project)

    # Fetch all cards
    all_cards = fetch_kanban_cards(project["kanban_number"])
    workflow = get_status_workflow(project)
    selectable_issues = _get_selectable_cards(all_cards, project)

    print("🗺️  Checking and syncing Roadmap.md...")
    synced_total = 0

    # Auto-sync CLOSED issues to Roadmap.md (silent background sync)
    try:
        done_statuses = {_status_key(s) for s in workflow.get("done_statuses", ["Done", "Closed"])}
        closed_issue_nums = [
            c.issue_number for c in all_cards if _status_key(c.status) in done_statuses
        ]
        if closed_issue_nums:
            synced = sync_roadmap_for_closed_issues(project, closed_issue_nums)
            if synced:
                print(f"   🔄 Synced {synced} closed issue(s) → Roadmap.md")
                synced_total += synced
    except Exception:
        pass  # Never block issue selection due to roadmap sync error

    # Auto-append NEW OPEN issues not yet in Roadmap.md
    try:
        if all_cards:
            new_appended = sync_roadmap_for_new_issues(project, all_cards)
            if new_appended:
                print(f"   📌 {new_appended} new issue(s) appended → Roadmap.md")
                synced_total += new_appended
    except Exception:
        pass  # Never block issue selection

    if synced_total == 0:
        print("   ✅ Roadmap is up to date.")

    if not selectable_issues:
        allowed = "', '".join(workflow.get("selectable_statuses", []))
        print(f"📭 No '{allowed}' issues found on Kanban.")
        _display_selection_blockers(all_cards, workflow)
        return False

    print("\n--- 📋 Select Issue to Work On ---")
    for i, card in enumerate(selectable_issues, 1):
        status_icon = _get_status_icon(card.status, workflow) or "✅"
        print(
            f"  [{i}] {status_icon} #{card.issue_number}: {card.title[:50]} ({card.status})"
        )
    print("  [0] Cancel")
    print("  ℹ️  Comma-separated for multi-select (e.g. 1,3)")

    choice = safe_input("\nSelect issue(s): ")

    if choice == "0":
        return False

    # Parse multi-select (e.g. "1,3" or "1")
    try:
        indices = [int(x.strip()) - 1 for x in choice.split(",")]
        selected_cards = []
        for idx in indices:
            if 0 <= idx < len(selectable_issues):
                selected_cards.append(selectable_issues[idx])
            else:
                print(f"❌ Invalid index: {idx + 1}")
        if not selected_cards:
            return False
        
        # Detect cross-repo links from selected issue bodies
        cross_repo_links = []
        for card in selected_cards:
            if card.body:
                cross_repo_links.extend(detect_zenith_issues_from_text(card.body))
        
        # Remove duplicates
        seen = set()
        unique_links = []
        for link in cross_repo_links:
            key = f"{link.repo}#{link.issue_number}"
            if key not in seen:
                unique_links.append(link)
                seen.add(key)
        
        if unique_links:
            print(f"\n🔗 Cross-Repo Links Detected ({len(unique_links)}):")
            for link in unique_links:
                print(f"   • {link.repo}#{link.issue_number} → {link.url}")
            
            # Store in state for later PR creation
            state.context["cross_repo_links"] = [
                {
                    "repo": link.repo,
                    "issue_number": link.issue_number,
                    "url": link.url,
                    "relationship": link.relationship,
                }
                for link in unique_links
            ]
            print("   💡 Links will be auto-included when creating PR")
            
        return _start_issues(state, selected_cards, project)
    except (ValueError, IndexError):
        print("❌ Invalid input. Please enter numbers.")
        return False

def action_add_issue(state: LumaState, project: dict) -> bool:
    """Add an issue to the current active issues (mid-work)"""
    if state.phase not in [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]:
        print("❌ Can only add issues during CODING or PREFLIGHT phase.")
        return False

    print("\n➕ Add Issue to Current Work Session")
    if state.active_issues:
        print(
            f"   Current issues: {', '.join(f'#{i.number}' for i in state.active_issues)}"
        )

    all_cards = fetch_kanban_cards(project["kanban_number"])
    active_nums = {i.number for i in state.active_issues}
    selectable = _get_selectable_cards(all_cards, project, exclude_numbers=active_nums)

    if not selectable:
        print("📬 No additional issues available.")
        return False

    for i, card in enumerate(selectable, 1):
        print(f"  [{i}] #{card.issue_number}: {card.title[:50]} ({card.status})")
    print("  [0] Cancel")

    choice = safe_input("\nSelect issue to add: ").strip()
    if choice == "0":
        return False

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(selectable):
            card = selectable[idx]
            new_issue = IssueData(
                number=card.issue_number,
                title=card.title,
                html_url=card.url,
                body=card.body,
                project_item_id=card.item_id,
                repository=card.repository,
            )
            state.active_issues.append(new_issue)
            print(f"✅ Added #{card.issue_number}: {card.title[:40]}")
            print(
                f"   Active issues: {', '.join(f'#{i.number}' for i in state.active_issues)}"
            )

            # Sync Kanban
            if card.item_id and project.get("kanban_id"):
                sync_kanban_on_action(
                    "select_issue",
                    project["kanban_id"],
                    card.item_id,
                )
            return True
    except ValueError:
        pass

    print("❌ Invalid selection")
    return False

def action_remove_issue(state: LumaState, project: dict) -> bool:
    """Remove an issue from the current active issues"""
    if not state.active_issues or len(state.active_issues) <= 1:
        print("❌ Cannot remove: need at least 1 active issue.")
        return False

    print("\n➖ Remove Issue from Current Work Session")
    for i, issue in enumerate(state.active_issues, 1):
        primary = " (primary)" if i == 1 else ""
        print(f"  [{i}] #{issue.number}: {issue.title[:50]}{primary}")
    print("  [0] Cancel")

    choice = safe_input("\nSelect issue to remove: ").strip()
    if choice == "0":
        return False

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(state.active_issues):
            removed = state.active_issues.pop(idx)
            print(f"✅ Removed #{removed.number}: {removed.title[:40]}")
            print(
                f"   Remaining: {', '.join(f'#{i.number}' for i in state.active_issues)}"
            )
            return True
    except ValueError:
        pass

    print("❌ Invalid selection")
    return False

def action_view_kanban(project: dict):
    """View Kanban status"""
    print(f"\n📊 Fetching {project['name']} Kanban...")
    workflow = get_status_workflow(project)
    board_priority = _status_priority(workflow.get("board_order", []))

    cards = fetch_kanban_cards(project["kanban_number"])

    if not cards:
        print("📬 No cards found")
        return

    # Group cards by status
    cards_by_status = {}
    for card in cards:
        cards_by_status.setdefault(card.status or "Unknown", []).append(card)

    # Sort statuses by priority
    sorted_statuses = sorted(
        cards_by_status.keys(),
        key=lambda s: (board_priority.get(_status_key(s), 999), _status_key(s)),
    )

    for status in sorted_statuses:
        status_icon = _get_status_icon(status, workflow) or "➡️"
        print(f"\n{status_icon} {status}")
        for card in cards_by_status[status]:
            print(f"  #{card.issue_number}: {card.title[:65]}")

def action_list_active_issues(project: dict):
    """List all active issues (Backlog, Ready, In Progress)"""
    print(f"\n📋 Fetching Active Issues for {project['name']}...")
    workflow = get_status_workflow(project)
    # Use active_sort_order for display order of active issues
    active_sort_order = workflow.get("active_sort_order", workflow.get("board_order", []))
    status_priority = _status_priority(active_sort_order)

    cards = fetch_kanban_cards(project["kanban_number"])

    if not cards:
        print("📭 No cards found")
        return

    active_statuses = {_status_key(status) for status in workflow.get("active_statuses", [])}
    if active_statuses:
        active_cards = [c for c in cards if _status_key(c.status) in active_statuses]
        # Sort by active status priority then by issue number
        active_cards.sort(
            key=lambda c: (status_priority.get(_status_key(c.status), 999), c.issue_number)
        )
        for card in active_cards:
            print(f"  #{card.issue_number}: {card.title[:65]} ({card.status})")
    else:
        print("ℹ️ No active statuses configured for this project.")

def bootstrap_issue(state: LumaState, project: dict, issue_numbers: list[int], branch_name: str = None) -> bool:
    """
    Bootstrap a specific issue (or multiple) for headless/machine-readable workflows.
    Fetches the issue data from Kanban and starts the coding phase.
    """
    print(f"\n🚀 Bootstrapping issue(s): {', '.join(map(str, issue_numbers))}")
    
    # Fetch all cards to find the requested ones
    all_cards = fetch_kanban_cards(project["kanban_number"])
    
    selected_cards = []
    for num in issue_numbers:
        card = next((c for c in all_cards if c.issue_number == num), None)
        if card:
            selected_cards.append(card)
        else:
            print(f"❌ Issue #{num} not found on Kanban.")
            
    if not selected_cards or len(selected_cards) != len(issue_numbers):
        return False
        
    from .utils import _start_issues_headless
    return _start_issues_headless(state, selected_cards, project, branch_name=branch_name)
