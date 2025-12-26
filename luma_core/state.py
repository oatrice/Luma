from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    task: str           # The task description
    code_content: str   # Generated code content (Reviewer context)
    filename: str       # Target filename (legacy single-file support)
    test_errors: str    # Error logs from testing
    iterations: int     # Retry count
    approved: bool      # User approval status
    disable_log_truncation: bool # Flag to disable log limit
    changes: Dict[str, str]      # Multi-file changes {filename: content}
    source_files: List[str]      # Context source files
    repo: str                    # GitHub Repository name
    issue_data: Dict[str, Any]   # GitHub Issue data
    test_suggestions: str        # Test cases suggested by Reviewer
    skip_coder: bool             # Flag to skip Coder Agent (Docs Only Mode)
