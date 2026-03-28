import re
from luma_core.ui import safe_input
from .utils import *
from .quality_actions import sync_roadmap_for_closed_issues, sync_roadmap_for_new_issues

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
                return False
        if selected_cards:
            return _start_issues(state, selected_cards, project)
    except ValueError:
        import traceback

        traceback.print_exc()
        pass

    print("❌ Invalid selection")
    return False

def action_add_issue(state: LumaState, project: dict) -> bool:
    """Add an issue to the current active issues (mid-work)"""
    if state.phase not in [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]:
        print("❌ Can only add issues during CODING or PREFLIGHT phase.")
        return False

    print("\n\u2795 Add Issue to Current Work Session")
    workflow = get_status_workflow(project)
    if state.active_issues:
        print(
            f"   Current issues: {', '.join(f'#{i.number}' for i in state.active_issues)}"
        )

    all_cards = fetch_kanban_cards(project["kanban_number"])
    active_nums = {i.number for i in state.active_issues}
    selectable = _get_selectable_cards(all_cards, project, exclude_numbers=active_nums)

    if not selectable:
        print("\ud83d\udced No additional issues available.")
        return False

    for i, card in enumerate(selectable, 1):
        print(f"  [{i}] #{card.issue_number}: {card.title[:50]} ({card.status})")
    print("  [0] Cancel")

    choice = safe_input("\nSelect issue to add: ")
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
                project_id=project["kanban_id"],
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
                    workflow.get("action_status_map"),
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

    print("\n\u2796 Remove Issue from Current Work Session")
    for i, issue in enumerate(state.active_issues, 1):
        primary = " (primary)" if i == 1 else ""
        print(f"  [{i}] #{issue.number}: {issue.title[:50]}{primary}")
    print("  [0] Cancel")

    choice = safe_input("\nSelect issue to remove: ")
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
    sorted_statuses = sorted(
        by_status.keys(),
        key=lambda status: (board_priority.get(_status_key(status), 999), _status_key(status)),
    )
    for status in sorted_statuses:
        items = by_status[status]
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
    workflow = get_status_workflow(project)

    cards = fetch_kanban_cards(project["kanban_number"])

    if not cards:
        print("📭 No cards found")
        return

    active_statuses = {_status_key(status) for status in workflow.get("active_statuses", [])}
    if active_statuses:
        active_cards = [c for c in cards if _status_key(c.status) in active_statuses]
    else:
        done_statuses = {_status_key(status) for status in workflow.get("done_statuses", [])}
        active_cards = [c for c in cards if _status_key(c.status) not in done_statuses]

    if not active_cards:
        print("✅ No active issues! All done.")
        return

    priority = _status_priority(workflow.get("active_sort_order", []))

    def get_priority(card):
        return priority.get(_status_key(card.status), 99)

    active_cards.sort(key=lambda c: (get_priority(c), c.issue_number))

    print(f"\n{'─' * 70}")
    print(f"{'#':<5} {'Title':<40} {'Status':<12} {'Repository'}")
    print(f"{'─' * 70}")

    for card in active_cards:
        # Title truncation
        title = card.title[:38] + ".." if len(card.title) > 40 else card.title

        # Colorize status (simulated with emojis)
        status_icon = _get_status_icon(card.status, workflow)
        display_status = f"{status_icon}{card.status}"

        print(
            f"#{card.issue_number:<4} {title:<40} {display_status:<15} {card.repository.split('/')[-1]}"
        )

    print(f"{'─' * 70}")
    print(f"Total Active: {len(active_cards)} issues")
