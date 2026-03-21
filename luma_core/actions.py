import datetime
import json
import os
import sys
from dataclasses import asdict
from collections import deque

import luma_core.usage_tracker as usage_tracker
from luma_core.agents.publisher import publisher_agent
from luma_core.config import PROJECTS, get_status_workflow, normalize_project_entry
from luma_core.context_summarizer import ContextSummarizer
from luma_core.doc_updates import pending_doc_update_summary, refresh_pending_doc_updates
from luma_core.github_project import (
    KanbanCard,
    fetch_kanban_cards,
    run_gh_command,
    sync_kanban_on_action,
)
from luma_core.preflight_checker import PreflightChecker
from luma_core.issue_metrics import (
    EFFORT_LEVELS,
    IssueMetricsRecord,
    format_metric_datetime,
    get_issue_metrics,
    list_issue_metrics,
    parse_metric_datetime,
    prefill_metrics_from_roadmap,
    save_issue_metrics,
    validate_effort_level,
)
from luma_core.state_manager import (
    IssueData,
    LumaState,
    WorkflowPhase,
    get_next_step_recommendation,
    transition_to,
)
from luma_core.tools import (
    generate_draft_code_review,
    get_git_changed_files,
    update_multi_repo_docs,
)
from luma_core import usage_tracker

# =============================================================================
# Menu Actions
# =============================================================================


def _status_key(status: str) -> str:
    return (status or "").strip().lower()


def _status_priority(order: list) -> dict:
    return {_status_key(status): idx for idx, status in enumerate(order)}


def _get_status_icon(status: str, workflow: dict) -> str:
    for configured_status, icon in workflow.get("status_icons", {}).items():
        if _status_key(configured_status) == _status_key(status):
            return icon
    return ""


def _get_selectable_cards(cards: list, project: dict, exclude_numbers: set = None) -> list:
    workflow = get_status_workflow(project)
    selectable_statuses = {
        _status_key(status) for status in workflow.get("selectable_statuses", [])
    }
    selection_priority = _status_priority(workflow.get("selection_order", []))
    exclude_numbers = exclude_numbers or set()

    selectable_cards = [
        card
        for card in cards
        if _status_key(card.status) in selectable_statuses
        and card.issue_number not in exclude_numbers
    ]

    selectable_cards.sort(
        key=lambda card: (
            selection_priority.get(_status_key(card.status), 999),
            card.issue_number,
        )
    )
    return selectable_cards


def _display_selection_blockers(
    cards: list,
    workflow: dict,
    exclude_numbers: set = None,
) -> None:
    """Explain why the board looks empty when no cards match the selectable lanes."""
    exclude_numbers = exclude_numbers or set()
    selectable_statuses = {
        _status_key(status) for status in workflow.get("selectable_statuses", [])
    }
    board_priority = _status_priority(workflow.get("board_order", []))
    blocked_by_status = {}

    for card in cards:
        if card.issue_number in exclude_numbers:
            continue
        if _status_key(card.status) in selectable_statuses:
            continue
        blocked_by_status.setdefault(card.status or "Unknown", []).append(card)

    if not blocked_by_status:
        print("   The board currently has no other issue cards.")
        return

    print("   Available elsewhere on the board:")
    sorted_statuses = sorted(
        blocked_by_status.keys(),
        key=lambda status: (
            board_priority.get(_status_key(status), 999),
            _status_key(status),
        ),
    )

    for status in sorted_statuses:
        items = blocked_by_status[status]
        print(f"   - {status}: {len(items)}")
        for card in items[:3]:
            print(f"     #{card.issue_number}: {card.title[:55]}")
        if len(items) > 3:
            print(f"     ... and {len(items) - 3} more")

    allowed = " or ".join(workflow.get("selectable_statuses", []))
    if allowed:
        print(f"   Move a card to {allowed} on the GitHub Project board, then try again.")


def _build_code_review_followup_prompt(multi_repo: bool = False) -> str:
    if multi_repo:
        return (
            "นำ code review จาก code_review.md "
            "(อาจจะติด gitignored ต้องเข้าไปอ่านตรงๆ) ในทุก repo มาอธิบาย "
            "และถามเพื่อ clarify ด้วย และให้ทำตาม Test suggestion ทั้งหมดด้วย "
            "ถ้า code_review.md ไม่ make sense ให้ใช้ draft_code_review.md แทน"
        )

    return (
        "นำ code review จาก code_review.md "
        "(อาจจะติด gitignored ต้องเข้าไปอ่านตรงๆ) มาอธิบาย "
        "และถามเพื่อ clarify ด้วย และให้ทำตาม Test suggestion ทั้งหมดด้วย "
        "ถ้า code_review.md ไม่ make sense ให้ใช้ draft_code_review.md แทน"
    )


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
        return _start_issue(state, dummy_card, project)

    # Fetch all cards
    all_cards = fetch_kanban_cards(project["kanban_number"])
    workflow = get_status_workflow(project)
    selectable_issues = _get_selectable_cards(all_cards, project)

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

    choice = input("\nSelect issue(s): ").strip()

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
    except ValueError as e:
        import traceback

        traceback.print_exc()
        pass

    print("❌ Invalid selection")
    return False


