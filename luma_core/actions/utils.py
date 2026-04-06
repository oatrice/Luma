import luma_core.ui as ui
from luma_core.ui import safe_input
import datetime
import json
import os
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
    suggest_post_story_point,
    validate_effort_level,
    validate_post_story_point,
)
from luma_core.state_manager import (
    IssueData,
    LumaState,
    WorkflowPhase,
    transition_to,
)
from luma_core.tools import (
    generate_draft_code_review,
    get_git_changed_files,
    update_multi_repo_docs,
)

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
                import os

                print("🔄 Syncing sibling repos...")
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

        previous_action = usage_tracker.get_current_action()
        previous_context = usage_tracker.get_current_context()
        previous_sub_action = usage_tracker.get_current_sub_action()

        if previous_action is None:
            usage_tracker.set_action("Select Issue")
        if previous_context is None:
            usage_tracker.set_context(state, project)
        usage_tracker.set_sub_action("SelectIssue/BranchSuggestion")

        try:
            suggestions = generate_branch_names(
                primary_title,
                primary_body,
                primary_number,
            )
        finally:
            if previous_context is None:
                usage_tracker.clear_context()
            if previous_action is None:
                usage_tracker.clear_action()
            else:
                usage_tracker.set_action(previous_action)
            usage_tracker.set_sub_action(previous_sub_action)

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

    choice = ui.safe_input("Select [1-3] or type custom name: ").strip()

    branch_name = suggestions[0]  # Default

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(suggestions):
            branch_name = suggestions[idx]
    elif choice:
        branch_name = choice

    # Validate branch name to prevent corruption (e.g., "1", "True", "None")
    invalid_branch_values = ["1", "0", "True", "False", "None", "", "HEAD"]
    if branch_name in invalid_branch_values or len(branch_name) < 2:
        # Fallback to first suggestion if invalid
        print(f"⚠️ Invalid branch name '{branch_name}' detected, using default suggestion.")
        branch_name = suggestions[0]

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
            print("🔄 Creating git branch...")
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
                import os

                print("\n🔄 Creating branches in sibling repos...")
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
                    project,
                )

        return True

    print(f"❌ Transition failed: {msg}")
    return False

