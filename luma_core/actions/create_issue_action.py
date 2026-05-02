"""
Action: Create Issue with Cross-Repo Link Support
==================================================
สร้าง Issue พร้อมรองรับการเชื่อมโยงข้าม Repository (Luma <-> Zenith)
"""

import json
import re
import subprocess
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from luma_core.ui import safe_input
from luma_core.state_manager import LumaState
from luma_core.github_project import run_gh_command, run_gh_graphql
from luma_core.config import PROJECTS


@dataclass
class CrossRepoLink:
    """ข้อมูลการเชื่อมโยงข้าม Repository"""
    repo: str           # เช่น "oatrice/Zenith"
    issue_number: int
    url: str
    relationship: str = "Related"  # Related, Closes, Fixes, etc.


def detect_zenith_issues_from_text(text: str) -> List[CrossRepoLink]:
    """
    Auto-detect Zenith issue references จากข้อความ
    รองรับ patterns:
    - oatrice/Zenith#19
    - Zenith#19
    - https://github.com/oatrice/Zenith/issues/19
    - #19 (ถ้า context ชัดเจนว่าเป็น Zenith)
    """
    if not text:
        return []
    
    links = []
    
    # Pattern: oatrice/Zenith#19 หรือ Zenith#19
    pattern1 = r'(?:oatrice/)?Zenith#(\d+)'
    for match in re.finditer(pattern1, text, re.IGNORECASE):
        issue_num = int(match.group(1))
        links.append(CrossRepoLink(
            repo="oatrice/Zenith",
            issue_number=issue_num,
            url=f"https://github.com/oatrice/Zenith/issues/{issue_num}",
            relationship="Related"
        ))
    
    # Pattern: Full URL
    pattern2 = r'https://github\.com/oatrice/Zenith/issues/(\d+)'
    for match in re.finditer(pattern2, text):
        issue_num = int(match.group(1))
        # เช็คว่ายังไม่มีใน list
        if not any(link.issue_number == issue_num for link in links):
            links.append(CrossRepoLink(
                repo="oatrice/Zenith",
                issue_number=issue_num,
                url=f"https://github.com/oatrice/Zenith/issues/{issue_num}",
                relationship="Related"
            ))
    
    return links


def detect_zenith_issues_from_branch(branch_name: str) -> List[CrossRepoLink]:
    """
    Auto-detect Zenith issues จากชื่อ branch
    Patterns:
    - feature/zenith-19-description
    - fix-zenith-22-bug
    - zenith/19-description
    """
    if not branch_name:
        return []
    
    links = []
    
    # Pattern: zenith-19 หรือ zenith/19
    patterns = [
        r'zenith[-/](\d+)',
        r'zenith[_-]?(\d+)',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, branch_name, re.IGNORECASE):
            issue_num = int(match.group(1))
            if not any(link.issue_number == issue_num for link in links):
                links.append(CrossRepoLink(
                    repo="oatrice/Zenith",
                    issue_number=issue_num,
                    url=f"https://github.com/oatrice/Zenith/issues/{issue_num}",
                    relationship="Related"
                ))
    
    return links


def prompt_cross_repo_links(auto_detected: List[CrossRepoLink]) -> List[CrossRepoLink]:
    """
    Prompt ผู้ใช้สำหรับ cross-repo links (manual override/add)
    """
    print("\n🔗 Cross-Repo Link Detection")
    print("─" * 50)
    
    final_links = list(auto_detected)
    
    # แสดง auto-detected
    if auto_detected:
        print("✅ Auto-detected links:")
        for link in auto_detected:
            print(f"   • {link.repo}#{link.issue_number} ({link.relationship})")
    else:
        print("ℹ️  No auto-detected cross-repo links")
    
    # ถามว่าต้องการเพิ่ม manual links ไหม
    print("\n[1] Accept auto-detected links only")
    print("[2] Add manual cross-repo links")
    print("[3] Remove/Edit detected links")
    
    choice = safe_input("\nSelect: ").strip()
    
    if choice == "2":
        # Manual entry
        print("\n📝 Manual Cross-Repo Entry")
        print("Format: owner/repo#issue_number (e.g., oatrice/Zenith#19)")
        print("Enter empty line when done")
        
        while True:
            entry = safe_input("Add link: ").strip()
            if not entry:
                break
            
            # Parse entry
            match = re.match(r'(?:https://github\.com/)?([^/]+/[^/#]+)/?#?(?:issues?/)?(\d+)', entry)
            if match:
                repo = match.group(1)
                issue_num = int(match.group(2))
                final_links.append(CrossRepoLink(
                    repo=repo,
                    issue_number=issue_num,
                    url=f"https://github.com/{repo}/issues/{issue_num}",
                    relationship="Related"
                ))
                print(f"   ✅ Added {repo}#{issue_num}")
            else:
                print(f"   ❌ Invalid format: {entry}")
    
    elif choice == "3":
        # Edit mode
        if not final_links:
            print("No links to edit")
        else:
            print("\nCurrent links:")
            for i, link in enumerate(final_links, 1):
                print(f"   [{i}] {link.repo}#{link.issue_number}")
            print("   [d1, d2, ...] Delete specific links")
            print("   [r1=repo#num] Replace link")
            
            edit_choice = safe_input("Edit command: ").strip()
            if edit_choice.startswith('d'):
                # Delete
                indices = [int(x)-1 for x in edit_choice[1:].split(',') if x.strip().isdigit()]
                for idx in sorted(indices, reverse=True):
                    if 0 <= idx < len(final_links):
                        removed = final_links.pop(idx)
                        print(f"   🗑️ Removed {removed.repo}#{removed.issue_number}")
    
    return final_links