def _start_issues(state: LumaState, cards: list, project: dict) -> bool:
    """Start working on one or more issues"""

    # Check if ALL these issues are already active (re-selecting same set)
    active_nums = (
        {i.number for i in state.active_issues} if state.active_issues else set()
    )
    card_nums = {c.issue_number for c in cards}

    if active_nums == card_nums and state.active_branch:
        print(
            f"\n✅ Already working on {', '.join(f'#{n}' for n in card_nums)} - continuing..."
        )
        print(f"🌿 Branch: {state.active_branch}")

        # Ensure git is on the correct branch
        import subprocess

        try:
            result = subprocess.run(
                ["git", "checkout", state.active_branch],
                cwd=project["path"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"✅ Switched to branch '{state.active_branch}'.")
            else:
                create_result = subprocess.run(
                    ["git", "checkout", "-b", state.active_branch],
                    cwd=project["path"],
                    capture_output=True,
                    text=True,
                )
                if create_result.returncode == 0:
                    print(f"✅ Created and switched to branch '{state.active_branch}'.")
                else:
                    print(f"⚠️ Git: {create_result.stderr.strip()}")

            # Also ensure sibling repos are on the correct branch
            if project.get("type") == "monorepo_root" and project.get("sibling_repos"):
                from luma_core.config import PROJECTS

                print(f"🔄 Syncing sibling repos...")
                for sibling_key in project.get("sibling_repos", []):
                    sibling = PROJECTS.get(sibling_key)
                    if sibling and os.path.exists(sibling["path"]):
                        sib_result = subprocess.run(
                            ["git", "checkout", state.active_branch],
                            cwd=sibling["path"],
                            capture_output=True,
                            text=True,
                        )
                        if sib_result.returncode == 0:
                            print(f"   ✅ {sibling['name']}: Switched to branch")
                        else:
                            create_sib = subprocess.run(
                                ["git", "checkout", "-b", state.active_branch],
                                cwd=sibling["path"],
                                capture_output=True,
                                text=True,
                            )
                            if create_sib.returncode == 0:
                                print(f"   ✅ {sibling['name']}: Branch created")
                            else:
                                print(
                                    f"   ⚠️ {sibling['name']}: {sib_result.stderr.strip()}"
                                )

        except Exception as e:
            print(f"⚠️ Git error: {e}")

        return True

    # Transition to selecting first (only if coming from IDLE)
    if state.phase == WorkflowPhase.IDLE:
        transition_to(state, WorkflowPhase.SELECTING)
    # If already CODING, we're switching issues - no need to go through SELECTING

    # Create IssueData list
    issues = []
    for card in cards:
        issues.append(
            IssueData(
                number=card.issue_number,
                title=card.title,
                html_url=card.url,
                body=card.body,
                project_item_id=card.item_id,
                project_id=project["kanban_id"],
                repository=card.repository,
            )
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

    # Suggest branch name (with multi-issue numbers)
    issue_nums = "-".join(str(c.issue_number) for c in cards)
    primary_title = cards[0].title
    primary_body = cards[0].body or ""
    primary_number = cards[0].issue_number

    try:
        from luma_core.agents.analyst import generate_branch_names

        suggestions = generate_branch_names(primary_title, primary_body, primary_number)
        # Replace single issue number with multi-issue numbers in suggestions
        if len(cards) > 1:
            suggestions = [
                s.replace(f"/{primary_number}-", f"/{issue_nums}-") for s in suggestions
            ]
    except Exception as e:
        print(f"⚠️ AI Agent unavailable: {e}")
        slug = (
            primary_title.lower()
            .replace(" ", "-")
            .replace("[", "")
            .replace("]", "")[:30]
        )
        suggestions = [f"feat/{issue_nums}-{slug}"]

    print("\n🌿 Suggested branches:")
    for i, name in enumerate(suggestions, 1):
        print(f"  [{i}] {name}")

    choice = input("Select [1-3] or type custom name: ").strip()

    branch_name = suggestions[0]  # Default

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(suggestions):
            branch_name = suggestions[idx]
    elif choice:
        branch_name = choice

    # Transition to coding
    ok, msg = transition_to(
        state, WorkflowPhase.CODING, active_issues=issues, active_branch=branch_name
    )

    if ok:
        issue_display = ", ".join(f"#{c.issue_number}" for c in cards)
        workflow = get_status_workflow(project)
        print(f"\n✅ Started: {issue_display}")
        for c in cards:
            print(f"   🎯 #{c.issue_number}: {c.title[:50]}")
        print(f"🌿 Branch: {branch_name}")

        # Actually create the branch in Git
        import subprocess

        try:
            print(f"🔄 Creating git branch...")
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=project["path"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"✅ Branch '{branch_name}' created and checked out.")
            else:
                switch_result = subprocess.run(
                    ["git", "checkout", branch_name],
                    cwd=project["path"],
                    capture_output=True,
                    text=True,
                )
                if switch_result.returncode == 0:
                    print(f"✅ Switched to existing branch '{branch_name}'.")
                else:
                    print(f"⚠️ Git error: {result.stderr.strip()}")

            # Create branches in sibling repos
            if project.get("type") == "monorepo_root" and project.get("sibling_repos"):
                from luma_core.config import PROJECTS

                print(f"\n🔄 Creating branches in sibling repos...")
                for sibling_key in project.get("sibling_repos", []):
                    sibling = PROJECTS.get(sibling_key)
                    if sibling and os.path.exists(sibling["path"]):
                        sib_result = subprocess.run(
                            ["git", "checkout", "-b", branch_name],
                            cwd=sibling["path"],
                            capture_output=True,
                            text=True,
                        )
                        if sib_result.returncode == 0:
                            print(f"   ✅ {sibling['name']}: Branch created")
                        else:
                            switch_sib = subprocess.run(
                                ["git", "checkout", branch_name],
                                cwd=sibling["path"],
                                capture_output=True,
                                text=True,
                            )
                            if switch_sib.returncode == 0:
                                print(
                                    f"   ✅ {sibling['name']}: Switched to existing branch"
                                )
                            else:
                                print(
                                    f"   ⚠️ {sibling['name']}: {sib_result.stderr.strip()}"
                                )

        except Exception as e:
            print(f"⚠️ Failed to create branch: {e}")

        # Sync Kanban for all issues
        for i, card in enumerate(cards):
            if card.item_id and project.get("kanban_id"):
                if i == 0:
                    print("🔄 Syncing Kanban status...")
                sync_kanban_on_action(
                    "select_issue",
                    project["kanban_id"],
                    card.item_id,
                    workflow.get("action_status_map"),
                )

        return True
    else:
        print(f"❌ {msg}")
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

    choice = input("\nSelect issue to add: ").strip()
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

    choice = input("\nSelect issue to remove: ").strip()
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


_KEEP_METRIC_VALUE = object()


def _get_metrics_project_cards(project: dict) -> list:
    cards = fetch_kanban_cards(project["kanban_number"])
    repo = project.get("repo")
    if repo:
        cards = [card for card in cards if card.repository == repo]

    workflow = get_status_workflow(project)
    board_priority = _status_priority(workflow.get("board_order", []))
    cards.sort(
        key=lambda card: (
            board_priority.get(_status_key(card.status), 999),
            card.issue_number,
        )
    )
    return cards


def _select_issue_card_for_metrics(project: dict):
    cards = _get_metrics_project_cards(project)
    if not cards:
        print("📭 No GitHub issues found for this project.")
        return None

    print(f"\n🎯 Issues in {project['name']}")
    print(f"{'Idx':<5} {'#':<6} {'Title':<38} {'Status'}")
    print("─" * 72)
    for idx, card in enumerate(cards, 1):
        title = card.title[:36] + ".." if len(card.title) > 38 else card.title
        print(f"{idx:<5} #{card.issue_number:<5} {title:<38} {card.status}")

    choice = input("\nSelect index or use #issue-number [0=Back]: ").strip()
    if choice == "0":
        return None

    if choice.startswith("#") and choice[1:].isdigit():
        issue_number = int(choice[1:])
        return next((card for card in cards if card.issue_number == issue_number), None)

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(cards):
            return cards[idx]

    print("❌ Invalid issue selection")
    return None


def _display_tracked_issue_summary(project: dict):
    records = list_issue_metrics(project["path"])
    if not records:
        print(f"\nℹ️ No tracked issues yet for {project['name']}.")
        return []

    print(f"\n📋 Tracked Issues for {project['name']}")
    print(
        f"{'Idx':<5} {'#':<6} {'Title':<26} {'Pts':<5} {'EstMD':<7} "
        f"{'ActMD':<7} {'Due':<19} {'Effort':<7}"
    )
    print("─" * 96)
    for idx, record in enumerate(records, 1):
        title = (
            record.issue_title[:24] + ".."
            if len(record.issue_title) > 26
            else record.issue_title
        )
        print(
            f"{idx:<5} #{record.issue_number:<5} {title:<26} "
            f"{(record.estimate_points if record.estimate_points is not None else '-'): <5} "
            f"{(record.estimated_mandays if record.estimated_mandays is not None else '-'): <7} "
            f"{(record.actual_mandays if record.actual_mandays is not None else '-'): <7} "
            f"{format_metric_datetime(record.due_date):<19} "
            f"{(record.effort_level or '-'): <7}"
        )
    print("─" * 96)
    print(f"Total tracked: {len(records)}")
    return records


def _select_tracked_issue_record(project: dict):
    records = _display_tracked_issue_summary(project)
    if not records:
        return None

    choice = input("\nSelect index or use #issue-number [0=Back]: ").strip()
    if choice == "0":
        return None

    if choice.startswith("#") and choice[1:].isdigit():
        issue_number = int(choice[1:])
        return next((record for record in records if record.issue_number == issue_number), None)

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(records):
            return records[idx]

    print("❌ Invalid tracked issue selection")
    return None


def _format_metric_value(value):
    if value in (None, ""):
        return "-"
    if isinstance(value, str) and "T" in value:
        return format_metric_datetime(value)
    return str(value)


def _parse_optional_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError("Estimate Points must be an integer.") from exc
    if parsed < 0:
        raise ValueError("Estimate Points must be 0 or greater.")
    return parsed


def _parse_optional_float(value: str, label: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be numeric.") from exc
    if parsed < 0:
        raise ValueError(f"{label} must be 0 or greater.")
    return parsed


def _prompt_metric_value(label: str, current_value, parser):
    while True:
        raw = input(
            f"{label} [{_format_metric_value(current_value)}] "
            "(Enter keep, - clear): "
        ).strip()
        if raw == "":
            return _KEEP_METRIC_VALUE
        if raw == "-":
            return None
        try:
            return parser(raw)
        except ValueError as e:
            print(f"❌ {e}")


def _edit_issue_metrics_record(project: dict, record: IssueMetricsRecord, is_new: bool = False):
    print(f"\n📝 Issue Metrics for #{record.issue_number} - {record.issue_title}")
    print(f"   Project: {project['name']}")
    print(f"   Repository: {record.repository or '-'}")
    print(f"   Status: {record.issue_status or '-'}")
    print("   Press Enter to keep the current value, or '-' to clear it.")

    candidate = IssueMetricsRecord(**asdict(record))
    changed = False

    field_specs = [
        ("estimate_points", "Estimate Points", _parse_optional_int),
        (
            "estimated_mandays",
            "Estimated Mandays",
            lambda value: _parse_optional_float(value, "Estimated Mandays"),
        ),
        (
            "actual_mandays",
            "Actual Mandays",
            lambda value: _parse_optional_float(value, "Actual Mandays"),
        ),
        ("due_date", "Due Date/Time", parse_metric_datetime),
        (
            "actual_completion_date",
            "Actual Completion Date/Time",
            parse_metric_datetime,
        ),
        ("effort_level", f"Effort Level {EFFORT_LEVELS}", validate_effort_level),
        ("notes", "Notes", lambda value: value),
    ]

    for field_name, label, parser in field_specs:
        next_value = _prompt_metric_value(label, getattr(candidate, field_name), parser)
        if next_value is _KEEP_METRIC_VALUE:
            continue
        if getattr(candidate, field_name) != next_value:
            setattr(candidate, field_name, next_value)
            changed = True

    if not changed:
        if is_new:
            print("ℹ️ No tracking values entered. Nothing was saved.")
        else:
            print("ℹ️ No changes saved.")
        return False

    save_issue_metrics(project["path"], candidate)
    print("✅ Issue metrics saved.")
    return True


def _build_issue_metrics_record(project: dict, card: KanbanCard) -> IssueMetricsRecord:
    existing = get_issue_metrics(project["path"], card.repository, card.issue_number)
    if existing:
        existing.issue_title = card.title
        existing.issue_url = card.url
        existing.issue_status = card.status
        existing.project_name = project["name"]
        return existing

    return IssueMetricsRecord(
        issue_key=f"{card.repository}#{card.issue_number}",
        issue_number=card.issue_number,
        issue_title=card.title,
        issue_url=card.url,
        repository=card.repository,
        project_name=project["name"],
        issue_status=card.status,
    )


def action_test_telegram_notification(state: LumaState, project: dict):
    """Test sending a Telegram notification directly from the CLI."""
    from luma_core import ui
    from luma_core.notifier import notify_task_complete
    
    ui.display_header(state, project)
    
    project_name = project["name"] if project else "Luma"
    
    result = notify_task_complete(
        project=project_name,
        task="Test Telegram Notification",
        status="success",
        duration="1s",
        message="🧪 ทดสอบการส่งข้อความจากเมนู Luma CLI"
    )
    
    if result:
        print(f"\n✅ Notification sent successfully!")
    else:
        print(f"\n❌ Failed to send notification (Check AKASA_CHAT_ID or backend config).")
    
    input(f"\nPress Enter to return to menu...")


def action_view_dashboard(state: LumaState, project: dict):
    """Display Usage & Metrics Dashboard in terminal."""
    from luma_core.metrics_summarizer import (
        summarize_usage_stats,
        summarize_issue_metrics,
        format_summary_message,
    )

    usage_path = usage_tracker.get_log_path()
    metrics_path = os.path.join(project["path"], ".luma_metrics.json")

    print("\n" + "╔" + "═" * 52 + "╗")
    print("║  📊 Usage & Metrics Dashboard                      ║")
    print("╠" + "═" * 52 + "╣")

    # Usage Stats (current project)
    usage = summarize_usage_stats(usage_path, project)
    duration_s = (usage.get("total_duration_ms", 0) or 0) / 1000
    if duration_s >= 60:
        mins = int(duration_s // 60)
        secs = int(duration_s % 60)
        dur_str = f"{mins}m {secs}s"
    else:
        dur_str = f"{duration_s:.0f}s"

    print("║                                                    ║")
    print("║  🤖 AI Usage (this project)                        ║")
    print(f"║    Total Calls: {usage['total_calls']:<35}║")
    print(f"║    ✅ Success:  {usage['success_count']:<35}║")
    print(f"║    ❌ Errors:   {usage['error_count']:<35}║")
    print(f"║    ⏱  Duration: {dur_str:<34}║")

    models = usage.get("unique_models", [])
    if models:
        models_str = ", ".join(models[:3])
        if len(models_str) > 34:
            models_str = models_str[:31] + "..."
        print(f"║    🧠 Models:   {models_str:<34}║")

    print("║                                                    ║")

    # Issue Metrics
    metrics = summarize_issue_metrics(metrics_path)
    print("║  📏 Issue Metrics                                  ║")
    print(f"║    Total Issues:    {metrics['total_issues']:<31}║")
    print(f"║    ✅ Done:         {metrics['done_count']:<31}║")
    print(f"║    🔄 In Progress:  {metrics['in_progress_count']:<31}║")
    print(f"║    🔲 Todo:         {metrics['todo_count']:<31}║")
    print(f"║    📊 Total Points: {metrics['total_points']:<31}║")
    est_md = f"{metrics['total_estimated_mandays']:.1f}"
    act_md = f"{metrics['total_actual_mandays']:.1f}"
    print(f"║    📅 Mandays:      Est {est_md} / Act {act_md:<20}║")
    print("║                                                    ║")
    print("╚" + "═" * 52 + "╝")

    input("\nPress Enter to return...")


def action_manage_issue_metrics(state: LumaState, project: dict):
    """Manage per-issue estimates and actuals in .luma_metrics.json files."""
    selected_project = project
    prefill_result = prefill_metrics_from_roadmap(
        selected_project["path"],
        selected_project.get("name"),
        selected_project.get("repo"),
    )
    if prefill_result["created"] or prefill_result["updated"]:
        print(
            "\n🗺️  Prefilled issue metrics from ROADMAP.md "
            f"(created {prefill_result['created']}, updated {prefill_result['updated']})."
        )

    while True:
        print(f"\n📏 Issue Metrics Tracker - {selected_project['name']}")
        print("  [1] List tracked issues")
        print("  [2] Select GitHub issue to view/edit metrics")
        print("  [3] Open tracked issue")
        print("  [0] Back")

        choice = input("\nSelect [0-3]: ").strip()
        if choice == "0":
            return
        if choice == "1":
            _display_tracked_issue_summary(selected_project)
            continue
        if choice == "2":
            card = _select_issue_card_for_metrics(selected_project)
            if card:
                _edit_issue_metrics_record(
                    selected_project,
                    _build_issue_metrics_record(selected_project, card),
                    is_new=get_issue_metrics(
                        selected_project["path"], card.repository, card.issue_number
                    )
                    is None,
                )
            continue
        if choice == "3":
            tracked_record = _select_tracked_issue_record(selected_project)
            if tracked_record:
                _edit_issue_metrics_record(selected_project, tracked_record, is_new=False)
            continue

        print("❌ Invalid selection")


def action_generate_project_report(state: LumaState, project: dict):
    """Generate Weekly/Monthly Project Report."""
    print(f"\n📊 Generate Project Report - {project['name']}")
    print("  [1] Weekly Report (Based on today's week)")
    print("  [2] Monthly Report (Based on today's month)")
    print("  [0] Back")

    choice = input("\nSelect [0-2]: ").strip()
    if choice == "0":
        return
    
    period = "weekly" if choice == "1" else "monthly" if choice == "2" else None
    if not period:
        print("❌ Invalid selection")
        return

    custom_date = input("Enter reference date (YYYY-MM-DD) or press Enter for today: ").strip()
    
    print(f"\n🔄 Syncing metrics from ROADMAP...")
    prefill_result = prefill_metrics_from_roadmap(
        project["path"],
        project.get("name"),
        project.get("repo"),
    )
    if prefill_result["created"] or prefill_result["updated"]:
        print(f"   🗺️  Synced (created {prefill_result['created']}, updated {prefill_result['updated']})")
    
    print(f"🚀 Generating {period} report...")
    try:
        from luma_core.report_generator import generate_report
        import os
        from datetime import date
        
        ref_date = date.fromisoformat(custom_date) if custom_date else date.today()
        report_content = generate_report(project["path"], period=period, reference_date=ref_date)
        
        base_dir = os.path.join(project["path"], "docs", "reports")
        os.makedirs(base_dir, exist_ok=True)
        
        if period == "weekly":
            year, week, _ = ref_date.isocalendar()
            base_name = f"weekly_{year}-W{week:02d}"
        else:
            base_name = f"monthly_{ref_date.strftime('%Y-%m')}"
            
        output_path = os.path.join(base_dir, f"{base_name}.md")
        counter = 1
        while os.path.exists(output_path):
            output_path = os.path.join(base_dir, f"{base_name}({counter}).md")
            counter += 1
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"✅ Report generated successfully at: {output_path}")
        
    except ValueError:
        print("❌ Invalid date format. Please use YYYY-MM-DD.")
    except Exception as e:
        print(f"❌ Failed to generate report: {e}")


def _safe_read_lines(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.readlines()
    except UnicodeDecodeError:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()


def _print_preview(lines, max_lines: int = 200):
    total = len(lines)
    if total == 0:
        print("   (empty file)")
        return

    for line in lines[:max_lines]:
        print(line.rstrip())

    if total > max_lines:
        print(f"\n... ({total - max_lines} more lines)")


def _event_matches_project(event: dict, project: dict) -> bool:
    if not project:
        return True
    if event.get("project_path") and event.get("project_path") == project.get("path"):
        return True
    if event.get("project_name") and event.get("project_name") == project.get("name"):
        return True
    if project.get("repo") and event.get("project_repo") == project.get("repo"):
        return True
    return False


def _load_recent_usage_events(path: str, limit: int = 50, project: dict = None):
    events = deque(maxlen=limit)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if project and not _event_matches_project(event, project):
                    continue
                events.append(event)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"⚠️ Failed to read usage log: {e}")
        return []
    return list(events)


def _format_event_line(event: dict) -> str:
    ts = event.get("ts", "")
    if "T" in ts:
        ts = ts.replace("T", " ")[:19]
    status = event.get("status", "-")
    provider = event.get("provider", "")
    model = event.get("model", "")
    model_desc = "/".join([p for p in [provider, model] if p]) or "-"
    action = event.get("action", "-")
    project = event.get("project_name") or event.get("project_key") or "-"
    return f"{ts} | {status} | {model_desc} | {action} | {project}"


def action_view_stats_files(state: LumaState, project: dict):
    """View AI usage log."""
    usage_path = usage_tracker.get_log_path()

    while True:
        print("\n📊 Usage Log Viewer")
        print("===================")
        print(f"  [1] View .luma_ai_usage.jsonl {'✅' if os.path.exists(usage_path) else '❌'}")
        print("  [2] Show file path")
        print("  [0] Back")

        choice = input("\nSelect [0-2]: ").strip()

        if choice == "0":
            return

        if choice == "1":
            if not os.path.exists(usage_path):
                print("\n❌ .luma_ai_usage.jsonl not found.")
                input("\nPress Enter to return...")
                continue

            print("\n📄 Usage Log View")
            print("  [1] Summary (current project)")
            print("  [2] Summary (all projects)")
            print("  [3] Raw tail (last 50 lines)")
            print("  [0] Back")

            sub = input("\nSelect [0-3]: ").strip()

            if sub == "0":
                continue

            if sub == "1":
                events = _load_recent_usage_events(usage_path, limit=50, project=project)
                if not events:
                    print("\nℹ️ No usage events for this project yet.")
                else:
                    print("\nTS | STATUS | MODEL | ACTION | PROJECT")
                    print("-" * 70)
                    for event in events:
                        print(_format_event_line(event))

            elif sub == "2":
                events = _load_recent_usage_events(usage_path, limit=50, project=None)
                if not events:
                    print("\nℹ️ No usage events yet.")
                else:
                    print("\nTS | STATUS | MODEL | ACTION | PROJECT")
                    print("-" * 70)
                    for event in events:
                        print(_format_event_line(event))

            elif sub == "3":
                tail = deque(maxlen=50)
                try:
                    with open(usage_path, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            tail.append(line.rstrip())
                except Exception as e:
                    print(f"⚠️ Failed to read usage log: {e}")
                    input("\nPress Enter to return...")
                    continue

                print("\nLast 50 lines:")
                print("-" * 70)
                for line in tail:
                    print(line)

            else:
                print("❌ Invalid option")

            input("\nPress Enter to return...")
            continue

        if choice == "2":
            print("\n📁 File Path")
            print(f"  .luma_ai_usage.jsonl: {usage_path}")
            input("\nPress Enter to return...")
            continue

        print("❌ Invalid option")


def action_create_pr(state: LumaState, project: dict, auto_approve: bool = False, target_repos: list = None):
    """Create Pull Request with Pre-flight Checks"""
    # Allow if Coding OR (PR_Pending to sync other repos) OR Preflight (Retry)
    allowed_phases = [
        WorkflowPhase.CODING,
        WorkflowPhase.PR_PENDING,
        WorkflowPhase.PREFLIGHT,
    ]
    if state.phase not in allowed_phases:
        print(f"❌ Cannot create PR in '{state.phase.value}' phase")
        print("💡 Start coding first by selecting an issue")
        return

    if not state.active_issues or not state.active_branch:
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

        override = (
            "y"
            if auto_approve
            else input("⚠️ Force create PR anyways? (y/N): ").strip().lower()
        )
        if override != "y":
            # Revert to CODING
            transition_to(state, WorkflowPhase.CODING)
            return

    if not _confirm_pending_doc_updates_before_pr(state, project, auto_approve=auto_approve):
        transition_to(state, WorkflowPhase.CODING)
        return

    # 3. Ask for Mode if not auto-approved already
    if not auto_approve:
        print("\n🤖 PR Creation Mode:")
        mode = (
            input(
                "   [y] Interactive (Confirm each)\n   [a] Auto-Approve ALL\n   [n] Cancel / Back to Coding\n   Select: "
            )
            .strip()
            .lower()
        )

        if mode == "n":
            print("❌ Operation cancelled.")
            transition_to(state, WorkflowPhase.CODING)
            return

        if mode == "a":
            print("   ✅ Auto-Approve enabled for all repos.")
            auto_approve = True

    # Determine target repos (Multi-Repo Support)
    if target_repos is not None:
        target_projects = target_repos
        if len(target_projects) > 1:
            print("   Mode: Multi-Repo (JarWise) - Using explicitly selected repos...")
    else:
        target_projects = [project]
        if project.get("type") == "monorepo_root" and project.get("sibling_repos"):
            print("   Mode: Multi-Repo (JarWise) - Checking all repos...")
            try:
                for sibling_key in project.get("sibling_repos", []):
                    if sibling_key in PROJECTS:
                        target_projects.append(PROJECTS[sibling_key])
            except Exception:
                pass

    # --- SCREENSHOT LOGIC ---
    screenshot_md = ""
    feature_dir = state.context.get("last_feature_dir")
    screenshots_to_sync = []
    
    created_prs = []

    if feature_dir:
        sc_dir = os.path.join(feature_dir, "screenshots")
        if os.path.exists(sc_dir):
            files = [
                f
                for f in os.listdir(sc_dir)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
            ]
            if files:
                print(f"   📸 Found {len(files)} screenshots to attach...")
                for f in files:
                    screenshots_to_sync.append(os.path.join(sc_dir, f))

    for proj in target_projects:
        print(f"\n🚀 Processing {proj['name']}...")

        # Check if this repo is on the correct branch or has relevant changes
        # Simple check: Is current branch == active_branch?
        import subprocess

        try:
            br_res = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=proj["path"],
                capture_output=True,
                text=True,
            )
            curr_br = br_res.stdout.strip()
            if curr_br != state.active_branch:
                print(
                    f"   ⏩ Skipping {proj['name']} (Branch mismatch: {curr_br} != {state.active_branch})"
                )
                continue

            # Check for commits ahead of main
            commits_res = subprocess.run(
                ["git", "rev-list", "--count", "origin/main..HEAD"],
                cwd=proj["path"],
                capture_output=True,
                text=True,
            )
            commits_ahead = int(commits_res.stdout.strip() or "0")

            if commits_ahead == 0:
                print(f"   ⏩ Skipping {proj['name']} (No commits ahead of main)")
                continue

        except Exception as e:
            print(f"   ⚠️ Error checking repo {proj['name']}: {e}")
            continue

        # Check for existing PR
        from luma_core.github_client import get_open_pr

        repo_name = proj.get("repo")
        if repo_name:
            existing = get_open_pr(repo_name, state.active_branch)
            if existing:
                print(
                    f"   ⏩ Skipping {proj['name']} (PR already exists: {existing['html_url']})"
                )
                continue

        # --- SYNC SCREENSHOTS TO TARGET REPO ---
        repo_screenshot_section = ""
        ai_brain_section = ""
        if screenshots_to_sync:
            try:
                # 1. Create docs/screenshots/issue-N/ in target repo
                issue_id = state.active_issue.number
                target_sc_dir = os.path.join(
                    proj["path"], "docs", "screenshots", f"issue-{issue_id}"
                )
                os.makedirs(target_sc_dir, exist_ok=True)

                repo_screenshot_section = "\n\n## 📸 Screenshots\n"

                import shutil

                git_add_files = []

                for src_path in screenshots_to_sync:
                    filename = os.path.basename(src_path)
                    dst_path = os.path.join(target_sc_dir, filename)

                    if not os.path.exists(dst_path) or os.path.getsize(
                        src_path
                    ) != os.path.getsize(dst_path):
                        shutil.copy2(src_path, dst_path)
                        print(f"      - Copied {filename} to {proj['name']}")

                    # Relative path for file operation
                    rel_path = f"docs/screenshots/issue-{issue_id}/{filename}"
                    git_add_files.append(rel_path)

                    # Markdown Link for PR Body (Must use Raw URL for new files to render in PR description)
                    # format: https://raw.githubusercontent.com/{owner_repo}/{branch}/{path}
                    if proj.get("repo") and state.active_branch:
                        raw_url = f"https://raw.githubusercontent.com/{proj['repo']}/{state.active_branch}/{rel_path}"
                        # Encoding spaces just in case, though filenames likely safe
                        from urllib.parse import quote

                        # We only encode the path part if needed, but simple f-string is usually fine for strict filenames
                        repo_screenshot_section += f"![{filename}]({raw_url})\n"
                    else:
                        # Fallback if repo info missing
                        repo_screenshot_section += f"![{filename}]({rel_path})\n"

                # 2. Git Add the screenshots
                if git_add_files:
                    subprocess.run(
                        ["git", "add"] + git_add_files, cwd=proj["path"], check=False
                    )
                    subprocess.run(
                        ["git", "commit", "-m", "docs: add screenshots"],
                        cwd=proj["path"],
                        check=False,
                        capture_output=True,
                    )

            except Exception as e:
                print(f"   ⚠️ Failed to sync screenshots: {e}")

        # --- SYNC AI BRAIN ARTIFACTS ---
        try:
            from luma_core.ai_brain_sync import AntigravityBrain

            print("   🔄 Syncing AI Agent Brain Artifacts...")
            brain_session = state.context.get("selected_brain_session")
            synced_docs = AntigravityBrain.sync_to_repo(
                proj["path"], state.active_issue.number, session_path=brain_session
            )

            if synced_docs:
                subprocess.run(
                    ["git", "add"] + synced_docs, cwd=proj["path"], check=False
                )
                subprocess.run(
                    ["git", "commit", "-m", "docs: sync AI brain artifacts"],
                    cwd=proj["path"],
                    check=False,
                    capture_output=True,
                )
                print(f"   ✅ Merged AI Brain Context to {proj['name']}")

                ai_brain_section = "\n\n## 🧠 AI Brain Context\n"
                for doc in synced_docs:
                    filename = os.path.basename(doc)
                    if proj.get("repo") and state.active_branch:
                        raw_url = f"https://raw.githubusercontent.com/{proj['repo']}/{state.active_branch}/{doc}"
                        ai_brain_section += f"- [{filename}]({raw_url})\n"
                    else:
                        ai_brain_section += f"- [{filename}]({doc})\n"
        except Exception as e:
            print(f"   ⚠️ Failed to sync AI brain artifacts: {e}")

        # 3. Proceed to Create PR for this repo
        if not auto_approve:
            confirm = (
                input(f"   ✨ Create PR for {proj['name']}? (Y/n): ").strip().lower()
            )
            if confirm == "n":
                continue

        print(f"   ✨ Creating PR for {proj['name']}...")

        # Construct a temporary state for the publisher
        # Append screenshots and AI brain context to body
        # Multi-issue: combine all issue bodies + closing references
        primary_issue = state.active_issue

        if len(state.active_issues) > 1:
            closes_line = ", ".join(f"Closes #{i.number}" for i in state.active_issues)
            issues_section = "\n\n## Issues\n" + "\n".join(
                f"- #{i.number}: {i.title}" for i in state.active_issues
            )
            combined_body = (
                (primary_issue.body or "")
                + issues_section
                + repo_screenshot_section
                + ai_brain_section
            )
            pr_title = f"{primary_issue.title} (#{', #'.join(str(i.number) for i in state.active_issues)})"
        else:
            closes_line = f"Closes #{primary_issue.number}"
            combined_body = (
                (primary_issue.body or "") + repo_screenshot_section + ai_brain_section
            )
            pr_title = primary_issue.title

        # Add closes line at the end
        combined_body += f"\n\n{closes_line}"

        pub_state = {
            "task": pr_title,
            "issue_data": {
                "title": pr_title,
                "number": primary_issue.number,
                "body": combined_body,
                "url": getattr(
                    primary_issue,
                    "html_url",
                    f"https://github.com/{project['repo']}/issues/{primary_issue.number}",
                ),
            },
            "repo": proj["repo"],
            "issue_source_repo": project["repo"],
            "target_dir": proj["path"],
            "test_suggestions": "",
            "auto_approve": auto_approve,
        }

        print(f"   📤 Invoking Publisher Agent for {proj['name']}...")
        result = publisher_agent(pub_state)
        pr_url = result.get("pr_url")

        if pr_url:
            print(f"   ✅ PR Created: {pr_url}")
            created_prs.append((proj["name"], pr_url))
            # Update state with the created PR url
            if proj == project:
                ok, msg = transition_to(state, WorkflowPhase.PR_PENDING, pr_url=pr_url)
                if ok:
                    print("   🔄 State updated to PR_PENDING")
        else:
            print(f"   ⚠️ Publisher finished but no known PR URL.")

    if created_prs:
        print("\n📋 PR Summary:")
        for name, url in created_prs:
            print(f"  ✅ {name:<20} → {url}")


def action_sync_ai_brain(state: LumaState, project: dict) -> bool:
    """Manually trigger AI Brain Sync with preview + confirm + session picker. Supports Antigravity and Gemini CLI."""
    if not state.active_issue:
        print("❌ No active issue selected. Please select an issue first.")
        return False

    print(f"\n🧠 Syncing AI Agent Brain Artifacts for {project['name']}...")
    all_synced_docs = []

    # 1. Try Antigravity Brain
    try:
        from luma_core.ai_brain_sync import AntigravityBrain, GeminiCLIBrain

        sessions = AntigravityBrain.get_all_sessions()
        if sessions:
            # Preview latest session
            latest = sessions[0]
            print(
                f"\n   📂 [Antigravity] Latest Session: {latest['session_id'][:12]}..."
            )
            print(f"   📄 Preview: {latest['preview']}")

            confirm = (
                input("\n   ✅ Use this Antigravity session? (Y/n/s to skip): ")
                .strip()
                .lower()
            )

            if confirm != "s":
                selected_path = latest["path"]

                if confirm == "n":
                    # Show session picker
                    print(f"\n   📋 Available Antigravity Sessions:")
                    display_limit = min(8, len(sessions))
                    for i, s in enumerate(sessions[:display_limit]):
                        print(
                            f"   [{i + 1}] {s['session_id'][:12]}... — {s['preview'][:50]}"
                        )

                    choice = (
                        input(
                            f"\n   Select session [1-{display_limit}] or [c] Cancel: "
                        )
                        .strip()
                        .lower()
                    )
                    if choice != "c" and choice:
                        try:
                            idx = int(choice) - 1
                            if 0 <= idx < display_limit:
                                selected_path = sessions[idx]["path"]
                                print(
                                    f"   🔗 Selected: {sessions[idx]['session_id'][:12]}..."
                                )
                                synced_antigravity = AntigravityBrain.sync_to_repo(
                                    project["path"],
                                    state.active_issue.number,
                                    session_path=selected_path,
                                )
                                all_synced_docs.extend(synced_antigravity)
                                state.context["selected_brain_session"] = selected_path
                        except ValueError:
                            pass
                else:
                    synced_antigravity = AntigravityBrain.sync_to_repo(
                        project["path"],
                        state.active_issue.number,
                        session_path=selected_path,
                    )
                    all_synced_docs.extend(synced_antigravity)
                    state.context["selected_brain_session"] = selected_path
        else:
            print("ℹ️ No Antigravity sessions found.")

    except Exception as e:
        print(f"⚠️ Antigravity sync failed: {e}")

    # 2. Try Gemini CLI Brain
    try:
        from luma_core.ai_brain_sync import GeminiCLIBrain

        print("\n   🔍 Checking Gemini CLI session artifacts...")

        gemini_sessions = GeminiCLIBrain.get_all_sessions()
        if gemini_sessions:
            latest = gemini_sessions[0]
            print(
                f"\n   📂 [Gemini CLI] Latest Session: {latest['session_id'][:12]}..."
            )
            print(f"   📄 Preview: {latest['preview'][:80]}")

            confirm = (
                input("\n   ✅ Sync this Gemini CLI session? (Y/n/s to skip): ")
                .strip()
                .lower()
            )

            if confirm != "s":
                selected_path = latest["path"]

                if confirm == "n":
                    # Show session picker
                    print(f"\n   📋 Available Gemini CLI Sessions:")
                    display_limit = min(8, len(gemini_sessions))
                    for i, s in enumerate(gemini_sessions[:display_limit]):
                        print(
                            f"   [{i + 1}] {s['session_id'][:12]}... — {s['preview'][:60]}"
                        )

                    choice = (
                        input(
                            f"\n   Select session [1-{display_limit}] or [c] Cancel: "
                        )
                        .strip()
                        .lower()
                    )
                    if choice != "c" and choice:
                        try:
                            idx = int(choice) - 1
                            if 0 <= idx < display_limit:
                                selected_path = gemini_sessions[idx]["path"]
                                print(
                                    f"   🔗 Selected: {gemini_sessions[idx]['session_id'][:12]}..."
                                )
                                synced_gemini = GeminiCLIBrain.sync_to_repo(
                                    project["path"],
                                    state.active_issue.number,
                                    session_path=selected_path,
                                )
                                all_synced_docs.extend(synced_gemini)
                        except ValueError:
                            pass
                else:
                    synced_gemini = GeminiCLIBrain.sync_to_repo(
                        project["path"],
                        state.active_issue.number,
                        session_path=selected_path,
                    )
                    all_synced_docs.extend(synced_gemini)
        else:
            print("   ℹ️ No Gemini CLI session artifacts found.")
    except Exception as e:
        print(f"⚠️ Gemini CLI sync failed: {e}")

    if all_synced_docs:
        print(
            f"\n✅ Successfully synced {len(all_synced_docs)} files from AI Brain(s)."
        )
        for doc in all_synced_docs:
            print(f"  - {doc}")
        print(
            f"💡 The files have been copied to the project. You can review and commit them manually."
        )
        return True
    else:
        print("\n⚠️ No new artifacts to sync (content unchanged or no sources found).")
        return False


def action_code_review(state: LumaState, project: dict):
    """Run local code review agent"""
    print(f"\n🧐 Local Code Reviewer")

    # Determine target repos (Multi-Repo Support)
    potential_projects = [project]
    if project.get("type") == "monorepo_root" and project.get("sibling_repos"):
        try:
            for sibling_key in project.get("sibling_repos", []):
                if str(sibling_key) in PROJECTS:
                    potential_projects.append(PROJECTS[str(sibling_key)])
        except Exception:
            pass

    target_projects = []
    if len(potential_projects) > 1:
        print("\n   Select repositories to review (e.g., 1, 2 or 'all'):")
        for i, proj in enumerate(potential_projects, 1):
            print(f"   [{i}] {proj['name']} ({proj.get('type', 'unknown')})")

        choice = input("\n   Select [all]: ").strip().lower()
        if not choice or choice == "all":
            target_projects = potential_projects
        else:
            try:
                indices = [int(i.strip()) - 1 for i in choice.split(",") if i.strip()]
                for idx in indices:
                    if 0 <= idx < len(potential_projects):
                        target_projects.append(potential_projects[idx])
            except ValueError:
                print("   ⚠️ Invalid input. Reviewing all repositories.")
                target_projects = potential_projects
    else:
        target_projects = potential_projects

    if not target_projects:
        print("   ❌ No repositories selected.")
        return

    for proj in target_projects:
        print(f"\n🚀 Reviewing {proj['name']}...")
        target_dir = proj["path"]

        # 1. Get changed files
        try:
            import subprocess

            from luma_core.agents.reviewer import reviewer_agent

            file_list = get_git_changed_files("all", target_dir=target_dir)
            if not file_list:
                print(f"   ✅ {proj['name']}: No changes found (Clean vs origin/main).")
                continue

            print(f"   🔎 Found {len(file_list)} changed files in {proj['name']}.")
            # Limit files
            if len(file_list) > 30:
                print(f"   ⚠️ Too many files ({len(file_list)}). Reviewing top 10.")
                file_list = file_list[:10]

            changes = {}
            for rel_path in file_list:
                full_path = os.path.join(target_dir, rel_path)
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    # Skip binary/large files heuristic
                    if rel_path.endswith((".png", ".jpg", ".ico", ".pdf", ".jar")):
                        continue
                    try:
                        # 1. Try to get diff against origin/main (includes local commits)
                        diff_cmd = ["git", "diff", "origin/main", "--", rel_path]
                        diff_res = subprocess.run(
                            diff_cmd, cwd=target_dir, capture_output=True, text=True
                        )

                        if diff_res.returncode == 0 and diff_res.stdout.strip():
                            changes[rel_path] = diff_res.stdout.strip()
                        else:
                            # 2. If no origin/main diff, try just checking uncommitted changes
                            diff_cmd = ["git", "diff", "HEAD", "--", rel_path]
                            diff_res = subprocess.run(
                                diff_cmd, cwd=target_dir, capture_output=True, text=True
                            )

                            if diff_res.returncode == 0 and diff_res.stdout.strip():
                                changes[rel_path] = diff_res.stdout.strip()
                            else:
                                # 3. Fallback to reading the full file if it's untracked or we can't get diff
                                with open(full_path, "r", encoding="utf-8") as f:
                                    changes[rel_path] = f.read()
                    except:
                        pass

            if not changes:
                print("   ❌ No readable content to review.")
                continue

            # 2. Run Reviewer
            print(f"   🚀 Running Reviewer on {list(changes.keys())}...")

            review_state = {
                "task": "Review local code changes for bugs, security issues, and best practices.",
                "changes": changes,
                "iterations": 0,
                "test_errors": "",
                "skip_coder": False,
            }

            result = reviewer_agent(review_state)

            if result.get("code_content"):
                print("\n   📝 Reviewer Feedback:")
                print("   --------------------------------------------------")
                print(result["code_content"])
                print("   --------------------------------------------------")

            if result.get("test_suggestions"):
                print("\n   🧪 Test Suggestions:")
                print(result["test_suggestions"])

            # Save to file
            report_path = os.path.join(target_dir, "code_review.md")
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write("# Luma Code Review Report\n\n")
                    f.write(
                        f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    f.write(f"**Files Reviewed:** {list(changes.keys())}\n\n")

                    if result.get("code_content"):
                        f.write("## 📝 Reviewer Feedback\n\n")
                        f.write(result["code_content"] + "\n\n")

                    if result.get("test_suggestions"):
                        f.write("## 🧪 Test Suggestions\n\n")
                        f.write(result["test_suggestions"] + "\n\n")
                print(f"\n   ✅ Review Report saved to: {report_path}")

                # Append the raw prompt to draft_code_review.md if available
                if result.get("prompt_used"):
                    draft_path = os.path.join(target_dir, "draft_code_review.md")
                    try:
                        with open(draft_path, "a", encoding="utf-8") as f:
                            f.write(
                                "\n\n---\n\n## 🤖 Prompt Used by Reviewer\n\n```text\n"
                            )
                            f.write(result["prompt_used"])
                            f.write("\n```\n")
                        print(f"   ✅ Appended review prompt to: {draft_path}")
                    except Exception as e:
                        print(f"   ⚠️ Could not append prompt to {draft_path}: {e}")

            except Exception as e:
                print(f"\n   ⚠️ Failed to save report: {e}")

            print(f"\n   ✅ Review Complete for {proj['name']}.")

            # Print the prompt for the user to copy and paste to the AI assistant
            print("\n" + "=" * 60)
            print("💡 COPY THIS PROMPT FOR THE AI ASSISTANT:")
            print("=" * 60)
            prompt_text = _build_code_review_followup_prompt(
                multi_repo=len(target_projects) > 1
            )
            print(prompt_text)
            print("=" * 60)

            prompt_path = os.path.join(target_dir, "code_review_prompt.txt")
            try:
                with open(prompt_path, "w", encoding="utf-8") as f:
                    f.write(prompt_text)
                print(f"\n   📝 Prompt saved to: {prompt_path}")
            except Exception as e:
                print(f"\n   ⚠️ Failed to save prompt: {e}")

            print("\n" + "🧪" * 10 + " ต้อง RE-MANUAL VERIFY อย่างไร " + "🧪" * 10)

        except Exception as e:
            print(f"   ❌ Error during code review for {proj['name']}: {e}")


def _confirm_pending_doc_updates_before_pr(
    state: LumaState, project: dict, auto_approve: bool = False
) -> bool:
    status = refresh_pending_doc_updates(state, project)
    summary = pending_doc_update_summary(status)
    if not summary:
        return True

    print("\n⚠️ Pending docs/version updates detected before PR.")
    print(f"   Missing: {summary}")

    if auto_approve:
        print("   ℹ️ Auto-Approve mode: continuing without forcing docs update.")
        return True

    choice = (
        input(
            "   [u] Update now\n"
            "   [c] Continue anyway\n"
            "   [b] Back to Coding\n"
            "   Select (Default=u): "
        )
        .strip()
        .lower()
    )

    if choice in ("", "u"):
        action_update_docs(state, project, skip_confirm=True)
        status = refresh_pending_doc_updates(state, project)
        summary = pending_doc_update_summary(status)
        if not summary:
            return True

        print(f"   ⚠️ Still pending after docs update: {summary}")
        return input("   Continue PR anyway? (y/N): ").strip().lower() == "y"

    if choice == "c":
        return True

    print("⏳ Back to Coding so you can keep refining before the docs/version update.")
    return False


def action_update_docs(state: LumaState, project: dict, skip_confirm: bool = False):
    """Update documentation (Changelog, Version, README)"""
    print("\n📝 Documentation Update")
    print(f"   Project: {project['name']}")

    # 1. Determine Scope (Single vs Multi-Repo)
    # Check for explicit multi-repo flag in project config
    is_multi_repo = project.get("type") == "monorepo_root"
    target_repos = [project]

    if is_multi_repo:
        print("   Mode: Multi-Repo (JarWise)")
        # Dynamically load sibling repos
        all_candidates = [project]
        try:
            for sibling_key in project.get("sibling_repos", []):
                # Ensure key is string
                if str(sibling_key) in PROJECTS:
                    all_candidates.append(PROJECTS[str(sibling_key)])
                else:
                    print(f"   ⚠️ Sibling key '{sibling_key}' not found in PROJECTS config.")
        except Exception as e:
            print(f"⚠️ Failed to load sibling repos: {e}")
            import traceback

            traceback.print_exc()
            
        if not skip_confirm:
            print("\n   📦 Select projects to update docs:")
            for idx, cand in enumerate(all_candidates, 1):
                print(f"      [{idx}] {cand['name']}")
            print("      [a] All (Default)")

            selected = input("\n   Select indices (e.g., 1,3) or 'a' for all: ").strip().lower()
            if selected and selected != 'a':
                target_repos = []
                for s in selected.split(','):
                    s = s.strip()
                    if s.isdigit():
                        idx = int(s) - 1
                        if 0 <= idx < len(all_candidates):
                            target_repos.append(all_candidates[idx])
                if not target_repos:
                    print("   ⚠️ No valid projects selected. Defaulting to 'All'.")
                    target_repos = all_candidates
            else:
                target_repos = all_candidates
        else:
            target_repos = all_candidates

    print("\n🚀 Ready to update:")
    for repo in target_repos:
        print(f"   - {repo['name']}")

    if not skip_confirm:
        confirm = input("\nProceed with docs update? (y/N): ").lower()
        if confirm != "y":
            return []

    # 2. Run Update
    print("\n⏳ Updating docs (AI-powered)...")
    results = update_multi_repo_docs(target_repos, docs_agent_func=None)

    # 3. Summary
    print("\n" + "=" * 40)
    print("📊 Docs Update Summary:")
    print("=" * 40)

    for r in results:
        status = "✅" if r.get("success") else "⏩"
        msg = (
            ", ".join(r.get("files_updated", []))
            if r.get("success")
            else r.get("error")
        )
        print(f"   {status} {r['name']}: {msg}")

    print("\n✅ Done.")
    refresh_pending_doc_updates(state, project)
    return results


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

    # Combine properties if multiple issues
    issues = state.active_issues
    combined_title = " & ".join([issue.title for issue in issues])
    combined_number = "-".join([str(issue.number) for issue in issues])
    combined_body = "\n\n---\n\n".join(
        [f"### Issue #{issue.number}\n{issue.body or ''}" for issue in issues]
    )

    # Create temporary state
    analyst_state = {
        "task": combined_title,
        "issue_data": {
            "title": combined_title,
            "number": combined_number,
            "body": combined_body,
        },
        "target_dir": project["path"],
    }

    print("\n🧠 Invoking Analyst Agent...")
    result = analyst_agent(analyst_state)

    if result.get("analysis_file"):
        print(f"\n✨ Analysis complete! Document saved to: {result['analysis_file']}")
    else:
        print("\n⚠️ Analysis failed or produced no output.")


def action_switch_project(state: LumaState) -> str:
    """Switch to different project"""
    # Collect all sibling repo keys to hide from menu
    sibling_keys = set()
    for key, proj in PROJECTS.items():
        for sib_key in proj.get("sibling_repos", []):
            sibling_keys.add(str(sib_key))

    print("\n🔀 Select Project:")
    for key, proj in PROJECTS.items():
        if key in sibling_keys:
            continue  # Hide sibling repos from menu
        print(f"  [{key}] {proj['name']}")

    print("  [+] Add New Project")

    choice = input("\nSelect: ").strip()

    if choice == "+":
        return _add_new_project(state)

    if choice in PROJECTS:
        return choice

    return None


def _add_new_project(state: LumaState) -> str:
    """Interactively add a new project and save it to config"""
    print("\n✨ Add New Project")
    print("=================")

    name = input("Project Name: ").strip()
    if not name:
        print("❌ Project Name is required.")
        return None

    path = input("Absolute Path to Project: ").strip()
    if not path or not os.path.isabs(path):
        print("❌ Absolute Path is required.")
        return None

    repo = input("GitHub Repo (e.g. oatrice/Akasa) [Optional]: ").strip()
    kanban_number_str = input("GitHub Project Board Number [Optional]: ").strip()

    # Generate a unique key based on auto-incrementing existing numeric keys
    max_key = 0
    for key in PROJECTS.keys():
        try:
            val = int(key)
            # Ignore previously generated timestamp keys (Unix timestamps are ~1.7B)
            # so we only auto-increment from standard project id sequences.
            if val < 1000000:
                max_key = max(max_key, val)
        except ValueError:
            pass

    new_key = str(max_key + 1)

    new_project = normalize_project_entry({
        "name": name,
        "path": path,
        "repo": repo if repo else "",
        "kanban_number": int(kanban_number_str) if kanban_number_str.isdigit() else 1,
        "kanban_id": "",  # Cannot easily infer this via CLI right now
    })

    # 1. Add to current session runtime
    PROJECTS[new_key] = new_project

    # 2. Save to global config
    import json

    from luma_core.config import GLOBAL_CONFIG_FILE

    try:
        current_config = {}
        if os.path.exists(GLOBAL_CONFIG_FILE):
            with open(GLOBAL_CONFIG_FILE, "r") as f:
                current_config = json.load(f)

        if "custom_projects" not in current_config:
            current_config["custom_projects"] = {}

        current_config["custom_projects"][new_key] = new_project

        with open(GLOBAL_CONFIG_FILE, "w") as f:
            json.dump(current_config, f, indent=2)

        print(f"\n✅ Project '{name}' added successfully!")
        return new_key
    except Exception as e:
        print(f"\n❌ Failed to save project: {e}")
        return None


def action_settings():
    """Settings menu to configure LLM Provider, Agent CLI, and Gemini CLI Model"""
    import json
    import os

    from luma_core.config import (
        AGENT_CLI,
        AVAILABLE_GEMINI_CLI_MODELS,
        GEMINI_CLI_MODEL,
        GLOBAL_CONFIG_FILE,
        LLM_PROVIDER,
        save_gemini_cli_model,
    )

    print("\n⚙️  Settings")
    print("==========")

    # Load current config
    current_config = {}
    if os.path.exists(GLOBAL_CONFIG_FILE):
        try:
            with open(GLOBAL_CONFIG_FILE, "r") as f:
                current_config = json.load(f)
        except Exception:
            pass

    current_llm = current_config.get("LLM_PROVIDER", LLM_PROVIDER)
    current_cli = current_config.get("AGENT_CLI", AGENT_CLI)
    current_model = current_config.get("GEMINI_CLI_MODEL", GEMINI_CLI_MODEL)

    while True:
        print(f"\nCurrent Configuration:")
        print(f"  [1] LLM Provider:      {current_llm}")
        print(f"  [2] Agent CLI:         {current_cli}")
        print(f"  [3] Gemini CLI Model:  {current_model}")
        print(f"  [4] 🔙 Back")

        choice = input("\nSelect setting to change [1-4]: ").strip()

        if choice == "1":
            print("\nSelect LLM Provider:")
            print("  [1] gemini (API)")
            print("  [2] openrouter")
            print("  [3] gemini_cli (Local CLI)")

            p_choice = input("Select [1-3]: ").strip()
            if p_choice == "1":
                current_llm = "gemini"
            elif p_choice == "2":
                current_llm = "openrouter"
            elif p_choice == "3":
                current_llm = "gemini_cli"

        elif choice == "2":
            print("\nSelect Agent CLI:")
            print("  [1] gemini_cli")
            print("  [2] opencode")

            c_choice = input("Select [1-2]: ").strip()
            if c_choice == "1":
                current_cli = "gemini_cli"
            elif c_choice == "2":
                current_cli = "opencode"

        elif choice == "3":
            print("\nSelect Gemini CLI Model:")
            for i, model in enumerate(AVAILABLE_GEMINI_CLI_MODELS, 1):
                marker = " ← current" if model == current_model else ""
                print(f"  [{i}] {model}{marker}")

            m_choice = input(f"Select [1-{len(AVAILABLE_GEMINI_CLI_MODELS)}]: ").strip()
            try:
                idx = int(m_choice) - 1
                if 0 <= idx < len(AVAILABLE_GEMINI_CLI_MODELS):
                    current_model = AVAILABLE_GEMINI_CLI_MODELS[idx]
                    save_gemini_cli_model(current_model)
                    print(f"  ✅ Model set to: {current_model}")
                else:
                    print("❌ Invalid option")
            except ValueError:
                print("❌ Invalid option")

        elif choice == "4" or choice == "":
            break
        else:
            print("❌ Invalid option")

    # Save back to config
    current_config["LLM_PROVIDER"] = current_llm
    current_config["AGENT_CLI"] = current_cli

    try:
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            json.dump(current_config, f, indent=2)

        # Hot-reload config module so get_llm picks up the change immediately
        import importlib

        import luma_core.config

        importlib.reload(luma_core.config)

        print("\n✅ Settings saved!")
    except Exception as e:
        print(f"\n❌ Failed to save settings: {e}")


def action_generate_sbe(state: LumaState, project: dict):
    """Generate SBE (Specification by Example) for current issue"""
    if not state.active_issue:
        print("❌ No active issue selected.")
        print("💡 Select an issue first (Menu option 2)")
        return

    print("\n📋 SBE (Specification by Example) Generator")
    print(f"   Issue: #{state.active_issue.number} {state.active_issue.title}")

    # Enable SBE Agent
    try:
        from luma_core.agents.sbe_agent import sbe_agent
    except ImportError as e:
        print(f"❌ SBE agent not available: {e}")
        return

    # Combine properties if multiple issues
    issues = state.active_issues
    combined_title = " & ".join([issue.title for issue in issues])
    combined_number = "-".join([str(issue.number) for issue in issues])
    combined_body = "\n\n---\n\n".join(
        [f"### Issue #{issue.number}\n{issue.body or ''}" for issue in issues]
    )

    first_issue = issues[0]

    # Create state for SBE agent
    sbe_state = {
        "task": combined_title,
        "issue_data": {
            "title": combined_title,
            "number": combined_number,
            "body": combined_body,
            "url": getattr(first_issue, "html_url", ""),
            "repository": getattr(first_issue, "repository", ""),
        },
        "target_dir": project["path"],
    }

    print("\n🤖 Invoking SBE Agent (Integration -> Spec Agent)...")
    # Redirect legacy SBE to new Spec Agent if possible, or keep separate for now.
    # For now, let's keep SBE as a sub-feature, but we encourage using the full Spec Agent.
    result = sbe_agent(sbe_state)

    if result.get("sbe_file"):
        print(f"\n✨ SBE Specification created!")
        print(f"   📁 File: {result['sbe_file']}")

        # Preview first few lines
        try:
            with open(result["sbe_file"], "r") as f:
                lines = f.readlines()[:15]
                print("\n📄 Preview:")
                print("-" * 50)
                for line in lines:
                    print(line.rstrip())
                if len(lines) >= 15:
                    print("...")
                print("-" * 50)
        except:
            pass
    else:
        print("\n⚠️ SBE generation failed or produced no output.")


def action_generate_draft(state: LumaState, project: dict):
    """Generate draft_code_review.md with full diff context"""
    print("\n📊 Generating Draft Code Review...")

    try:
        output_path = generate_draft_code_review(project["path"])
        print(f"\n✅ Draft saved to: {output_path}")
        print("   💡 This file can be used for PR creation and code review.")
        print("   📋 Publisher Agent will automatically use this file if present.")

        # Open in VS Code
        import subprocess

        try:
            subprocess.run(["code", output_path], capture_output=True)
            print("   📂 Opened in VS Code")
        except:
            pass

    except Exception as e:
        print(f"\n❌ Failed to generate draft: {e}")


def action_generate_spec(state: LumaState, project: dict):
    """Generate spec.md using Spec Agent"""
    if not state.active_issue:
        print("❌ No active issue selected.")
        return

    # Enable Spec Agent
    try:
        from luma_core.agents.spec_agent import spec_agent
    except ImportError as e:
        print(f"❌ Spec agent not available: {e}")
        return

    # Combine properties if multiple issues
    issues = state.active_issues
    combined_title = " & ".join([issue.title for issue in issues])
    combined_number = "-".join([str(issue.number) for issue in issues])
    combined_body = "\n\n---\n\n".join(
        [f"### Issue #{issue.number}\n{issue.body or ''}" for issue in issues]
    )

    # Use the first issue's URL and repository for simplicity
    first_issue = issues[0]

    # Create State
    spec_state = {
        "task": combined_title,
        "issue_data": {
            "title": combined_title,
            "number": combined_number,
            "body": combined_body,
            "url": getattr(first_issue, "html_url", ""),
            "repository": getattr(first_issue, "repository", ""),
        },
        "target_dir": project["path"],
    }

    print("\n🧬 Invoking Spec Agent (Spec Kit)...")
    result = spec_agent(spec_state)

    if result.get("feature_dir"):
        # Update state with feature dir for subsequent steps
        # In a real app, we might want to persist this in LumaState
        print(f"   📂 Feature Directory: {result['feature_dir']}")

        # Determine relative path for display
        rel_path = os.path.relpath(result["feature_dir"], project["path"])
        # Store in state for Plan Agent to use immediately
        state.context["last_feature_dir"] = result["feature_dir"]
        print(f"   💡 Tip: Now you can generate the Plan (Menu Option 'P').")

    # Chain SBE Generation
    print("\n------------------------------------------------")
    # Chain SBE Generation
    print("\n------------------------------------------------")
    print("📋 Auto-generating Specification by Example (SBE)...")
    action_generate_sbe(state, project)


def action_generate_plan(state: LumaState, project: dict):
    """Generate plan.md using Architect Agent"""
    # Try to find feature dir: 1. From context, 2. Ask user
    feature_dir = state.context.get("last_feature_dir")

    if not feature_dir:
        # Simple heuristic: Look for valid feature dirs in docs/features
        # and ask user to pick
        features_root = os.path.join(project["path"], "docs", "features")
        if not os.path.exists(features_root):
            print("❌ No features directory found.")
            return

        dirs = [
            d
            for d in os.listdir(features_root)
            if os.path.isdir(os.path.join(features_root, d))
        ]
        if not dirs:
            print("❌ No feature directories found.")
            return

        print("\n📂 Select Feature to Plan:")
        for i, d in enumerate(dirs, 1):
            print(f"  [{i}] {d}")

        choice = input("Select: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(dirs):
                feature_dir = os.path.join(features_root, dirs[idx])
            else:
                return
        except:
            return

    # Enable Architect Agent
    try:
        from luma_core.agents.architect_agent import architect_agent
    except ImportError as e:
        print(f"❌ Architect agent not available: {e}")
        return

    # Create State
    plan_state = {"feature_dir": feature_dir, "target_dir": project["path"]}

    print("\n🏗️ Invoking Architect Agent...")
    result = architect_agent(plan_state)

    if result.get("plan_file"):
        print(f"\n✨ Plan created at: {result['plan_file']}")


def action_update_roadmap(state: LumaState, project: dict):  # PATCHED: multi-issue support
    """Update ROADMAP.md status for one or more issues (supports comma-separated input)."""
    print(f"\n🗺️  Updating Roadmap for {project['name']}...")

    # Locate ROADMAP.md
    roadmap_paths = [
        os.path.join(project["path"], "docs", "ROADMAP.md"),
        os.path.join(project["path"], "ROADMAP.md"),
    ]
    roadmap_path = next((p for p in roadmap_paths if os.path.exists(p)), None)

    if not roadmap_path:
        print("❌ Roadmap not found in docs/ or root.")
        return

    try:
        with open(roadmap_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Failed to read roadmap: {e}")
        return

    # ── Input: รองรับ single ("65") หรือ comma/space-separated ("33, 34", "33 34") ──
    issue_input = input("Enter Issue # to update (e.g. 65 or 33, 34): ").strip()
    if not issue_input:
        return

    raw_ids = issue_input.replace(",", " ").split()
    issue_ids = [x.strip().replace("#", "") for x in raw_ids if x.strip().replace("#", "").isdigit()]

    if not issue_ids:
        print(f"❌ No valid issue numbers found in: {issue_input!r}")
        return

    def _fetch_issue_from_github(issue_id: str):
        gh_args = ["issue", "view", issue_id, "--json", "number,title,state,url"]
        repo_name = project.get("repo")
        if repo_name:
            gh_args.extend(["--repo", repo_name])

        output = run_gh_command(gh_args, timeout=15)
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError as e:
                print(f"   ⚠️ Failed to parse gh output for issue #{issue_id}: {e}")

        import subprocess

        try:
            fallback_cmd = ["gh", "issue", "view", issue_id, "--json", "number,title,state,url"]
            if repo_name:
                fallback_cmd.extend(["--repo", repo_name])

            gh_res = subprocess.run(
                fallback_cmd,
                cwd=project["path"],
                capture_output=True,
                text=True,
            )
            if gh_res.returncode == 0:
                return json.loads(gh_res.stdout)

            error_text = gh_res.stderr.strip()
            if error_text:
                print(f"   ⚠️ Could not verify issue via gh: {error_text}")
        except Exception as e:
            print(f"   ⚠️ GitHub CLI check failed: {e}")

        return None

    verified_issues = {}

    # ── Verify each issue via gh CLI and keep metadata for sync ──────────────
    for issue_id in issue_ids:
        print(f"🔍 Verifying Issue #{issue_id} via GitHub CLI...")
        issue_data = _fetch_issue_from_github(issue_id)
        if issue_data:
            verified_issues[issue_id] = issue_data
            issue_number = issue_data.get("number", issue_id)
            title = (issue_data.get("title") or "").replace("\n", " ").strip() or "(Untitled issue)"
            state_name = issue_data.get("state", "UNKNOWN")
            print(f"   ✅ Found: #{issue_number} {title} ({state_name})")
        else:
            print(f"   ⚠️ Could not verify issue #{issue_id}. Existing Roadmap entry can still be updated.")

    # ── Helper: find issue in roadmap and return metadata ────────────────────
    def _find_issue(issue_id, lines):
        found_idx = -1
        for i, line in enumerate(lines):
            if (
                f"**#{issue_id}" in line
                or f"#{issue_id} " in line
                or f"[#{issue_id}]" in line
            ):
                found_idx = i
                break

        if found_idx == -1:
            return found_idx, False, -1, "    - "

        is_table_row = lines[found_idx].strip().startswith("|")
        status_idx = -1
        indent = "    - "

        if is_table_row:
            status_idx = found_idx
            print(f"   Current row: {lines[found_idx].strip()}")
        else:
            for i in range(found_idx + 1, min(found_idx + 6, len(lines))):
                stripped = lines[i].strip()
                if (
                    stripped.startswith("- **Status:**")
                    or stripped.startswith("- ✅ **Done**")
                    or stripped.startswith("- 🟡 **In Progress**")
                    or "Status:" in stripped
                    or "✅ **Done**" in stripped
                ):
                    status_idx = i
                    print(f"   Current: {stripped}")
                    if lines[i].startswith("    -"):
                        indent = "    - "
                    elif lines[i].startswith("\t-"):
                        indent = "\t- "
                    break

        return found_idx, is_table_row, status_idx, indent

    def _ensure_synced_issue_section(lines):
        section_title = "## Synced From GitHub"

        for idx, line in enumerate(lines):
            if line.strip().lower() == section_title.lower():
                for next_idx in range(idx + 1, len(lines)):
                    if lines[next_idx].startswith("## "):
                        return next_idx
                return len(lines)

        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append(section_title + "\n")
        lines.append("\n")
        return len(lines)

    def _build_missing_issue_block(issue_data, status_line):
        issue_number = issue_data.get("number", "")
        title = (issue_data.get("title") or "").replace("\n", " ").strip() or "(Untitled issue)"
        issue_url = (issue_data.get("url") or "").strip()
        issue_state = (issue_data.get("state") or "UNKNOWN").strip()

        block = [f"### Issue #{issue_number} - {title}\n"]
        if issue_url:
            block.append(f"- **GitHub:** [#{issue_number}]({issue_url})\n")
        block.append(f"- **State:** {issue_state}\n")
        block.append(status_line.strip() + "\n")
        block.append("\n")
        return block

    # ── Find all requested issues ─────────────────────────────────────────────
    found_issues = []
    missing_issues = []
    for issue_id in issue_ids:
        found_idx, is_table_row, status_idx, indent = _find_issue(issue_id, lines)
        if found_idx == -1:
            if issue_id in verified_issues:
                print(f"⚠️  Issue #{issue_id} not found in Roadmap. Will append it from GitHub metadata.")
                missing_issues.append(issue_id)
            else:
                print(f"⚠️  Issue #{issue_id} not found in Roadmap and could not be verified via gh. Skipping.")
        else:
            print(f"✅ Found issue #{issue_id} at line {found_idx + 1}: {lines[found_idx].strip()}")
            found_issues.append((issue_id, found_idx, is_table_row, status_idx, indent))

    if not found_issues and not missing_issues:
        print("❌ No requested issues could be updated in the Roadmap.")
        return

    # ── Ask for status ONCE — applies to all found issues ────────────────────
    issues_to_update = [x[0] for x in found_issues] + missing_issues
    issue_list = ", ".join(f"#{issue_id}" for issue_id in issues_to_update)
    print(f"\nSelecting status for {len(issues_to_update)} issue(s): {issue_list}")
    # Check if all verified issues being updated are CLOSED
    all_closed = False
    if verified_issues:
        states = [
            verified_issues[i].get("state", "OPEN").upper() 
            for i in issues_to_update if i in verified_issues
        ]
        if states and all(s == "CLOSED" for s in states):
            all_closed = True

    if all_closed:
        print("\n💡 GitHub state is CLOSED, auto-selecting ✅ Done (press Enter to confirm, or choose manually)")
        prompt_str = "Select [1-4] (Enter for '1'): "
    else:
        print("\nSelect new status:")
        prompt_str = "Select [1-4]: "

    print("  [1] ✅ Done / Complete")
    print("  [2] 🟢 Ready")
    print("  [3] 🟡 In Progress / Todo")
    print("  [4] 🔴 Blocked")

    status_choice = input(prompt_str).strip()
    if all_closed and status_choice == "":
        status_choice = "1"
    if status_choice not in ("1", "2", "3", "4"):
        print("❌ Invalid selection")
        return

    version = ""
    note = ""
    if status_choice == "1":
        version = input("Enter Version (e.g. v1.8.0, Enter to skip): ").strip()
        note = input("Enter Completion Note (Enter to skip): ").strip()

    def _build_status_strings(is_table_row, indent):
        if status_choice == "1":
            status_prefix = "✅ Complete" if is_table_row else "✅ **Done**"
            if version and note:
                new_table_status = f"{status_prefix} ({version}) - {note}"
            elif version:
                new_table_status = f"{status_prefix} ({version})"
            elif note:
                new_table_status = f"{status_prefix} - {note}"
            else:
                new_table_status = f"{status_prefix}"
            new_status_line = (
                f"{indent}✅ **Done**"
                + (f" ({version})" if version else "")
                + (f" - {note}" if note else "")
            )
        elif status_choice == "2":
            new_table_status = "🟢 Ready"
            new_status_line = f"{indent}**Status:** 🟢 **Ready**"
        elif status_choice == "3":
            new_table_status = "🔲 Todo" if is_table_row else "🟡 In Progress"
            new_status_line = f"{indent}**Status:** 🟡 **In Progress**"
        else:
            new_table_status = "🔴 Blocked"
            new_status_line = f"{indent}**Status:** 🔴 **Blocked**"
        return new_table_status, new_status_line

    # ── Apply updates in reverse line order to preserve indices ──────────────
    for issue_id, found_idx, is_table_row, status_idx, indent in sorted(
        found_issues, key=lambda x: x[1], reverse=True
    ):
        new_table_status, new_status_line = _build_status_strings(is_table_row, indent)

        if is_table_row:
            parts = lines[found_idx].split("|")
            status_col_index = -2 if lines[found_idx].rstrip().endswith("|") else -1
            if len(parts) >= 3:
                parts[status_col_index] = f" {new_table_status} "
                lines[found_idx] = "|".join(parts)
                if not lines[found_idx].endswith("\n"):
                    lines[found_idx] += "\n"
            else:
                print(f"⚠️  Issue #{issue_id}: row does not have standard table formatting.")
        elif status_idx != -1:
            lines[status_idx] = new_status_line + "\n"
        else:
            print(f"⚠️  Issue #{issue_id}: status line not found nearby. Appending.")
            lines.insert(found_idx + 2, new_status_line + "\n")

        print(f"   ✅ Issue #{issue_id} → updated.")

    added_issue_count = 0
    if missing_issues:
        insert_at = _ensure_synced_issue_section(lines)
        new_issue_lines = []
        for issue_id in missing_issues:
            issue_data = verified_issues.get(issue_id)
            if not issue_data:
                continue
            _, new_status_line = _build_status_strings(False, "- ")
            new_issue_lines.extend(_build_missing_issue_block(issue_data, new_status_line))
            added_issue_count += 1
            print(f"   ✅ Issue #{issue_id} → added to Roadmap from GitHub.")
        if new_issue_lines:
            lines[insert_at:insert_at] = new_issue_lines

    # ── Write back once ───────────────────────────────────────────────────────
    try:
        with open(roadmap_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        updated_count = len(found_issues) + added_issue_count
        print(f"\n✅ Roadmap updated successfully! ({updated_count} issue(s))")
    except Exception as e:
        print(f"❌ Failed to write roadmap: {e}")


def action_archive_artifacts(state: LumaState, project: dict):
    """Move active artifacts to feature directory"""
    if not state.active_issue:
        print("❌ No active issue to archive for.")
        return

    combined_number = "-".join([str(i.number) for i in state.active_issues])
    print(f"\n📦 Archiving artifacts for Issue #{combined_number}...")

    # Determine Feature Directory
    # Strategy: Try to find existing dir matching issue number
    features_root = os.path.join(project["path"], "docs", "features")
    if not os.path.exists(features_root):
        os.makedirs(features_root)

    feature_dir = None

    # 1. Check if we already have a context
    if state.context.get("last_feature_dir"):
        feature_dir = state.context.get("last_feature_dir")

    # 2. Search existing
    if not feature_dir:
        for d in os.listdir(features_root):
            if d.startswith(f"{combined_number}_") or f"issue-{combined_number}" in d:
                feature_dir = os.path.join(features_root, d)
                break

    # 3. Create new if needed
    if not feature_dir:
        combined_title = " & ".join([i.title for i in state.active_issues])
        slug = (
            combined_title.lower()
            .replace(" ", "-")
            .replace("[", "")
            .replace("]", "")[:50]
        )
        dirname = f"{combined_number}_{slug}"
        feature_dir = os.path.join(features_root, dirname)
        os.makedirs(feature_dir, exist_ok=True)
        print(f"   📂 Created feature dir: {dirname}")
    else:
        print(f"   📂 Target: {os.path.basename(feature_dir)}")

    # Only archive locally generated planning/documentation artifacts.
    # AI Brain artifacts (task.md, walkthrough.md, etc.) are handled by ai_brain_sync.py
    # and placed in the ai_brain/ subdirectory.
    search_dirs = [project["path"]]

    artifacts = ["analysis.md", "spec.md", "plan.md", "sbe.md", "code_review.md"]
    # Also support platform specific variations like plan_android.md

    import shutil

    moved_count = 0

    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        for filename in os.listdir(sdir):
            is_match = filename in artifacts
            if not is_match:
                if filename.startswith("plan_") and filename.endswith(".md"):
                    is_match = True
                if filename.startswith("spec_") and filename.endswith(".md"):
                    is_match = True

            if is_match:
                src = os.path.join(sdir, filename)
                dst = os.path.join(feature_dir, filename)
                try:
                    shutil.move(src, dst)
                    print(f"   ➡️  Moved {filename}")
                    moved_count += 1
                except Exception as e:
                    print(f"   ⚠️  Failed to process {filename}: {e}")

    if moved_count == 0:
        print("   (No local artifacts found to archive)")
    else:
        print(f"✅ Archived {moved_count} local files.")

    # 4. Sync AI Brain artifacts (Antigravity & Gemini CLI)
    try:
        from luma_core.ai_brain_sync import AntigravityBrain, GeminiCLIBrain

        # Issue number requires int
        issue_num_int = (
            int(combined_number.split("-")[0])
            if "-" in combined_number
            else int(combined_number)
        )

        # Sync Antigravity
        antigravity_files = AntigravityBrain.sync_to_repo(
            project["path"], issue_num_int
        )
        if antigravity_files:
            print(f"✅ Synced {len(antigravity_files)} Antigravity artifacts.")

        # Sync Gemini CLI
        gemini_files = GeminiCLIBrain.sync_to_repo(project["path"], issue_num_int)
        if gemini_files:
            print(f"✅ Synced {len(gemini_files)} Gemini CLI artifacts.")

    except Exception as e:
        print(f"   ⚠️  Failed to sync AI Brain artifacts: {e}")


def get_feature_dir(project_path: str, issue_number: str) -> str:
    """Helper to find feature directory for an issue"""
    features_root = os.path.join(project_path, "docs", "features")
    if not os.path.exists(features_root):
        return None

    for d in os.listdir(features_root):
        # Match patterns: 71_..., issue-71..., x-issue-71..., etc.
        if (
            d.startswith(f"{issue_number}_")
            or f"issue-{issue_number}" in d
            or f"-{issue_number}_" in d
        ):
            return os.path.join(features_root, d)
    return None


def check_planning_artifacts(feature_dir: str) -> dict:
    """Check existence of planning artifacts"""
    artifacts = {"analysis": "analysis.md", "spec": "spec.md", "plan": "plan.md"}
    status = {}
    if not feature_dir or not os.path.exists(feature_dir):
        for k in artifacts:
            status[k] = False
        return status

    for key, filename in artifacts.items():
        status[key] = os.path.exists(os.path.join(feature_dir, filename))

    return status


def action_guided_workflow(state: LumaState, project: dict):
    """Run a guided end-to-end feature workflow"""
    print("\n⚡ Starting Guided Feature Workflow")
    print("====================================")

    # 1. Select Issue
    if not state.active_issue:
        print("\n🔹 Step 1: Select Issue")
        if not action_select_issue(state, project):
            print("❌ No issue selected. Aborting.")
            return
    else:
        combined_number = "-".join([str(i.number) for i in state.active_issues])
        print(f"\n🔹 Step 1: Issue #{combined_number} already selected.")

    # 2. Planning (Refine -> Spec -> Plan)
    print("\n🔹 Step 2: Planning Phase (Analyst -> Spec -> Architect)")

    target_planning_repos = [project]
    if project.get("sibling_repos"):
        print("\n   📂 Select repos for Planning:")
        print(f"   [1] ✅ {project['name']} (current)")
        
        selectable_repos = [project]
        # We need to access global PROJECTS dictionary if it's available, otherwise skip sibling lookup
        from luma_core.actions import PROJECTS
        for sib_id in project["sibling_repos"]:
            if sib_id in PROJECTS:
                selectable_repos.append(PROJECTS[sib_id])
                
        for i, sib in enumerate(selectable_repos[1:], start=2):
            print(f"   [{i}] ☐  {sib['name']}")
            
        repo_choice = input("   Select (e.g. 1,2,3 or 'a' for all, Enter for current only): ").strip().lower()
        if repo_choice == 'a':
            target_planning_repos = selectable_repos
        elif repo_choice:
            selected_indices = [idx.strip() for idx in repo_choice.split(",") if idx.strip().isdigit()]
            new_targets = []
            for idx_str in selected_indices:
                idx = int(idx_str) - 1
                if 0 <= idx < len(selectable_repos):
                    new_targets.append(selectable_repos[idx])
            if new_targets:
                target_planning_repos = new_targets

    for planning_proj in target_planning_repos:
        if len(target_planning_repos) > 1:
            print(f"\n   ────────────── Planning for {planning_proj['name']} ──────────────")

        # Check for existing artifacts
        combined_number = "-".join([str(i.number) for i in state.active_issues])
        feature_dir = get_feature_dir(planning_proj["path"], combined_number)
        # Also check context if just created
        if not feature_dir and state.context.get("last_feature_dir"):
            feature_dir = state.context.get("last_feature_dir")

        # Save to context immediately so action_generate_plan will use it
        if feature_dir:
            state.context["last_feature_dir"] = feature_dir

        artifacts_status = check_planning_artifacts(feature_dir)
        has_any = any(artifacts_status.values())

        run_planning = True
        planning_mode = "all"  # all, missing, selective
        selected_steps = ["analysis", "spec", "plan"]

        if has_any:
            print(
                f"\n   📝 Found existing Planning Docs in {os.path.basename(feature_dir)}:"
            )
            for k, exists in artifacts_status.items():
                icon = "[x]" if exists else "[ ]"
                print(f"      {icon} {k.capitalize()} ({k}.md)")

            print("\n   Select action:")
            print("   [1] Run All (Overwrite)")
            print("   [2] Generate Missing Only")
            print("   [3] Select Specific Documents")
            print("   [0] Skip Planning Phase")

            p_choice = input("\n   Select [0-3]: ").strip()

            if p_choice == "0":
                run_planning = False
            elif p_choice == "2":
                planning_mode = "missing"
            elif p_choice == "3":
                planning_mode = "selective"
                # Ask for selection
                selected_steps = []
                if input("      - Run Analysis? (y/N): ").lower() == "y":
                    selected_steps.append("analysis")
                if input("      - Run Spec? (y/N): ").lower() == "y":
                    selected_steps.append("spec")
                if input("      - Run Plan? (y/N): ").lower() == "y":
                    selected_steps.append("plan")
                if not selected_steps:
                    print("      (No steps selected, skipping planning)")
                    run_planning = False
            else:
                # Default to Run All
                planning_mode = "all"

        else:
            # Standard flow
            if input("   Run Planning Phase? (Y/n): ").lower() == "n":
                run_planning = False

        if run_planning:
            # Execute based on mode/selection

            # 1. Analyst
            should_run_analyst = False
            if planning_mode == "all":
                should_run_analyst = True
            elif planning_mode == "missing" and not artifacts_status["analysis"]:
                should_run_analyst = True
            elif planning_mode == "selective" and "analysis" in selected_steps:
                should_run_analyst = True

            if should_run_analyst:
                usage_tracker.set_sub_action("Auto:Planning/Analyst")
                action_refine_issue(state, planning_proj)
                # Update feature dir after analyst runs (it might have created it)
                feature_dir = get_feature_dir(planning_proj["path"], state.active_issues[0].number if state.active_issues else combined_number)
                state.context["last_feature_dir"] = feature_dir

            # 2. Spec
            should_run_spec = False
            if planning_mode == "all":
                should_run_spec = True
            elif planning_mode == "missing" and not artifacts_status["spec"]:
                should_run_spec = True
            elif planning_mode == "selective" and "spec" in selected_steps:
                should_run_spec = True

            if should_run_spec:
                usage_tracker.set_sub_action("Auto:Planning/Spec+SBE")
                action_generate_spec(state, planning_proj)
                # Update feature dir
                if state.context.get("last_feature_dir"):
                    feature_dir = state.context.get("last_feature_dir")

            # 3. Plan
            should_run_plan = False
            if planning_mode == "all":
                should_run_plan = True
            elif planning_mode == "missing" and not artifacts_status["plan"]:
                should_run_plan = True
            elif planning_mode == "selective" and "plan" in selected_steps:
                should_run_plan = True

            if should_run_plan:
                # Ensure feature_dir is in context so action_generate_plan doesn't ask again
                if feature_dir:
                    state.context["last_feature_dir"] = feature_dir
                usage_tracker.set_sub_action("Auto:Planning/Plan")
                action_generate_plan(state, planning_proj)

    # 3. Coding (User)
    print("\n🔹 Step 3: Coding Phase")
    print("   🤖 AI Assist + 👤 Human Coding")

    # Offer Multi-Agent Swarm
    usage_tracker.set_sub_action("Auto:Coding/Multi-Agent")
    action_run_multi_agent_coding(state, project)

    print("   - Use your IDE to implement the feature.")
    print("   - Run 'Luma' > 'Code Review' periodically.")

    rel_feat_dir = "docs/features/..."
    if feature_dir:
        try:
            rel_feat_dir = os.path.relpath(feature_dir, project.get("path", "."))
        except:
            pass

    cont = input(
        "\n   Have you finished coding and verified the feature? (y/N): "
    ).lower()
    if cont != "y":
        print("\n⏳ Pausing workflow. Come back when you're done!")
        return

    print("\n   " + "🛠️" * 5 + " ต้อง Manual verify อย่างไรบ้าง " + "🛠️" * 5)

    # 4. Review & Docs & Roadmap
    print("\n🔹 Step 4: Quality, Documentation & Roadmap")
    if input("   Run Code Review? (Y/n): ").lower() != "n":
        usage_tracker.set_sub_action("Auto:Quality/CodeReview")
        action_code_review(state, project)

        print("\n   " + "🔍" * 5 + " RE-VERIFY AFTER REVIEW " + "🔍" * 5)
        print("   กรุณา Re-verify ฟังก์ชันต่างๆ อีกครั้งหลังจากทำการแก้ไขตาม Code Review")
        print("   เพื่อยืนยันว่าไม่มีผลกระทบ (Regression) ต่อส่วนอื่นๆ ของระบบ")
        print("   " + "-" * 75)

    if input("   Update Docs (Changelog/README/Version)? (Y/n): ").lower() != "n":
        usage_tracker.set_sub_action("Auto:Quality/Docs")
        action_update_docs(state, project)

    if input("   Update Roadmap? (Y/n): ").lower() != "n":
        usage_tracker.set_sub_action("Auto:Quality/Roadmap")
        action_update_roadmap(state, project)

    # 5. Archive Artifacts
    print("\n🔹 Step 5: Archive Artifacts")
    if input("   Move artifacts to docs/features/...? (Y/n): ").lower() != "n":
        action_archive_artifacts(state, project)

    # 6. Create PR (With Auto Option)
    print("\n🔹 Step 6: Create Pull Request")

    # Check for "Yes to All" preference
    auto_approve_pr = False
    choice = (
        input("   Create PRs? [y] Yes (confirm each), [a] Yes to All (auto), [n] No: ")
        .strip()
        .lower()
    )

    if choice == "a":
        usage_tracker.set_sub_action("Auto:PR/Auto-Approve")
        action_create_pr(state, project, auto_approve=True, target_repos=target_planning_repos)
    elif choice == "y" or choice == "":
        usage_tracker.set_sub_action("Auto:PR/Interactive")
        action_create_pr(state, project, auto_approve=False, target_repos=target_planning_repos)

    # Poll for Merge?
    if state.phase == WorkflowPhase.PR_PENDING and state.pr_url:
        print(f"\n⏳ PR Created: {state.pr_url}")

        # 7. CI Check
        print("\n🔹 Step 7: Check CI Status")
        if input("   Check CI status? (Y/n): ").strip().lower() != "n":
            from luma_core.ci_checker import check_pr_ci_status, get_ci_failure_logs
            from luma_core.notifier import notify_task_complete
            import time
            
            parts = state.pr_url.split("/")
            if len(parts) >= 7 and "github.com" in state.pr_url:
                ci_repo = f"{parts[-4]}/{parts[-3]}"
                ci_pr_num = parts[-1]
                
                max_polls = 20
                for attempt in range(1, max_polls + 1):
                    display_str = f"   ⏳ Waiting for CI... ({attempt}/{max_polls})"
                    print(display_str, end="\r")
                    
                    status = check_pr_ci_status(ci_pr_num, ci_repo)
                    if status["all_passed"]:
                        print(f"\r   ✅ All CI checks passed!{' ' * 20}")
                        notify_task_complete(
                            project=project.get("name", "Unknown"),
                            task=f"CI Check for PR #{ci_pr_num}",
                            status="success",
                            link=state.pr_url
                        )
                        break
                    elif len(status["failed_checks"]) > 0:
                        print(f"\r   ❌ CI Failed:{' ' * 20}")
                        for fc in status["failed_checks"]:
                            print(f"      - {fc.get('name', 'Unknown')} ({fc.get('conclusion', 'failure').lower()})")
                        
                        first_fail = status["failed_checks"][0].get("name")
                        if first_fail:
                            print(f"\n   📋 Error Log ({first_fail}):")
                            fail_log = get_ci_failure_logs(ci_pr_num, ci_repo, first_fail)
                            print(fail_log)
                            
                            ai_context = f"The CI check `{first_fail}` failed for my PR on {ci_repo}.\nHere is the log:\n```\n{fail_log}\n```\nHow should I fix this?"
                            print("\n   💡 Sending error logs to Akasa Telegram Bot...")
                            
                            notify_task_complete(
                                project=project.get("name", "Unknown"),
                                task=f"CI Check for PR #{ci_pr_num} ({first_fail})",
                                status="failure",
                                message=ai_context,
                                link=state.pr_url
                            )
                            print("   ✅ Notification sent!")
                            break # break poll loop to ask user
                    
                    time.sleep(30)
                else:
                    print(f"\r   ⚠️ CI check timed out ending polls.{' ' * 20}")
                    notify_task_complete(
                        project=project.get("name", "Unknown"),
                        task=f"CI Check for PR #{ci_pr_num}",
                        status="failure",
                        message="CI check timed out after 10 minutes.",
                        link=state.pr_url
                    )
            else:
                print("   ⚠️ Could not parse PR URL to check CI.")

        print("\n   Please merge the PR on GitHub.")
        input("   Press Enter AFTER you have merged the PR...")

        # Use the refresh check logic from main loop or just assume
        from luma_core.github_project import check_pr_merged

        pr_status = check_pr_merged(state.pr_url)
        if pr_status["merged"]:
            print("✅ PR Merged confirmed!")

    # Clear sub_action at the end of the auto workflow so future usage is clean
    usage_tracker.set_sub_action(None)

    # 8. Send Summary to Telegram
    try:
        from luma_core.metrics_summarizer import (
            summarize_usage_stats,
            summarize_issue_metrics,
            format_summary_message,
        )
        from luma_core.notifier import notify_task_complete as _notify

        usage_summary = summarize_usage_stats(
            usage_tracker.get_log_path(), project, usage_tracker._SESSION_ID
        )
        metrics_path = os.path.join(project["path"], ".luma_metrics.json")
        metrics_summary = summarize_issue_metrics(metrics_path)
        summary_msg = format_summary_message(usage_summary, metrics_summary)
        _notify(
            project=project.get("name", "Unknown"),
            task="Workflow Summary",
            status="success",
            message=summary_msg,
        )
        print("\n📊 Summary sent to Telegram!")
    except Exception as e:
        print(f"\n⚠️ Could not send summary: {e}")

    print("\n🎉 Workflow Completed! You can now select the next issue.")


def action_run_multi_agent_coding(state: LumaState, project: dict):
    """Run sequential AI coding agents for different stacks."""
    print("\n🤖 Multi-Agent Auto-Coding Swarm")
    print("==================================")
    print("Which agents would you like to compile?")
    print("  [1] All (Frontend + Backend + Android + iOS)")
    print("  [2] Frontend (Web)")
    print("  [3] Backend (Go/Python)")
    print("  [4] Android (Kotlin)")
    print("  [5] iOS (Swift)")
    print("  [6] 📝 Generate Prompts Only (for manual use)")
    print("  [0] Skip (Manual Coding)")

    choice = input("\nSelect [0-6]: ").strip()

    if choice == "0":
        feature_dir = None
        if state.context.get("last_feature_dir"):
            feature_dir = state.context.get("last_feature_dir")

        if not feature_dir:
            features_root = os.path.join(project["path"], "docs", "features")
            if os.path.exists(features_root):
                combined_number = "-".join([str(i.number) for i in state.active_issues])
                for d in os.listdir(features_root):
                    if (
                        d.startswith(f"{combined_number}_")
                        or f"issue-{combined_number}" in d
                    ):
                        feature_dir = os.path.join(features_root, d)
                        break

        feature_label = os.path.basename(feature_dir) if feature_dir else "[feature_dir]"
        prompt_instruction_brief = (
            f"ให้อ่านไฟล์ทั้งหมดใน `docs/features/{feature_label}` "
            "(ระวังปัญหาติด .gitignore ให้ใช้วิธีอ่านไฟล์โดยตรง)\n"
            "มาวิเคราะห์ อธิบาย และถามคำถามเพื่อ clarify ก่อนที่จะเริ่มลงมือ implement"
        )
        print("   💡 Prompt Instruction:")
        print(f"   {prompt_instruction_brief}")
        return

    # Define agents config
    agents_to_run = []
    generate_prompts_only = False

    if choice == "1":
        agents_to_run = ["frontend", "backend", "android", "ios"]
    elif choice == "2":
        agents_to_run = ["frontend"]
    elif choice == "3":
        agents_to_run = ["backend"]
    elif choice == "4":
        agents_to_run = ["android"]
    elif choice == "5":
        agents_to_run = ["ios"]
    elif choice == "6":
        agents_to_run = ["frontend", "backend", "android", "ios"]
        generate_prompts_only = True
    else:
        print("❌ Invalid selection.")
        return

    # Import Coder
    try:
        from luma_core.agents.coder import coder_agent
    except ImportError:
        print("❌ Coder Agent not found.")
        return

    # Execution Loop
    for agent_type in agents_to_run:
        print(f"\n🚀 Preparing {agent_type.upper()} context...")

        # 1. Prepare Context based on type
        # In a real system, we'd read from plan.md to get specific tasks per platform
        # For now, we use a generic task + specific path scope

        combined_number = "-".join([str(i.number) for i in state.active_issues])
        combined_title = " & ".join([i.title for i in state.active_issues])
        sub_task = f"Implement {agent_type} components for Issue #{combined_number}: {combined_title}"
        source_paths = []

        tech_stack = ""
        if agent_type == "frontend":
            tech_stack = "React/Vue/Web technologies. Focus on UI implementation."
            if os.path.exists(os.path.join(project["path"], "Web")):
                source_paths.append("Web/package.json")
        elif agent_type == "backend":
            tech_stack = "Go. Implement API endpoints and business logic."
            if os.path.exists(os.path.join(project["path"], "backend")):
                source_paths.append("backend/go.mod")
        elif agent_type == "android":
            tech_stack = "Kotlin/Jetpack Compose. Implement Mobile UI and ViewModel. You can use ./gradlew directly."
            if os.path.exists(
                os.path.join(project["path"], "view")
            ):  # Legacy or Luma specific
                pass
        elif agent_type == "ios":
            tech_stack = "Swift/SwiftUI. Implement iOS UI + MVVM. Use XCTest."
            # Ideally look for xcodeproj but we don't have a specific file to append yet
            pass

        sub_task += f" Use {tech_stack}"

        # --- NEW: Context from Artifacts ---
        artifact_context = ""
        feature_dir = None

        # 1. Try to find feature dir
        if state.context.get("last_feature_dir"):
            feature_dir = state.context.get("last_feature_dir")

        if not feature_dir:
            features_root = os.path.join(project["path"], "docs", "features")
            if os.path.exists(features_root):
                combined_number = "-".join([str(i.number) for i in state.active_issues])
                for d in os.listdir(features_root):
                    if (
                        d.startswith(f"{combined_number}_")
                        or f"issue-{combined_number}" in d
                    ):
                        feature_dir = os.path.join(features_root, d)
                        break

        if feature_dir and os.path.exists(feature_dir):
            print(f"   📂 Loading context from: {os.path.basename(feature_dir)}...")
            docs_to_read = [
                "analysis.md",
                "plan.md",
                "spec.md",
                "implementation_plan.md",
                f"plan_{agent_type}.md",
            ]

            for doc in docs_to_read:
                doc_path = os.path.join(feature_dir, doc)
                if os.path.exists(doc_path):
                    try:
                        with open(doc_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            artifact_context += f"\n\n## Reference: {doc}\n{content[:5000]}\n(truncated if too long)\n"
                    except:
                        pass
        else:
            print("   ⚠️ No feature directory found. Using generic context.")

        feature_label = os.path.basename(feature_dir) if feature_dir else "[feature_dir]"
        prompt_instruction = (
            f"ให้อ่านไฟล์ทั้งหมดใน `docs/features/{feature_label}` "
            f"และไฟล์ `prompt_{agent_type}.txt` นี้ (ระวังปัญหาติด .gitignore ให้ใช้วิธีอ่านไฟล์โดยตรง)\n"
            "มาวิเคราะห์ อธิบาย และถามคำถามเพื่อ clarify ก่อนที่จะเริ่มลงมือ implement"
        )
        prompt_instruction_brief = (
            f"ให้อ่านไฟล์ทั้งหมดใน `docs/features/{feature_label}` "
            "(ระวังปัญหาติด .gitignore ให้ใช้วิธีอ่านไฟล์โดยตรง)\n"
            "มาวิเคราะห์ อธิบาย และถามคำถามเพื่อ clarify ก่อนที่จะเริ่มลงมือ implement"
        )

        if generate_prompts_only:
            # Just generate the prompt text file
            prompt_file = os.path.join(project["path"], f"prompt_{agent_type}.txt")
            combined_number = "-".join([str(i.number) for i in state.active_issues])
            combined_title = " & ".join([i.title for i in state.active_issues])
            combined_body = "\n\n---\n\n".join(
                [
                    f"### Issue #{issue.number}\n{issue.body or ''}"
                    for issue in state.active_issues
                ]
            )

            android_specific_instruction = ""
            if agent_type == "android":
                android_specific_instruction = "\n**⚠️ สำคัญมากๆ สำหรับ Android:**\nหากคุณต้องการ Test หรือ Build ระบบ **ห้ามรันผ่าน Command Line `gradlew` เด็ดขาด** ให้คุณรันการ Build และ Test ผ่าน UI ของช่องทาง path ของ **Android Studio** เท่านั้น\n"

            prompt_content = f"""# Role: Senior {agent_type.capitalize()} Developer
# Task: {sub_task}
{android_specific_instruction}
**💡 คำสั่งสำหรับ AI Assistant (Cursor/Claude/etc):**
{prompt_instruction}

Please write the code for the following requirements.

## Context
Project: {project["name"]}
Issue: #{combined_number} {combined_title}
Body:
{combined_body or "No details provided."}

## Architecture & Plans (AUTHORITATIVE)
The following content is from the approved design documents. **You MUST follow this design.**
{artifact_context}

## Default Guidance (Use only if not specified in Plans)
- Tech Stack: {tech_stack}
- Follow Clean Architecture
- Ensure TDD (Test Driven Development)

**IMPORTANT CONFLICT RESOLUTION:**
If the 'Architecture & Plans' section conflicts with the 'Default Guidance', **FOLLOW THE PLANS**.

## Output Format
Please provide the full code files wrapped in XML tags:
<file path="path/to/file.ext">
... code ...
</file>

## Language
Please explain your solution and comments in Thai only.
"""
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(prompt_content)
            print(f"   📄 Generated prompt file: {os.path.basename(prompt_file)}")
            print("   💡 Prompt Instruction:")
            print(f"   {prompt_instruction}")
            continue

        # Create scoped state
        agent_state = {
            "task": sub_task,
            "source_files": source_paths,
            "iterations": 0,
            "test_errors": "",
            "skip_coder": False,
        }

        print("   💡 Prompt Instruction:")
        print(f"   {prompt_instruction_brief}")

        # 2. Run Agent
        try:
            print(f"   🤖 Running {agent_type} agent...")
            result = coder_agent(agent_state)

            # 3. Apply Changes (Simulation)
            changes = result.get("changes", {})
            if changes:
                print(f"   📝 Agent proposed {len(changes)} file changes:")
                for path in changes:
                    print(f"      - {path}")

                # In fully auto mode, we might write them.
                # For safety in this CLI, we ask or just save a patch.
                # Let's save a "patch" file for the user to review.
                patch_file = os.path.join(
                    project["path"], f"agent_{agent_type}_patch.xml"
                )
                with open(patch_file, "w") as f:
                    f.write(result.get("code_content", ""))
                print(
                    f"   💾 Saved proposed changes to: {os.path.basename(patch_file)}"
                )
            else:
                print("   🤷 Agent decided not to change any code.")

        except Exception as e:
            print(f"   ⚠️ Agent Error: {e}")

    if generate_prompts_only:
        print(
            "\n✅ Prompts generated! You can now use 'prompt_*.txt' files with your preferred AI."
        )
    else:
        print(
            "\n✅ Multi-Agent session finished. Review the 'agent_*_patch.xml' files."
        )
