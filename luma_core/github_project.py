"""
Luma V2 GitHub Project Integration
===================================
เชื่อมต่อกับ GitHub Project V2 ผ่าน gh CLI
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import subprocess
import json
from luma_core.cli_wrapper import get_cli_wrapper


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class KanbanCard:
    """ข้อมูล Card บน GitHub Project Kanban"""
    item_id: str           # "PVTI_..."
    issue_number: int
    title: str
    status: str            # "Backlog" | "Ready" | "In Progress" | "Done"
    repository: str        # "oatrice/JarWise-Root"
    url: str
    body: Optional[str] = None


# =============================================================================
# Project Configuration
# =============================================================================

# Known projects
KNOWN_PROJECTS = {
    "jarwise": {
        "number": 7,
        "id": "PVT_kwHOATfKEM4BMuLi",
        "name": "JarWise Kanban",
        "owner": "oatrice",
    },
    "tetris": {
        "number": 6,
        "id": "PVT_kwHOATfKEM4BKZK5", 
        "name": "Tetris Kanban",
        "owner": "oatrice",
    },
    "luma": {
        "number": 5,
        "id": "PVT_kwHOATfKEM4BKOOI",
        "name": "Luma Kanban",
        "owner": "oatrice",
    },
}


def get_project_config(project_key: str) -> Optional[Dict[str, Any]]:
    """Get project config by key"""
    return KNOWN_PROJECTS.get(project_key.lower())


# =============================================================================
# gh CLI Helpers
# =============================================================================

def run_gh_command(args: List[str], timeout: int = 30) -> Optional[str]:
    """
    Run gh CLI command and return output
    """
    try:
        wrapper = get_cli_wrapper()
        
        # Convert GitHub CLI commands to GitLab CLI equivalents
        if wrapper.cli_tool == "glab":
            args = _convert_glab_command(args)
        
        result = wrapper.run_cli_command(args)
        return result
    except subprocess.TimeoutExpired:
        print(f"   2. {wrapper.cli_tool} CLI command timed out")
        return None
    except Exception as e:
        print(f"   2. {wrapper.cli_tool} CLI error: {str(e)[:100]}")
        return None


def _convert_glab_command(args: List[str]) -> List[str]:
    """Convert GitHub CLI commands to GitLab CLI equivalents."""
    # Convert project item-list to board list for GitLab
    if len(args) >= 4 and args[0] == "project" and args[1] == "item-list":
        # gh project item-list 5 --owner oatricedev --format json
        # Convert to: glab board list --group oatricedev --format json
        project_id = args[2]
        owner = None
        format_json = False
        
        i = 3
        while i < len(args):
            if args[i] == "--owner" and i + 1 < len(args):
                owner = args[i + 1]
                i += 2
            elif args[i] == "--format" and i + 1 < len(args) and args[i + 1] == "json":
                format_json = True
                i += 2
            else:
                i += 1
        
        # For GitLab, we'll use issue list with tab-separated format
        # This is a temporary solution - the full GitLab project board integration would need
        # a different approach since GitLab doesn't have the same project structure as GitHub
        return ["issue", "list", "--per-page", "50"]
    
    return args


def _parse_glab_issue_list(output: str) -> List[KanbanCard]:
    """Parse GitLab CLI tab-separated issue list into KanbanCard objects."""
    cards = []
    lines = output.strip().split('\n')
    
    # Skip header line and empty lines
    data_lines = [line for line in lines if line.strip() and not line.startswith('ID\tTitle')]
    
    for line in data_lines:
        # Parse tab-separated values
        parts = line.split('\t')
        if len(parts) >= 2:
            # Extract issue number from "#91" format
            issue_id = parts[0].strip()
            if issue_id.startswith('#'):
                issue_number = int(issue_id[1:])
            else:
                continue
            
            title = parts[1].strip()
            labels = parts[2].strip() if len(parts) > 2 else ""
            created_at = parts[3].strip() if len(parts) > 3 else ""
            
            # Create KanbanCard with GitLab issue data
            card = KanbanCard(
                item_id=f"GLAB_{issue_number}",
                issue_number=issue_number,
                title=title,
                status="Ready",  # Default status for GitLab issues
                repository="oatricedev/Luma",
                url=f"https://gitlab.com/oatricedev/Luma/-/issues/{issue_number}",
                body=None
            )
            cards.append(card)
    
    return cards


def run_gh_graphql(query: str, variables: Dict[str, str] = None) -> Optional[Dict]:
    """
    Run GraphQL query via VCS CLI
    
    Args:
        query: GraphQL query string
        variables: Query variables
        
    Returns:
        JSON response or None if failed
    """
    wrapper = get_cli_wrapper()
    
    # GitLab CLI doesn't support GraphQL the same way as GitHub CLI
    # For now, we'll skip GraphQL operations when using GitLab
    if wrapper.cli_tool == "glab":
        print("   2. GitLab CLI doesn't support GraphQL operations in this context")
        return None
    
    args = ["api", "graphql", "-f", f"query={query}"]
    
    if variables:
        for k, v in variables.items():
            args.extend(["-f", f"{k}={v}"])
    
    output = run_gh_command(args)
    
    if output:
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            print(f"   2. JSON parse error: {e}")
            return None
    return None


# =============================================================================
# Kanban Operations
# =============================================================================

def fetch_kanban_cards(
    project_number: Optional[int],
    owner: str = "oatrice",
    status_filter: Optional[str] = None
) -> List[KanbanCard]:
    """
    ดึงการ์ดจาก GitHub Project Kanban

    Args:
        project_number: Project number (e.g., 7 for JarWise), or None if not configured
        owner: GitHub username or org
        status_filter: Optional status to filter (e.g., "Ready", "In Progress")

    Returns:
        List of KanbanCard objects
    """
    if project_number is None:
        print("⚠️  No Kanban project configured for this repository.")
        return []

    args = [
        "project", "item-list", str(project_number),
        "--owner", owner,
        "--format", "json",
        "--limit", "1000"
    ]
    
    output = run_gh_command(args, timeout=30)
    
    if not output:
        return []
    
    # Check if output is from GitLab CLI (tab-separated format)
    if "ID\tTitle\tLabels\tCreated at" in output:
        return _parse_glab_issue_list(output)
    
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        print("❌ Failed to parse project items")
        return []
    
    cards = []
    
    for item in data.get("items", []):
        content = item.get("content", {})
        
        # Skip non-issues (e.g., draft items, PRs)
        if content.get("type") != "Issue":
            continue
        
        card = KanbanCard(
            item_id=item.get("id", ""),
            issue_number=content.get("number", 0),
            title=item.get("title") or content.get("title", ""),
            status=item.get("status", "Unknown"),
            repository=content.get("repository", ""),
            url=content.get("url", ""),
            body=content.get("body")
        )
        
        # Apply status filter
        if status_filter:
            if card.status.lower() != status_filter.lower():
                continue
        
        cards.append(card)
    
    return cards


def add_issue_to_project(
    project_number: int,
    issue_url: str,
    owner: str = "oatrice"
) -> Optional[str]:
    """
    เพิ่ม Issue เข้า GitHub Project Kanban
    
    Args:
        project_number: Project number (e.g., 5 for Luma)
        issue_url: URL ของ issue (e.g., "https://github.com/oatrice/Luma/issues/50")
        owner: GitHub username or org
        
    Returns:
        item_id ของ project item ที่เพิ่มเข้าไป หรือ None ถ้า fail
    """
    args = [
        "project", "item-add", str(project_number),
        "--owner", owner,
        "--url", issue_url,
        "--format", "json"
    ]
    
    output = run_gh_command(args, timeout=30)
    
    if not output:
        return None
    
    try:
        data = json.loads(output)
        return data.get("id")
    except json.JSONDecodeError:
        print("❌ Failed to parse project item-add response")
        return None


def get_project_field_schema(project_id: str) -> Optional[Dict]:
    """
    Get project field schema (Status field options)
    
    Args:
        project_id: Project ID (e.g., "PVT_...")
        
    Returns:
        Dict with field_id and options, or None
    """
    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 20) {
            nodes {
              ... on ProjectV2SingleSelectField {
                id
                name
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    """
    
    result = run_gh_graphql(query, {"projectId": project_id})
    
    if not result:
        return None
    
    try:
        fields = result.get("data", {}).get("node", {}).get("fields", {}).get("nodes", [])
        
        for field in fields:
            if field and field.get("name") == "Status":
                return {
                    "field_id": field["id"],
                    "options": {
                        opt["name"].lower(): opt["id"] 
                        for opt in field.get("options", [])
                    }
                }
    except Exception as e:
        print(f"❌ Error parsing field schema: {e}")
    
    return None