def build_related_section(links: List[CrossRepoLink]) -> str:
    """สร้าง ## Related section สำหรับ issue body"""
    if not links:
        return ""
    
    section = "\n## Related\n"
    seen = set()
    for link in links:
        key = f"{link.repo}#{link.issue_number}"
        if key not in seen:
            section += f"- {link.relationship}: {link.repo}#{link.issue_number}\n"
            seen.add(key)
    
    return section


def create_github_issue(
    repo: str,
    title: str,
    body: str,
    labels: List[str] = None,
    project_number: int = None
) -> Optional[Dict]:
    """
    สร้าง GitHub Issue ผ่าน gh CLI
    
    Returns:
        Dict with issue data หรือ None ถ้าล้มเหลว
    """
    # สร้าง issue
    cmd = [
        "api", "repos", repo, "issues",
        "--method", "POST",
        "-f", f"title={title}",
        "-f", f"body={body}"
    ]
    
    if labels:
        for label in labels:
            cmd.extend(["-f", f"labels[]={label}"])
    
    result = run_gh_command(cmd)
    
    if not result:
        return None
    
    try:
        issue = json.loads(result)
        
        # Add to project ถ้ามี project_number
        if project_number and issue.get("node_id"):
            add_issue_to_project(repo, issue["node_id"], project_number)
        
        return issue
    except json.JSONDecodeError:
        print("❌ Failed to parse issue creation response")
        return None


def add_issue_to_project(repo: str, issue_node_id: str, project_number: int) -> bool:
    """Add issue to GitHub Project board"""
    # ต้องใช้ GraphQL API
    query = """
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
        item {
          id
        }
      }
    }
    """
    
    # ดึง project ID
    owner, repo_name = repo.split('/')
    project_query = """
    query($owner: String!, $number: Int!) {
      user(login: $owner) {
        projectV2(number: $number) {
          id
        }
      }
    }
    """
    
    project_result = run_gh_graphql(project_query, {"owner": owner, "number": project_number})
    
    if not project_result or "errors" in project_result:
        # Check if this is a GitLab CLI limitation
        from luma_core.cli_wrapper import get_cli_wrapper
        wrapper = get_cli_wrapper()
        if wrapper.cli_tool == "glab":
            print("   🔄 GitLab repositories use different project management system")
            print("   📋 Skipping GitHub Project addition for GitLab")
            return False
        print(f"⚠️ Could not find project #{project_number}")
        return False
    
    project_id = project_result.get("data", {}).get("user", {}).get("projectV2", {}).get("id")
    
    if not project_id:
        return False
    
    result = run_gh_graphql(query, {"projectId": project_id, "contentId": issue_node_id})
    
    if result and "errors" not in result:
        print(f"   📌 Added to project #{project_number}")
        return True
    else:
        # Check if this is a GitLab CLI limitation
        from luma_core.cli_wrapper import get_cli_wrapper
        wrapper = get_cli_wrapper()
        if wrapper.cli_tool == "glab":
            print("   🔄 GitLab repositories use different project management system")
            print("   📋 Skipping GitHub Project addition for GitLab")
            return False
        return False
    
    return False


