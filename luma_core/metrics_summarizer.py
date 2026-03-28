"""
📊 Luma Metrics Summarizer — สรุปภาพรวม Usage + Issue Metrics

ใช้สำหรับ:
  1. ส่ง Telegram notification หลังจบ Auto Full Workflow
  2. แสดง Dashboard ใน CLI
"""

import json
import os
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional


def _event_matches_project(event: dict, project: dict) -> bool:
    """Check if a usage event belongs to a given project."""
    if project.get("name") and event.get("project_name") == project["name"]:
        return True
    
    # Path normalization for robustness
    p_path = project.get("path")
    e_path = event.get("project_path")
    if p_path and e_path:
        p_path = os.path.normpath(os.path.abspath(p_path))
        e_path = os.path.normpath(os.path.abspath(e_path))
        if p_path == e_path:
            return True

    if project.get("repo") and event.get("project_repo") == project["repo"]:
        return True
    return False


def summarize_usage_stats(
    log_path: str,
    project: Optional[dict] = None,
    session_id: Optional[str] = None,
    since_hours: Optional[int] = None,
    branch: Optional[str] = None,
) -> Dict[str, Any]:
    """
    อ่าน .luma_ai_usage.jsonl แล้วสรุปเป็น dict

    Returns:
        dict with keys: total_calls, success_count, error_count,
        total_duration_ms, unique_models, top_actions
    """
    total = 0
    success = 0
    error = 0
    duration_ms = 0
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    models: set = set()
    model_counts: Counter = Counter()
    actions: Counter = Counter()
    sub_action_times: Dict[str, Dict[str, Any]] = {}  # {sub_action: {start, end}}

    if not os.path.exists(log_path):
        return {
            "total_calls": 0,
            "success_count": 0,
            "error_count": 0,
            "success_rate": 0.0,
            "total_duration_ms": 0,
            "elapsed_ms": 0,
            "unique_models": [],
            "model_counts": {},
            "top_actions": {},
        }

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
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
                
                # Filter priority: branch > session_id
                if branch:
                    if event.get("active_branch") != branch:
                        continue
                elif session_id:
                    if event.get("session_id") != session_id:
                        continue
                
                # Check since_hours filter
                if since_hours:
                    ts_str = event.get("ts")
                    if ts_str:
                        try:
                            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            now = datetime.now(dt.tzinfo) # Ensure same timezone
                            age = now - dt
                            if age.total_seconds() > since_hours * 3600:
                                continue
                        except (ValueError, TypeError):
                            pass

                total += 1
                status = event.get("status", "")
                if status == "success":
                    success += 1
                elif status == "error":
                    error += 1

                duration_ms += event.get("duration_ms", 0)

                ts_str = event.get("ts")
                if ts_str:
                    try:
                        # Handle basic ISO format, replace Z with +00:00 for older fromisoformat
                        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if start_ts is None or dt < start_ts:
                            start_ts = dt
                        if end_ts is None or dt > end_ts:
                            end_ts = dt
                    except (ValueError, TypeError):
                        pass

                model = event.get("model")
                if model:
                    models.add(model)
                    model_counts[model] += 1

                action = event.get("action")
                if action:
                    actions[action] += 1
                
                # Track per-sub-action timing
                sub_action = event.get("sub_action")
                if sub_action and ts_str:
                    try:
                        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if sub_action not in sub_action_times:
                            sub_action_times[sub_action] = {"start": dt, "end": dt}
                        else:
                            if dt < sub_action_times[sub_action]["start"]:
                                sub_action_times[sub_action]["start"] = dt
                            if dt > sub_action_times[sub_action]["end"]:
                                sub_action_times[sub_action]["end"] = dt
                    except (ValueError, TypeError):
                        pass
    except Exception:
        pass

    elapsed_ms = 0
    if start_ts and end_ts:
        elapsed_ms = int((end_ts - start_ts).total_seconds() * 1000)

    success_rate = 0.0
    if total > 0:
        success_rate = round((success / total) * 100, 1)

    # Process sub_action durations
    sub_actions_flat = {}
    for sa, timers in sub_action_times.items():
        sub_actions_flat[sa] = {
            "elapsed_ms": int((timers["end"] - timers["start"]).total_seconds() * 1000)
        }

    return {
        "total_calls": total,
        "success_count": success,
        "error_count": error,
        "success_rate": success_rate,
        "total_duration_ms": duration_ms,
        "elapsed_ms": elapsed_ms,
        "unique_models": sorted(models),
        "model_counts": dict(model_counts),
        "top_actions": dict(actions.most_common(10)),
        "sub_actions": sub_actions_flat,
    }


