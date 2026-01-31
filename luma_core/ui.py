import unicodedata
from luma_core.state_manager import LumaState, WorkflowPhase, get_phase_display, get_next_step_recommendation

# =============================================================================
# Constants
# =============================================================================

BOX_WIDTH = 58

MENU_ACTIONS = {
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

# =============================================================================
# Display Functions
# =============================================================================

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
    
    emoji, phase_name, _ = get_phase_display(state.phase)
    
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


def display_menu(state: LumaState, actions: dict = None):
    """Display context-sensitive menu"""
    # Color codes (Basic usage)
    DIM = "\033[90m"
    RESET = "\033[0m"
    
    if actions is None:
        actions = MENU_ACTIONS
    
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
