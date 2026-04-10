import os
import sys
import unicodedata

# Unix-specific terminal imports
try:
    import tty
    import termios
except ImportError:
    tty = None
    termios = None

try:
    from simple_term_menu import TerminalMenu
except ImportError:
    TerminalMenu = None

from luma_core.doc_updates import get_pending_doc_updates, pending_doc_update_summary
from luma_core.state_manager import LumaState, get_phase_display, get_next_step_recommendation
# Constants
# =============================================================================

BOX_WIDTH = 58

# MENU_ACTIONS is now passed from main.py to avoid duplication.
# See select_menu_option `actions` parameter.

# =============================================================================
# Input Handlers
# =============================================================================

def safe_input(prompt: str = "") -> str:
    """
    A robust input replacement that reads character by character using TTY/termios.
    Handles messed up terminal states where standard input() hangs or shows ^M.
    """
    # Try low-level terminal read if on Unix
    if tty is None or termios is None:
        try:
            return input(prompt).strip()
        except EOFError:
            return ""

    try:
        fd = sys.stdin.fileno()

        # Fallback if NOT a real TTY (e.g. in some IDE consoles or pipes)
        if not os.isatty(fd):
            return input(prompt).strip()

        sys.stdout.write(prompt)
        sys.stdout.flush()
        old_settings = termios.tcgetattr(fd)
        try:
            # Put terminal in cbreak mode to read single chars
            tty.setcbreak(fd)
            chars = []
            while True:
                c = sys.stdin.read(1)
                if not c:
                    break
                if c in ("\n", "\r"):  # Both represent "Enter"
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    break
                # ord(c) == 127 is Backspace on macOS, 8 on some others
                if ord(c) in (8, 127):
                    if chars:
                        chars.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif ord(c) == 3:  # Ctrl+C
                    raise KeyboardInterrupt()
                elif ord(c) == 4:  # Ctrl+D
                    break
                else:
                    chars.append(c)
                    sys.stdout.write(c)
                    sys.stdout.flush()
            return "".join(chars).strip()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except (ImportError, Exception):
        # Fallback to standard input if tty/termios not available or error occurs
        try:
            return input(prompt).strip()
        except EOFError:
            return ""

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

    # Show original project name if in worktree, with worktree indicator
    from luma_core.tools import get_main_repo_name_from_worktree
    main_repo_name = get_main_repo_name_from_worktree()
    if main_repo_name:
        project_display = f"{main_repo_name} (worktree)"
    else:
        project_display = project['name']
    _print_boxed_line(format_row("📂", "Project", project_display), BOX_WIDTH)
    
    # Folder path (truncated if too long)
    folder_path = project.get('path', 'N/A')
    max_path_len = 40
    if len(folder_path) > max_path_len:
        folder_path = "..." + folder_path[-(max_path_len-3):]
    _print_boxed_line(format_row("📁", "Folder ", folder_path), BOX_WIDTH)
    
    # GitHub Project info
    kanban_number = project.get('kanban_number')
    if kanban_number:
        _print_boxed_line(format_row("🐙", "GH Proj", f"Project #{kanban_number}"), BOX_WIDTH)
    
    _print_boxed_line(format_row("📍", "Phase  ", f"{emoji} {phase_name}"), BOX_WIDTH)
    
    if state.active_issues:
        issue = state.active_issues[0]
        if len(state.active_issues) == 1:
            max_title_len = 35 
            # Defensive check: ensure title is a string
            title = getattr(issue, 'title', 'Unknown Task')
            if callable(title): # Handle the str.title method case
                title = str(issue)
            
            if not isinstance(title, str):
                title = str(title)

            if len(title) > max_title_len:
                title = title[:max_title_len] + "..."
            task_info = f"#{getattr(issue, 'number', '?')} {title}"
        else:
            nums = ", ".join(f"#{getattr(i, 'number', '?')}" for i in state.active_issues)
            primary_title = getattr(issue, 'title', 'Tasks')
            if callable(primary_title):
                primary_title = str(issue)
            
            title = str(primary_title)[:25] + "..."
            task_info = f"[{nums}] {title}"
        _print_boxed_line(format_row("🎯", "Task   ", task_info), BOX_WIDTH)
    
    if state.active_branch:
        # Truncate branch
        max_branch_len = 40
        branch = state.active_branch
        if len(branch) > max_branch_len:
            branch = branch[:max_branch_len] + "..."
            
        _print_boxed_line(format_row("🌿", "Branch ", branch), BOX_WIDTH)

    pending_status = get_pending_doc_updates(state)
    pending_summary = pending_doc_update_summary(pending_status)
    if pending_summary:
        max_pending_len = 35
        if len(pending_summary) > max_pending_len:
            pending_summary = pending_summary[:max_pending_len] + "..."
        _print_boxed_line(format_row("📝", "Pending", pending_summary), BOX_WIDTH)
    
    print("╠" + "═" * (BOX_WIDTH + 2) + "╣")
    
    next_step = get_next_step_recommendation(state)
    _print_boxed_line(f"  ➡️  {next_step}", BOX_WIDTH)
    
    print("╚" + "═" * (BOX_WIDTH + 2) + "╝")


def select_menu_option(state: LumaState, actions: dict = None, title: str = "👉 Select an action:") -> str:
    """
    display interactive menu and return selected action key.
    Uses simple-term-menu for arrow key navigation.
    """
    if actions is None:
        print("⚠️ No actions provided to menu.")
        return "0"

    # Fallback if dependency is missing (Headless environments)
    if TerminalMenu is None:
        display_menu(state, actions)
        return safe_input(f"\n{title}\n👉 Select: ").strip()

    # Prepare menu items
    menu_items = []
    keys = []
    
    # Filter valid actions
    for key, action in actions.items():
        is_valid = False
        if action["valid_phases"] == "ALL":
            is_valid = True
        elif state.phase in action["valid_phases"]:
            is_valid = True
            
        if is_valid:
            # Format: "[Key] Label"
            menu_items.append(f"[{key}] {action['label']}")
            keys.append(key)
            
    if not menu_items:
        return "0"

    print("\n") # Space before menu
    
    terminal_menu = TerminalMenu(
        menu_items,
        title=title,
        menu_cursor="> ",
        menu_cursor_style=("fg_cyan", "bold"),
        menu_highlight_style=("bg_cyan", "fg_black"),
        cycle_cursor=True,
        clear_screen=False,
    )
    
    # Handle KeyboardInterrupt during menu selection gracefully
    try:
        menu_entry_index = terminal_menu.show()
    except KeyboardInterrupt:
        return "0"
    
    if menu_entry_index is None:
        return "0" # Exit on ESC/Cancel
        
    return keys[menu_entry_index]


def display_menu(state: LumaState, actions: dict = None):
    """
    Legacy display function.
    Now just delegates to select_menu_option if called, 
    but strictly speaking main.py calls this then input().
    To avoid breaking if we revert main.py, we keep it but it's unused if main.py changes.
    """
    if actions is None:
        print("⚠️ No actions provided.")
        return
    
    print("\n📋 Actions (Legacy View):")
    for key, action in actions.items():
        print(f"  [{key}] {action['label']}")