def _start_issues_headless(
    state: LumaState, 
    cards: list, 
    project: dict, 
    branch_name: str = None
) -> bool:
    """Headless version of _start_issues that doesn't ask for user input."""
    from luma_core.state_manager import IssueData
    
    issues = [
        IssueData(
            number=c.issue_number,
            title=c.title,
            html_url=c.url,
            project_item_id=c.item_id,
            repository=c.repository,
        )
        for c in cards
    ]

    issue_nums = "-".join(str(c.issue_number) for c in cards)
    primary_title = cards[0].title
    primary_body = cards[0].body or ""
    primary_number = cards[0].issue_number

    if not branch_name:
        try:
            from luma_core.agents.analyst import generate_branch_names
            suggestions = generate_branch_names(primary_title, primary_body, primary_number)
            branch_name = suggestions[0]  # Default to first suggestion
            
            if len(cards) > 1:
                branch_name = branch_name.replace(f"/{primary_number}-", f"/{issue_nums}-")
        except Exception:
            slug = primary_title.lower().replace(" ", "-").replace("[", "").replace("]", "")[:30]
            branch_name = f"feat/{issue_nums}-{slug}"

    # Validate branch name
    invalid_branch_values = ["1", "0", "True", "False", "None", "", "HEAD"]
    if branch_name in invalid_branch_values or len(branch_name) < 2:
        print(f"❌ Invalid branch name: '{branch_name}'")
        return False

    # Transition to coding
    from luma_core.state_manager import transition_to, WorkflowPhase
    ok, msg = transition_to(
        state, WorkflowPhase.CODING, active_issues=issues, active_branch=branch_name
    )

    if ok:
        issue_display = ", ".join(f"#{c.issue_number}" for c in cards)
        print(f"\n✅ Started (Headless): {issue_display}")
        print(f"🌿 Branch: {branch_name}")

        import subprocess
        import os
        try:
            print("🔄 Creating git branch...")
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

            # Create branches in sibling repos if monorepo
            if project.get("type") == "monorepo_root" and project.get("sibling_repos"):
                from luma_core.config import PROJECTS
                for sibling_key in project.get("sibling_repos", []):
                    sibling = PROJECTS.get(sibling_key)
                    if sibling and os.path.exists(sibling["path"]):
                        subprocess.run(["git", "checkout", "-b", branch_name], cwd=sibling["path"], capture_output=True)
                        subprocess.run(["git", "checkout", branch_name], cwd=sibling["path"], capture_output=True)

        except Exception as e:
            print(f"⚠️ Failed to create branch: {e}")

        # Sync Kanban
        for i, card in enumerate(cards):
            if card.item_id and project.get("kanban_id"):
                sync_kanban_on_action("select_issue", project["kanban_id"], card.item_id, project)
        return True
    
    print(f"❌ Transition failed: {msg}")
    return False

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

    choice = ui.safe_input("\nSelect index or use #issue-number [0=Back]: ").strip()
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
        f"{'Idx':<5} {'#':<6} {'Title':<26} {'Pts':<5} {'Post':<5} {'EstMD':<7} "
        f"{'ActMD':<7} {'Start':<16} {'Due':<16} {'Effort':<7}"
    )
    print("─" * 116)
    for idx, record in enumerate(records, 1):
        title = (
            record.issue_title[:24] + ".."
            if len(record.issue_title) > 26
            else record.issue_title
        )
        print(
            f"{idx:<5} #{record.issue_number:<5} {title:<26} "
            f"{(record.estimate_points if record.estimate_points is not None else '-'): <5} "
            f"{(record.post_story_point if record.post_story_point is not None else '-'): <5} "
            f"{(record.estimated_mandays if record.estimated_mandays is not None else '-'): <7} "
            f"{(record.actual_mandays if record.actual_mandays is not None else '-'): <7} "
            f"{format_metric_datetime(record.start_datetime):<16} "
            f"{format_metric_datetime(record.due_date):<16} "
            f"{(record.effort_level or '-'): <7}"
        )
    print("─" * 116)
    print(f"Total tracked: {len(records)}")
    return records

def _select_tracked_issue_record(project: dict):
    records = _display_tracked_issue_summary(project)
    if not records:
        return None

    choice = ui.safe_input("\nSelect index or use #issue-number [0=Back]: ").strip()
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


