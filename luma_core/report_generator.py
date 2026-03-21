import os
import re
from typing import Optional, List, Tuple, Dict
from datetime import date, datetime, timedelta
import calendar

from luma_core.issue_metrics import (
    IssueMetricsRecord,
    list_issue_metrics,
    get_roadmap_path,
)

def _get_period_dates(period: str, ref_date: date) -> Tuple[datetime, datetime, datetime, datetime]:
    if period == "monthly":
        start_this = datetime(ref_date.year, ref_date.month, 1)
        # Handle month rollover for end_this
        if ref_date.month == 12:
            end_this = datetime(ref_date.year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_this = datetime(ref_date.year, ref_date.month + 1, 1) - timedelta(seconds=1)
            
        # Previous month
        if ref_date.month == 1:
            start_prev = datetime(ref_date.year - 1, 12, 1)
        else:
            start_prev = datetime(ref_date.year, ref_date.month - 1, 1)
        end_prev = start_this - timedelta(seconds=1)
        
    else:  # weekly
        # ISO week: Monday is 0, Sunday is 6
        start_this = datetime.combine(ref_date - timedelta(days=ref_date.weekday()), datetime.min.time())
        end_this = start_this + timedelta(days=7) - timedelta(seconds=1)
        start_prev = start_this - timedelta(days=7)
        end_prev = start_this - timedelta(seconds=1)
        
    return start_this, end_this, start_prev, end_prev

def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None

def _is_complete(status: Optional[str]) -> bool:
    if not status:
        return False
    status_lower = status.lower()
    return "complete" in status_lower or "done" in status_lower or "released" in status_lower

def _parse_roadmap_phases(roadmap_path: str) -> Tuple[List[Dict[str, object]], str]:
    phases = []
    replan_history_lines = []
    if not os.path.exists(roadmap_path):
        return phases, ""
        
    with open(roadmap_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    current_phase = None
    in_replan_section = False
    
    for line in lines:
        if bool(re.match(r"^##\s+.*(?:Replan History|📅).*", line, re.IGNORECASE)):
            in_replan_section = True
            current_phase = None
            continue
        elif in_replan_section and re.match(r"^##\s+", line):
            in_replan_section = False
            
        if in_replan_section:
            if line.strip():
                replan_history_lines.append(line.strip())
            continue
            
        phase_match = re.match(r"^##\s+(Phase\s+\d+.*?)\s*$", line)
        if phase_match:
            if current_phase:
                phases.append(current_phase)
            current_phase = {
                "name": phase_match.group(1).strip(),
                "total": 0,
                "completed": 0
            }
            continue
            
        if current_phase:
            # Check for issue in table
            if line.strip().startswith("|") and "[#" in line:
                current_phase["total"] += 1
                if "✅" in line or "Complete" in line or "Done" in line:
                    current_phase["completed"] += 1
                    
    if current_phase:
        phases.append(current_phase)
        
    return phases, "\n".join(replan_history_lines)

def generate_report(project_path: str, period: str = "weekly", reference_date: Optional[date] = None) -> str:
    if reference_date is None:
        reference_date = date.today()
        
    metrics = list_issue_metrics(project_path)
    roadmap_path = get_roadmap_path(project_path)
    
    start_this, end_this, start_prev, end_prev = _get_period_dates(period, reference_date)
    
    # Velocity calculation
    this_period_completed = []
    prev_period_completed = []
    
    overdue_issues = []
    upcoming_issues = []
    
    today = datetime.combine(reference_date, datetime.min.time())
    upcoming_limit = today + timedelta(days=7 if period == "weekly" else 30)
    
    for issue in metrics:
        due_dt = _parse_datetime(issue.due_date)
        completed_dt = _parse_datetime(issue.actual_completion_date)
        is_done = _is_complete(issue.issue_status)
        
        if is_done and completed_dt:
            if start_this <= completed_dt <= end_this:
                this_period_completed.append(issue)
            elif start_prev <= completed_dt <= end_prev:
                prev_period_completed.append(issue)
                
        if not is_done and due_dt:
            # For overdue it should be strictly before today
            if due_dt < today:
                overdue_issues.append(issue)
            elif today <= due_dt <= upcoming_limit:
                upcoming_issues.append(issue)
                
    # On-time rate
    on_time_count = 0
    for issue in this_period_completed:
        due_dt = _parse_datetime(issue.due_date)
        completed_dt = _parse_datetime(issue.actual_completion_date)
        if due_dt and completed_dt and completed_dt <= due_dt:
            on_time_count += 1
        elif completed_dt and not due_dt:
            # Count as on-time if no due date? Requirements don't specify, let's say yes or just ignore
            on_time_count += 1
            
    # Compile markdown
    lines = []
    report_type = "Weekly" if period == "weekly" else "Monthly"
    
    # Header
    date_range_str = f"{start_this.strftime('%Y-%m-%d')} to {end_this.strftime('%Y-%m-%d')}"
    lines.append(f"# {report_type} Report")
    lines.append(f"**Date Range:** {date_range_str}")
    lines.append("")
    
    # Velocity Summary
    lines.append("## Velocity Summary")
    this_points = sum(iss.estimate_points or 0 for iss in this_period_completed)
    prev_points = sum(iss.estimate_points or 0 for iss in prev_period_completed)
    trend = "↑" if this_points > prev_points else "↓" if this_points < prev_points else "→"
    
    est_mandays = sum(iss.estimated_mandays or 0.0 for iss in this_period_completed)
    act_mandays = sum(iss.actual_mandays or 0.0 for iss in this_period_completed)
    
    lines.append(f"- **Issues completed in this period:** {len(this_period_completed)}")
    lines.append(f"- **Total points:** {this_points}")
    lines.append(f"- **Trend vs previous period:** {trend} (was {prev_points} points)")
    lines.append(f"- **Mandays (Completed):** {est_mandays:.1f} estimated vs {act_mandays:.1f} actual")
    lines.append("")
    
    # On-time Delivery Rate
    lines.append("## On-time Delivery Rate")
    total_completed = len(this_period_completed)
    if total_completed > 0:
        rate = (on_time_count / total_completed) * 100
        lines.append(f"- **{on_time_count}/{total_completed}** completed issues were on time ({rate:.0f}%)")
    else:
        lines.append("- No issues completed in this period.")
    lines.append("")
    
    # Overdue Issues
    lines.append("## Overdue Issues")
    if overdue_issues:
        for iss in overdue_issues:
            due_dt = _parse_datetime(iss.due_date)
            days_overdue = (today - due_dt).days if due_dt else 0
            lines.append(f"- **#{iss.issue_number}** {iss.issue_title} (Due: {iss.due_date}, Overdue by {days_overdue} days)")
    else:
        lines.append("- No overdue issues.")
    lines.append("")
    
    # Upcoming Due Dates
    lines.append("## Upcoming Due Dates")
    if upcoming_issues:
        for iss in upcoming_issues:
            lines.append(f"- **#{iss.issue_number}** {iss.issue_title} (Due: {iss.due_date})")
    else:
        lines.append("- No upcoming issues.")
    lines.append("")
    
    # Phase Progress
    if roadmap_path:
        phases, replan_history = _parse_roadmap_phases(roadmap_path)
        if phases:
            lines.append("## Phase Progress")
            for phase in phases:
                tot = int(phase["total"]) # type: ignore
                comp = int(phase["completed"]) # type: ignore
                pct = (comp / tot * 100) if tot > 0 else 0
                lines.append(f"- **{phase['name']}**: {comp}/{tot} ({pct:.0f}%)")
            lines.append("")
            
        if replan_history:
            lines.append("## Replan History Summary")
            # simple summary: take up to top 15 lines
            history_preview = "\n".join(replan_history.split("\n")[:15])
            lines.append(history_preview)
            if len(replan_history.split("\n")) > 15:
                lines.append("...")
            lines.append("")
            
    return "\n".join(lines)
