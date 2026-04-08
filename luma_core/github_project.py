"""
Luma V2 GitHub Project Integration
===================================
เชื่อมต่อกับ GitHub Project V2 ผ่าน gh CLI
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import subprocess
import json


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
    
    Args:
        args: Command arguments (without 'gh')
        timeout: Command timeout in seconds
        
    Returns:
        Command output or None if failed
    """
    import os
    import shutil
    
    # Find gh executable
    gh_path = shutil.which("gh")
    
    if not gh_path:
        # Try common locations
        for path in ["/opt/homebrew/bin/gh", "/usr/local/bin/gh"]:
            if os.path.exists(path):
                gh_path = path
                break
    
    if not gh_path:
        print("❌ gh CLI not installed. Visit: https://cli.github.com/")
        return None
    
    cmd = [gh_path] + args
    
    try:
        # Create a clean environment for gh CLI
        env = os.environ.copy()
        
        # EXPLICTLY REMOVE GITHUB_TOKEN provided via env vars 
        # because the one in .env/shell often lacks 'read:org' scope causing 'unknown owner type'
        # We want to force usage of the system keyring auth which has correct scopes.
        for token_key in ['GITHUB_TOKEN', 'GH_TOKEN']:
            if env.pop(token_key, None):
                pass
        
        # Remove Python-specific env vars that can interfere with gh CLI
        for key in ['VIRTUAL_ENV', 'PYTHONHOME', 'PYTHONPATH']:
            env.pop(key, None)

        # Force a clean PATH with only essential directories
        clean_path = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        env["PATH"] = clean_path
        
        # Ensure HOME is preserved (crucial for gh config)
        if "HOME" not in env:
             env["HOME"] = os.path.expanduser("~")
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            env=env,
            cwd=env.get("HOME") # Run from HOME to avoid local git config interference
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if "auth login" in error_msg.lower():
                print("❌ gh CLI not logged in. Run: gh auth login")
            # Only print error if it's not a "no items" verification empty state which might be valid in some contexts
            # but for item-list we generally expect success
            else:
                print(f"❌ gh CLI error: {error_msg[:100]}")
            return None
        
        return result.stdout
        
    except subprocess.TimeoutExpired:
        print(f"❌ gh CLI timeout ({timeout}s)")
        return None
    except FileNotFoundError:
        print("❌ gh CLI not installed. Visit: https://cli.github.com/")
        return None
    except Exception as e:
        print(f"❌ gh CLI error: {e}")
        return None


def run_gh_graphql(query: str, variables: Dict[str, str] = None) -> Optional[Dict]:
    """
    Run GraphQL query via gh api graphql
    
    Args:
        query: GraphQL query string
        variables: Query variables
        
    Returns:
        JSON response or None if failed
    """
    args = ["api", "graphql", "-f", f"query={query}"]
    
    if variables:
        for k, v in variables.items():
            args.extend(["-f", f"{k}={v}"])
    
    output = run_gh_command(args)
    
    if output:
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
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