def _parse_optional_post_story_point(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError("Post Story Point must be a number.") from exc
    validated = validate_post_story_point(parsed)
    return 0.0 if validated is None else validated

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
        raw = ui.safe_input(
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


def _prompt_post_story_point_value(project: dict, record: IssueMetricsRecord):
    current_value = record.post_story_point
    suggested_value = suggest_post_story_point(project["path"], record)

    if current_value is not None:
        return _prompt_metric_value(
            "Post Story Point",
            current_value,
            _parse_optional_post_story_point,
        )

    while True:
        suggestion_text = suggested_value if suggested_value is not None else "-"
        raw = ui.safe_input(
            f"Post Story Point [suggested: {suggestion_text}] "
            "(Enter accept, - clear): "
        ).strip()
        if raw == "":
            return suggested_value
        if raw == "-":
            return None
        try:
            return _parse_optional_post_story_point(raw)
        except ValueError as e:
            print(f"❌ {e}")


def prompt_post_story_points_for_records(project: dict, records: list) -> int:
    updated = 0

    for record in records:
        if record.post_story_point is not None:
            continue

        print(f"\n📌 Post Story Point for #{record.issue_number} - {record.issue_title}")
        next_value = _prompt_post_story_point_value(project, record)
        if next_value is None:
            continue
        if record.post_story_point == next_value:
            continue

        record.post_story_point = next_value
        save_issue_metrics(project["path"], record)
        print("   ✅ Saved Post Story Point.")
        updated += 1

    return updated

def prompt_missing_post_story_points(project: dict):
    """Find issues that are complete but missing post_story_point and prompt for them."""
    from luma_core.issue_metrics import list_issue_metrics
    
    completed_missing_post_points = [
        record
        for record in list_issue_metrics(project["path"])
        if record.post_story_point is None
        and record.repository == project.get("repo")
        and any(
            marker in (record.issue_status or "").lower()
            for marker in ("done", "complete", "released", "closed")
        )
    ]
    
    if completed_missing_post_points:
        print(
            "\n   📌 Re-estimate Post Story Point for completed issues missing actual complexity..."
        )
        prompt_post_story_points_for_records(
            project,
            completed_missing_post_points,
        )

def _edit_issue_metrics_record(project: dict, record: IssueMetricsRecord, is_new: bool = False):
    print(f"\n📝 Issue Metrics for #{record.issue_number} - {record.issue_title}")
    print(f"   Project: {project['name']}")
    print(f"   Repository: {record.repository or '-'}")
    print(f"   Status: {record.issue_status or '-'}")
    print("   Press Enter to keep the current value, or '-' to clear it.")

    candidate = IssueMetricsRecord(**asdict(record))
    changed = False

    estimate_points = _prompt_metric_value(
        "Estimate Points",
        candidate.estimate_points,
        _parse_optional_int,
    )
    if estimate_points is not _KEEP_METRIC_VALUE and candidate.estimate_points != estimate_points:
        candidate.estimate_points = estimate_points
        changed = True

    post_story_point = _prompt_post_story_point_value(project, candidate)
    if candidate.post_story_point != post_story_point:
        candidate.post_story_point = post_story_point
        changed = True

    field_specs = [
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
        ("start_datetime", "Start Date/Time", parse_metric_datetime),
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
        ui.safe_input(
            "   [u] Update now\n"
            "   [c] Continue anyway\n"
            "   [b] Back to Coding\n"
            "   Select (Default=u): "
        )
        .strip()
        .lower()
    )

    if choice in ("", "u"):
        from .quality_actions import action_update_docs
        action_update_docs(state, project, skip_confirm=True)
        status = refresh_pending_doc_updates(state, project)
        summary = pending_doc_update_summary(status)
        if not summary:
            return True

        print(f"   ⚠️ Still pending after docs update: {summary}")
        return ui.safe_input("   Continue PR anyway? (y/N): ").strip().lower() == "y"

    if choice == "c":
        return True

    print("⏳ Back to Coding so you can keep refining before the docs/version update.")
    return False

def _add_new_project(state: LumaState) -> str:
    """Interactively add a new project and save it to config"""
    print("\n✨ Add New Project")
    print("=================")

    name = ui.safe_input("Project Name: ").strip()
    if not name:
        print("❌ Project Name is required.")
        return None

    path = ui.safe_input("Absolute Path to Project: ").strip()
    if not path or not os.path.isabs(path):
        print("❌ Absolute Path is required.")
        return None

    repo = ui.safe_input("GitHub Repo (e.g. oatrice/Akasa) [Optional]: ").strip()
    kanban_number_str = ui.safe_input("GitHub Project Board Number [Optional]: ").strip()

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

def auto_fill_issue_metrics(state: LumaState, project: dict, issues: list):
    """Auto-fill missing metrics using AI / heuristics for the active issues."""
    from luma_core.issue_metrics import get_issue_metrics, save_issue_metrics, apply_heuristic_defaults, IssueMetricsRecord, issue_key_for
    
    if not issues:
        return
        
    for issue in issues:
        metrics = get_issue_metrics(project["path"], project.get("repo", ""), issue.number)
        
        if not metrics:
            metrics = IssueMetricsRecord(
                issue_key=issue_key_for(project.get("repo", ""), issue.number),
                issue_number=issue.number,
                issue_title=issue.title,
                issue_url=issue.url if hasattr(issue, 'url') else "",
                repository=project.get("repo", ""),
                project_name=project.get("name")
            )
            
        print(f"\n🤖 AI is estimating metrics for Issue #{issue.number}...")
        metrics = apply_heuristic_defaults(metrics)
        save_issue_metrics(project["path"], metrics)
        print(f"   ✅ Estimated: {metrics.estimate_points} points, {metrics.estimated_mandays} mandays, {metrics.effort_level} effort.")

__all__ = [name for name in dir() if not name.startswith('__')]