def action_create_issue(
    state: LumaState,
    project: dict,
    headless: bool = False,
    headless_args: dict = None
) -> bool:
    """
    สร้าง Issue พร้อม cross-repo link support
    
    Args:
        state: LumaState
        project: Project config dict
        headless: ถ้า True จะไม่ prompt interactive
        headless_args: Args สำหรับ headless mode (title, body, related_links, etc.)
    
    Returns:
        True ถ้าสำเร็จ
    """
    from luma_core.ui import safe_input
    
    repo = project.get("repo")
    if not repo:
        print("❌ Project has no repo configured")
        return False
    
    print(f"\n➕ Create New Issue for {project['name']}")
    print("─" * 50)
    
    # Get title
    if headless and headless_args:
        title = headless_args.get("title", "")
    else:
        title = safe_input("Issue title: ").strip()
    
    if not title:
        print("❌ Title is required")
        return False
    
    # Get body
    if headless and headless_args:
        body = headless_args.get("body", "")
    else:
        print("\nIssue body (Ctrl+D or type 'END' on new line to finish):")
        body_lines = []
        while True:
            try:
                line = input()
                if line.strip() == "END":
                    break
                body_lines.append(line)
            except EOFError:
                break
        body = "\n".join(body_lines)
    
    # Detect cross-repo links
    auto_detected = []
    
    # 1. From body
    auto_detected.extend(detect_zenith_issues_from_text(body))
    
    # 2. From branch name (ถ้ามี active branch)
    if state and state.active_branch:
        auto_detected.extend(detect_zenith_issues_from_branch(state.active_branch))
    
    # 3. From headless args (ถ้ามี manual links)
    if headless and headless_args and headless_args.get("related_links"):
        for link_str in headless_args.get("related_links", []):
            match = re.match(r'(?:https://github\.com/)?([^/]+/[^/#]+)/?#?(?:issues?/)?(\d+)', link_str)
            if match:
                repo_str = match.group(1)
                issue_num = int(match.group(2))
                auto_detected.append(CrossRepoLink(
                    repo=repo_str,
                    issue_number=issue_num,
                    url=f"https://github.com/{repo_str}/issues/{issue_num}",
                    relationship="Related"
                ))
    
    # Prompt for cross-repo links (ถ้าไม่ใช่ headless)
    final_links = auto_detected
    if not headless and auto_detected:
        final_links = prompt_cross_repo_links(auto_detected)
    
    # Build body with ## Related section
    body_with_related = body
    if final_links:
        related_section = build_related_section(final_links)
        # เช็คว่ายังไม่มี ## Related ใน body
        if "## Related" not in body:
            body_with_related = body + related_section
        else:
            # Merge กับ existing ## Related
            body_with_related = body  # TODO: Smart merge
    
    # Labels
    labels = []
    if headless and headless_args:
        labels = headless_args.get("labels", [])
    
    # Confirm ถ้าไม่ใช่ headless
    if not headless:
        print("\n" + "─" * 50)
        print(f"Title: {title}")
        print(f"Body preview:\n{body_with_related[:200]}...")
        if final_links:
            print(f"Cross-repo links: {len(final_links)}")
        confirm = safe_input("\nCreate issue? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Cancelled")
            return False
    
    # Create issue
    issue = create_github_issue(
        repo=repo,
        title=title,
        body=body_with_related,
        labels=labels,
        project_number=project.get("kanban_number")
    )
    
    if issue:
        print(f"✅ Issue created: {issue.get('html_url')}")
        
        # Post backlink comment to Zenith issues (ถ้ามี)
        for link in final_links:
            if "zenith" in link.repo.lower():
                post_backlink_comment(link, issue.get("html_url"), project.get("name"))
        
        return True
    else:
        print("❌ Failed to create issue")
        return False


def post_backlink_comment(target_link: CrossRepoLink, source_issue_url: str, source_project: str) -> bool:
    """
    Post comment กลับไปยัง Zenith issue เพื่อแสดง backlink
    """
    comment_body = f"🔗 **Referenced by** [{source_project}]({source_issue_url})"
    
    cmd = [
        "api", "repos", target_link.repo, "issues", str(target_link.issue_number), "comments",
        "--method", "POST",
        "-f", f"body={comment_body}"
    ]
    
    result = run_gh_command(cmd)
    
    if result:
        print(f"   💬 Posted backlink to {target_link.repo}#{target_link.issue_number}")
        return True
    
    return False


def action_create_issue_headless(project: dict, args: dict) -> dict:
    """
    Headless version สำหรับ CLI integration
    
    Args:
        project: Project config
        args: Dict with keys: title, body, related_links (list), labels (list)
    
    Returns:
        Result dict with status
    """
    from luma_core.state_manager import LumaState
    
    # Create minimal state
    state = LumaState(project_key=project.get("key", "unknown"))
    
    success = action_create_issue(
        state=state,
        project=project,
        headless=True,
        headless_args=args
    )
    
    return {
        "status": "success" if success else "error",
        "action": "create_issue",
        "project": project.get("key")
    }