def move_card_to_status(
    project_id: str,
    item_id: str,
    new_status: str
) -> bool:
    """
    ย้ายการ์ดไปยังสถานะใหม่บน Kanban
    
    Args:
        project_id: Project ID (e.g., "PVT_...")
        item_id: Item ID (e.g., "PVTI_...")
        new_status: Target status name (e.g., "In Progress")
        
    Returns:
        True if successful
    """
    # Get field schema
    schema = get_project_field_schema(project_id)
    
    if not schema:
        print("❌ Could not get project field schema")
        return False
    
    # Find option ID for status
    option_id = schema["options"].get(new_status.lower())
    
    if not option_id:
        available = ", ".join(schema["options"].keys())
        print(f"❌ Status '{new_status}' not found. Available: {available}")
        return False
    
    # Run mutation
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(
        input: {
          projectId: $projectId
          itemId: $itemId
          fieldId: $fieldId
          value: { singleSelectOptionId: $optionId }
        }
      ) {
        projectV2Item {
          id
        }
      }
    }
    """
    
    variables = {
        "projectId": project_id,
        "itemId": item_id,
        "fieldId": schema["field_id"],
        "optionId": option_id
    }
    
    result = run_gh_graphql(mutation, variables)
    
    if result and "errors" not in result:
        print(f"✅ Moved to '{new_status}'")
        return True
    else:
        errors = result.get("errors", []) if result else []
        print(f"❌ Failed to move: {errors}")
        return False


# =============================================================================
# Convenience Functions
# =============================================================================

def get_current_in_progress(
    project_number: int, 
    owner: str = "oatrice"
) -> Optional[KanbanCard]:
    """
    Get the first "In Progress" card
    
    Args:
        project_number: Project number
        owner: GitHub username
        
    Returns:
        KanbanCard or None if no active task
    """
    cards = fetch_kanban_cards(project_number, owner, status_filter="In Progress")
    return cards[0] if cards else None


def get_ready_issues(
    project_number: int,
    owner: str = "oatrice"
) -> List[KanbanCard]:
    """
    Get all "Ready" cards (available to start)
    
    Args:
        project_number: Project number
        owner: GitHub username
        
    Returns:
        List of ready KanbanCards
    """
    return fetch_kanban_cards(project_number, owner, status_filter="Ready")


def sync_kanban_on_action(
    action: str,
    project_id: str,
    item_id: str,
    status_map: Optional[Dict[str, str]] = None,
) -> bool:
    """
    Auto-sync Kanban based on Luma action
    
    Args:
        action: Action name ("start_issue", "select_issue", "create_pr", "pr_merged")
        project_id: GitHub Project ID
        item_id: Project item ID
        
    Returns:
        True if synced successfully
    """
    status_map = status_map or {
        "start_issue": "In Progress",
        "select_issue": "In Progress",
        "create_pr": "In Review",
        "pr_merged": "Done",
    }

    if not project_id or not item_id:
        print("⚠️ Missing GitHub Project identifiers; skipping Kanban sync")
        return False
    
    new_status = status_map.get(action)
    
    if not new_status:
        print(f"⚠️ Unknown action: {action}")
        return False
    
    return move_card_to_status(project_id, item_id, new_status)


# =============================================================================
# Display Functions
# =============================================================================

def display_kanban_cards(cards: List[KanbanCard], show_body: bool = False) -> None:
    """
    แสดงรายการการ์ดในรูปแบบ table
    
    Args:
        cards: List of KanbanCard
        show_body: Whether to show issue body
    """
    if not cards:
        print("📭 No cards found")
        return
    
    print(f"\n{'─' * 60}")
    print(f"{'#':<5} {'Title':<35} {'Status':<12}")
    print(f"{'─' * 60}")
    
    for card in cards:
        title = card.title[:33] + "..." if len(card.title) > 35 else card.title
        print(f"#{card.issue_number:<4} {title:<35} {card.status:<12}")
        
        if show_body and card.body:
            body_preview = card.body[:100].replace('\n', ' ')
            print(f"      └─ {body_preview}...")
    
    print(f"{'─' * 60}")
    print(f"Total: {len(cards)} cards")


# =============================================================================
# PR Status Check
# =============================================================================

def check_pr_merged(pr_url: str) -> dict:
    """
    Check if a PR has been merged
    
    Args:
        pr_url: Full PR URL (e.g., https://github.com/owner/repo/pull/123)
        
    Returns:
        {"merged": True/False, "state": "open|closed|merged", "error": None|str}
    """
    import re
    
    # Parse PR URL
    match = re.match(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
    if not match:
        return {"merged": False, "state": "unknown", "error": "Invalid PR URL"}
    
    owner, repo, pr_number = match.groups()
    
    # Use gh CLI to get PR status
    args = ["pr", "view", pr_number, "--repo", f"{owner}/{repo}", "--json", "state"]
    output = run_gh_command(args, timeout=15)
    
    if not output:
        return {"merged": False, "state": "unknown", "error": "Failed to fetch PR"}
    
    try:
        data = json.loads(output)
        state = data.get("state", "unknown").lower()
        
        if state == "merged":
            return {"merged": True, "state": "merged", "error": None}
        else:
            return {"merged": False, "state": state, "error": None}
            
    except json.JSONDecodeError as e:
        return {"merged": False, "state": "unknown", "error": str(e)}


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "KanbanCard",
    "KNOWN_PROJECTS",
    "get_project_config",
    "fetch_kanban_cards",
    "move_card_to_status",
    "get_current_in_progress",
    "get_ready_issues",
    "sync_kanban_on_action",
    "display_kanban_cards",
    "get_project_field_schema",
    "run_gh_command",
    "run_gh_graphql",
    "check_pr_merged",
]
