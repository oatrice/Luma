import os
import subprocess
from collections import deque
from luma_core.ui import safe_input
from luma_core.state_manager import LumaState
from luma_core import usage_tracker
from luma_core.issue_metrics import sync_github_metrics_for_project
from .utils import (
    get_issue_metrics,
    _display_tracked_issue_summary,
    _select_issue_card_for_metrics,
    _edit_issue_metrics_record,
    _build_issue_metrics_record,
    _select_tracked_issue_record,
    _load_recent_usage_events,
    _format_event_line,
    list_issue_metrics,
    prefill_metrics_from_roadmap,
    prompt_missing_post_story_points,
)

def action_view_dashboard(state: LumaState, project: dict):
    """Display Usage & Metrics Dashboard in terminal."""
    from luma_core.metrics_summarizer import (
        summarize_usage_stats,
        summarize_issue_metrics,
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
    post_points = f"{metrics['total_post_points']:.1f}"
    print(f"║    📌 Post Points:  {post_points:<31}║")
    est_md = f"{metrics['total_estimated_mandays']:.1f}"
    act_md = f"{metrics['total_actual_mandays']:.1f}"
    print(f"║    📅 Mandays:      Est {est_md} / Act {act_md:<20}║")
    gap = f"{metrics['total_accuracy_gap']:+.1f}"
    print(f"║    Δ Accuracy Gap: {gap:<31}║")
    print("║                                                    ║")
    print("╚" + "═" * 52 + "╝")

    safe_input("\nPress Enter to return...")
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
        print("  [4] Audit & Sync from GitHub")
        print("  [0] Back")

        choice = input("\nSelect [0-4]: ").strip()
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
        if choice == "4":
            print("\n   🐙 Auto-syncing issue metrics from GitHub...")
            gh_sync_result = sync_github_metrics_for_project(
                selected_project["path"],
                selected_project.get("name"),
                selected_project.get("repo"),
            )
            if gh_sync_result['updated'] > 0:
                print(f"   ✅ Synced {gh_sync_result['updated']} issue records from GitHub.")
            else:
                print("   ✅ GitHub metrics are already up-to-date.")
            
            if gh_sync_result.get("errors", 0) > 0:
                print(f"   ⚠️  Encountered {gh_sync_result['errors']} errors during sync.")
            if gh_sync_result.get("paradoxes_fixed", 0) > 0:
                print(f"   ⏱️  Fixed {gh_sync_result['paradoxes_fixed']} Time Paradox(es).")

            # Suggest and prompt for post story points for newly completed issues
            prompt_missing_post_story_points(selected_project)
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
    
    print("\n🔄 Syncing metrics from ROADMAP...")
    from luma_core.issue_metrics import prefill_metrics_from_roadmap, sync_github_metrics_for_project
    prefill_result = prefill_metrics_from_roadmap(
        project["path"],
        project.get("name"),
        project.get("repo"),
    )
    if prefill_result["created"] or prefill_result["updated"]:
        print(f"   🗺️  Synced (created {prefill_result['created']}, updated {prefill_result['updated']})")
        
    print("\n   🐙 Auto-syncing issue metrics from GitHub...")
    gh_sync_result = sync_github_metrics_for_project(
        project["path"],
        project.get("name"),
        project.get("repo"),
    )
    if gh_sync_result["updated"] > 0:
        print(f"   📊 Synced {gh_sync_result['updated']} records from GH.")
    
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
        original_path = output_path  # remember the original path for diffing
        counter = 1
        while os.path.exists(output_path):
            output_path = os.path.join(base_dir, f"{base_name}({counter}).md")
            counter += 1
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"✅ Report generated successfully at: {output_path}")

        # If a previous version exists, generate a diff
        # If a previous version exists, trigger a visual diff in VS Code
        if output_path != original_path and os.path.exists(original_path):
            try:
                subprocess.run(["code", "--diff", original_path, output_path], check=True)
                print(f"📋 Opening visual diff: {os.path.basename(original_path)} vs {os.path.basename(output_path)}")
            except Exception as e:
                print(f"⚠️ Failed to open visual diff: {e}")
        
    except ValueError:
        print("❌ Invalid date format. Please use YYYY-MM-DD.")
    except Exception as e:
        print(f"❌ Failed to generate report: {e}")

def action_view_stats_files(state: LumaState, project: dict):
    """View AI usage log."""
    usage_path = usage_tracker.get_log_path()

    while True:
        print("\n📊 Usage Log Viewer")
        print("===================")
        print(f"  [1] View .luma_ai_usage.jsonl {'✅' if os.path.exists(usage_path) else '❌'}")
        print("  [2] Show file path")
        print("  [0] Back")

        choice = safe_input("\nSelect [0-2]: ")

        if choice == "0":
            return

        if choice == "1":
            if not os.path.exists(usage_path):
                print("\n❌ .luma_ai_usage.jsonl not found.")
                safe_input("\nPress Enter to return...")
                continue

            print("\n📄 Usage Log View")
            print("  [1] Summary (current project)")
            print("  [2] Summary (all projects)")
            print("  [3] Raw tail (last 50 lines)")
            print("  [0] Back")

            sub = safe_input("\nSelect [0-3]: ")

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
                    safe_input("\nPress Enter to return...")
                    continue

                print("\nLast 50 lines:")
                print("-" * 70)
                for line in tail:
                    print(line)

            else:
                print("❌ Invalid option")

            safe_input("\nPress Enter to return...")
            continue

        if choice == "2":
            print("\n📁 File Path")
            print(f"  .luma_ai_usage.jsonl: {usage_path}")
            safe_input("\nPress Enter to return...")
            continue

        print("❌ Invalid option")