def summarize_issue_metrics(metrics_path: str) -> Dict[str, Any]:
    """
    อ่าน .luma_metrics.json แล้วสรุปเป็น dict

    Returns:
        dict with keys: total_issues, done_count, in_progress_count,
        todo_count, total_points, total_estimated_mandays, total_actual_mandays
    """
    empty = {
        "total_issues": 0,
        "done_count": 0,
        "in_progress_count": 0,
        "todo_count": 0,
        "total_points": 0,
        "total_estimated_mandays": 0.0,
        "total_actual_mandays": 0.0,
    }

    if not os.path.exists(metrics_path):
        return empty

    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            store = json.load(f)
    except Exception:
        return empty

    issues = store.get("issues", {})
    if not isinstance(issues, dict):
        return empty

    total = 0
    done = 0
    in_progress = 0
    todo = 0
    points = 0
    est_mandays = 0.0
    act_mandays = 0.0

    for item in issues.values():
        if not isinstance(item, dict):
            continue
        total += 1

        status = (item.get("issue_status") or "").lower()
        if "done" in status or "complete" in status or "released" in status:
            done += 1
        elif "progress" in status or "coding" in status or "review" in status:
            in_progress += 1
        else:
            todo += 1

        points += item.get("estimate_points", 0) or 0
        est_mandays += item.get("estimated_mandays", 0.0) or 0.0
        act_mandays += item.get("actual_mandays", 0.0) or 0.0

    return {
        "total_issues": total,
        "done_count": done,
        "in_progress_count": in_progress,
        "todo_count": todo,
        "total_points": points,
        "total_estimated_mandays": est_mandays,
        "total_actual_mandays": act_mandays,
    }


def _format_duration(ms: int) -> str:
    """Format milliseconds to human readable string."""
    s = (ms or 0) / 1000
    if s < 60:
        return f"{s:.0f}s"
    mins = int(s // 60)
    secs = int(s % 60)
    return f"{mins}m {secs}s"


def format_summary_message(
    usage: Dict[str, Any],
    metrics: Dict[str, Any],
) -> str:
    """
    รวม usage + metrics summary เป็น Markdown message สำหรับ Telegram
    """
    lines: List[str] = []
    lines.append("📊 **Workflow Summary**")
    lines.append("")

    # --- AI Usage ---
    lines.append("🤖 **AI Usage**")
    lines.append(f"  Calls: {usage.get('total_calls', 0)} "
                 f"(✅ {usage.get('success_count', 0)} / "
                 f"❌ {usage.get('error_count', 0)})")
    
    success_rate = usage.get("success_rate", 0.0)
    lines.append(f"  Success Rate: {success_rate}%")
    
    proc_time = _format_duration(usage.get("total_duration_ms", 0))
    lines.append(f"  AI Processing Time: {proc_time}")
    
    workflow_time = _format_duration(usage.get("elapsed_ms", 0))
    lines.append(f"  Workflow Duration: {workflow_time}")
    lines.append("")

    # --- Sub-action Breakdown ---
    sub_actions = usage.get("sub_actions", {})
    if sub_actions:
        lines.append("⏱️ **Breakdown (Elapsed Time)**")
        # Sort by elapsed time descending or just alphabetically? Alpha is safer for stable UI.
        for sa in sorted(sub_actions.keys()):
            sa_duration = _format_duration(sub_actions[sa]["elapsed_ms"])
            lines.append(f"  - {sa}: {sa_duration}")
        lines.append(f"  - Total (Elapsed): {workflow_time}")
        lines.append("")
    
    models = usage.get("unique_models", [])
    if models:
        lines.append(f"  Models: {', '.join(models)}")
    
    # --- Model Breakdown ---
    model_counts = usage.get("model_counts", {})
    if model_counts:
        lines.append("")
        lines.append("🧱 **Model Breakdown**")
        for model in sorted(model_counts.keys()):
            lines.append(f"  - {model} ({model_counts[model]})")

    # --- Action Breakdown ---
    top_actions = usage.get("top_actions", {})
    if top_actions:
        lines.append("")
        lines.append("⚙️ **Action Breakdown**")
        # Show top 10 actions
        for action, count in list(top_actions.items())[:10]:
            lines.append(f"  - {action} ({count})")

    lines.append("")

    # --- Issue Metrics ---
    lines.append("📏 **Issue Metrics**")
    lines.append(f"  Issues: {metrics.get('total_issues', 0)} "
                 f"(✅ {metrics.get('done_count', 0)} / "
                 f"🔄 {metrics.get('in_progress_count', 0)} / "
                 f"🔲 {metrics.get('todo_count', 0)})")
    lines.append(f"  Points: {metrics.get('total_points', 0)}")
    lines.append(f"  Mandays: "
                 f"Est {metrics.get('total_estimated_mandays', 0):.1f} / "
                 f"Act {metrics.get('total_actual_mandays', 0):.1f}")

    return "\n".join(lines)
