"""
Luma V2 State Manager
====================
จัดการ State ของ Workflow Guardian ผ่านไฟล์ .luma_state.json
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
from enum import Enum
import json
import os


class WorkflowPhase(Enum):
    """สถานะของ Workflow"""
    IDLE = "idle"
    SELECTING = "selecting"
    CODING = "coding"
    REVIEWING = "reviewing"
    PREFLIGHT = "preflight"
    PR_PENDING = "pr_pending"


@dataclass
class IssueData:
    """ข้อมูล GitHub Issue ที่กำลังทำงาน"""
    number: int
    title: str
    html_url: str
    body: Optional[str] = None
    project_item_id: Optional[str] = None
    project_id: Optional[str] = None
    repository: Optional[str] = None


@dataclass
class LumaState:
    """State หลักของ Luma Workflow Guardian"""
    version: str = "1.0"
    project_key: str = ""
    phase: WorkflowPhase = WorkflowPhase.IDLE
    active_issues: List[IssueData] = field(default_factory=list)
    active_branch: Optional[str] = None
    started_at: Optional[str] = None
    checklist: Dict[str, bool] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def active_issue(self) -> Optional[IssueData]:
        """Backward compat: returns first issue (primary) or None"""
        return self.active_issues[0] if self.active_issues else None

    @property
    def has_issues(self) -> bool:
        """Check if any issues are active"""
        return len(self.active_issues) > 0


# =============================================================================
# State Transition Rules
# =============================================================================

VALID_TRANSITIONS = {
    WorkflowPhase.IDLE: [WorkflowPhase.SELECTING, WorkflowPhase.CODING],
    WorkflowPhase.SELECTING: [WorkflowPhase.IDLE, WorkflowPhase.CODING],
    WorkflowPhase.CODING: [WorkflowPhase.IDLE, WorkflowPhase.REVIEWING, WorkflowPhase.PREFLIGHT, WorkflowPhase.CODING],  # Allow switching issues while coding
    WorkflowPhase.REVIEWING: [WorkflowPhase.PREFLIGHT, WorkflowPhase.CODING],
    WorkflowPhase.PREFLIGHT: [WorkflowPhase.CODING, WorkflowPhase.PR_PENDING, WorkflowPhase.PREFLIGHT],
    WorkflowPhase.PR_PENDING: [WorkflowPhase.IDLE, WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT], # Allow re-checks
}

TRANSITION_REQUIREMENTS = {
    (WorkflowPhase.SELECTING, WorkflowPhase.CODING): ["active_issues", "active_branch"],
    (WorkflowPhase.IDLE, WorkflowPhase.CODING): ["active_issues", "active_branch"],
    (WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING): ["pr_url"],
}


# =============================================================================
# State File Management
# =============================================================================

STATE_FILENAME = ".luma_state.json"


def get_state_path(project_path: str) -> str:
    """Get full path to state file"""
    return os.path.join(project_path, STATE_FILENAME)


def save_state(state: LumaState, project_path: str) -> bool:
    """
    Save state to JSON file
    
    Args:
        state: LumaState object to save
        project_path: Project directory path
        
    Returns:
        True if saved successfully, False otherwise
    """
    state_file = get_state_path(project_path)
    
    try:
        data = asdict(state)
        
        # Convert Enum to string
        data["phase"] = state.phase.value
        data["last_updated"] = datetime.now().isoformat()
        
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
        
    except PermissionError:
        print(f"❌ Permission denied: Cannot write to {state_file}")
        return False
    except Exception as e:
        print(f"❌ Error saving state: {e}")
        return False


def load_state(project_path: str) -> LumaState:
    """
    Load state from JSON file
    
    Args:
        project_path: Project directory path
        
    Returns:
        LumaState object (loaded or default)
    """
    state_file = get_state_path(project_path)
    
    if not os.path.exists(state_file):
        return LumaState()  # Return default state
    
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Convert phase string to Enum
        phase_str = data.get("phase", "idle")
        try:
            data["phase"] = WorkflowPhase(phase_str)
        except ValueError:
            print(f"⚠️ Unknown phase '{phase_str}', defaulting to 'idle'")
            data["phase"] = WorkflowPhase.IDLE
        
        # Backward compat: migrate old single active_issue to active_issues list
        if data.get("active_issue") and not data.get("active_issues"):
            old_issue = data.pop("active_issue")
            if isinstance(old_issue, dict):
                data["active_issues"] = [IssueData(**old_issue)]
            elif isinstance(old_issue, IssueData):
                data["active_issues"] = [old_issue]
        elif "active_issue" in data:
            data.pop("active_issue", None)

        # Reconstruct active_issues list with strict validation
        if data.get("active_issues") and isinstance(data["active_issues"], list):
            valid_issues = []
            for item in data["active_issues"]:
                if isinstance(item, IssueData):
                    valid_issues.append(item)
                elif isinstance(item, dict) and "number" in item and "title" in item:
                    try:
                        valid_issues.append(IssueData(**item))
                    except (TypeError, ValueError):
                        continue # Skip invalid dicts
            data["active_issues"] = valid_issues
        
        # Remove unknown fields
        from dataclasses import fields
        known_fields = {f.name for f in fields(LumaState)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        
        return LumaState(**filtered_data)
        
    except json.JSONDecodeError:
        print("⚠️ Corrupted state file, resetting to default...")
        return LumaState()
    except TypeError as e:
        print(f"⚠️ Invalid state data: {e}, resetting...")
        return LumaState()
    except Exception as e:
        print(f"⚠️ Error loading state: {e}")
        return LumaState()


def clear_state(project_path: str) -> bool:
    """
    Remove state file (reset to idle)
    
    Args:
        project_path: Project directory path
        
    Returns:
        True if cleared successfully
    """
    state_file = get_state_path(project_path)
    
    if os.path.exists(state_file):
        try:
            os.remove(state_file)
            return True
        except Exception as e:
            print(f"❌ Error clearing state: {e}")
            return False
    return True


# =============================================================================
# State Transitions
# =============================================================================

def can_transition(current: WorkflowPhase, target: WorkflowPhase) -> bool:
    """Check if transition is valid"""
    return target in VALID_TRANSITIONS.get(current, [])


def transition_to(
    state: LumaState, 
    new_phase: WorkflowPhase,
    **kwargs
) -> Tuple[bool, str]:
    """
    Attempt to transition state to new phase
    
    Args:
        state: Current LumaState
        new_phase: Target WorkflowPhase
        **kwargs: Additional data for the transition
        
    Returns:
        (success: bool, message: str)
    """
    # Check valid transition
    if not can_transition(state.phase, new_phase):
        return False, f"❌ Cannot transition from '{state.phase.value}' to '{new_phase.value}'"
    
    
    # Check requirements
    # Handle composite keys for requirements (tuple) or simple lookups
    reqs = TRANSITION_REQUIREMENTS.get((state.phase, new_phase))
    if reqs:
        for req in reqs:
            if req not in kwargs or kwargs[req] is None:
                return False, f"❌ Missing required data: '{req}'"
    
    # Apply transition
    old_phase = state.phase
    state.phase = new_phase
    
    # Apply additional data
    for k, v in kwargs.items():
        if hasattr(state, k):
            setattr(state, k, v)
    
    # Phase-specific actions
    if new_phase == WorkflowPhase.CODING:
        state.started_at = datetime.now().isoformat()
        
    elif new_phase == WorkflowPhase.IDLE:
        # Reset active work data
        state.active_issues = []
        state.active_branch = None
        state.pr_url = None
        state.pr_number = None
        state.checklist = {}
        state.started_at = None
    
    state.last_updated = datetime.now().isoformat()
    
    return True, f"✅ Transitioned: {old_phase.value} → {new_phase.value}"


# =============================================================================
# State Display Utilities
# =============================================================================

PHASE_DISPLAY = {
    WorkflowPhase.IDLE: ("⚪", "Idle", "No active task"),
    WorkflowPhase.SELECTING: ("🔍", "Selecting", "Choosing an issue"),
    WorkflowPhase.CODING: ("💻", "Coding", "Development in progress"),
    WorkflowPhase.REVIEWING: ("👀", "Reviewing", "AI Code Review in progress"),
    WorkflowPhase.PREFLIGHT: ("✅", "Pre-flight", "Running checks"),
    WorkflowPhase.PR_PENDING: ("🚀", "PR Pending", "Waiting for merge"),
}


def get_phase_display(phase: WorkflowPhase) -> Tuple[str, str, str]:
    """Get (emoji, name, description) for phase"""
    return PHASE_DISPLAY.get(phase, ("❓", "Unknown", ""))


def format_state_header(state: LumaState) -> str:
    """Format state for display in menu header"""
    emoji, name, _ = get_phase_display(state.phase)
    lines = [f"📍 Phase: {emoji} {name}"]
    
    if state.active_issues:
        if len(state.active_issues) == 1:
            issue = state.active_issues[0]
            lines.append(f"🎯 Task: #{issue.number} {issue.title[:40]}...")
        else:
            nums = ", ".join(f"#{i.number}" for i in state.active_issues)
            lines.append(f"🎯 Tasks: [{nums}] {state.active_issues[0].title[:30]}...")
    
    if state.active_branch:
        lines.append(f"🌿 Branch: {state.active_branch}")
    
    if state.started_at:
        try:
            started = datetime.fromisoformat(state.started_at)
            elapsed = datetime.now() - started
            hours = elapsed.seconds // 3600
            mins = (elapsed.seconds % 3600) // 60
            if elapsed.days > 0:
                lines.append(f"⏱️ Time: {elapsed.days}d {hours}h ago")
            elif hours > 0:
                lines.append(f"⏱️ Time: {hours}h {mins}m ago")
            else:
                lines.append(f"⏱️ Time: {mins}m ago")
        except Exception:
            pass
    
    return "\n".join(lines)


def get_next_step_recommendation(state: LumaState) -> str:
    """Get recommended next action based on current state"""
    recommendations = {
        WorkflowPhase.IDLE: "📥 Select an issue from GitHub Kanban to start",
        WorkflowPhase.SELECTING: "🎯 Choose an issue and confirm to start coding",
        WorkflowPhase.CODING: "💻 Continue development, then run AI Code Review",
        WorkflowPhase.REVIEWING: "👀 Reviewing AI changes, proceed to Pre-flight if tests pass",
        WorkflowPhase.PREFLIGHT: "✅ Fix any issues, then create Pull Request",
        WorkflowPhase.PR_PENDING: "⏳ Wait for PR review and merge",
    }
    return recommendations.get(state.phase, "❓ Unknown state")


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "WorkflowPhase",
    "IssueData", 
    "LumaState",
    "save_state",
    "load_state",
    "clear_state",
    "transition_to",
    "can_transition",
    "get_phase_display",
    "format_state_header",
    "get_next_step_recommendation",
    "VALID_TRANSITIONS",
    "TRANSITION_REQUIREMENTS",
]
