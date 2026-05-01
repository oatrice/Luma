"""Platform detection and unified PR/MR creation functionality."""

import re
from urllib.parse import urlparse
from typing import Optional, Tuple


def detect_repo_platform(repo_url: str) -> str:
    """
    Detect the platform (GitHub or GitLab) from a repository URL.
    
    Args:
        repo_url: Repository URL (can be https://, git@, or just owner/repo format)
        
    Returns:
        'github' or 'gitlab'
    """
    if not repo_url:
        return 'github'  # Default to GitHub
    
    # Parse URL if it's a full URL
    if repo_url.startswith(('http://', 'https://', 'git@')):
        original_url = repo_url
        if repo_url.startswith('git@'):
            # Convert git@github.com:owner/repo.git to https://github.com/owner/repo
            # First extract the domain part between git@ and the colon
            domain_part = repo_url[4:].split(':')[0]  # Remove 'git@' and split at ':'
            if 'gitlab' in domain_part.lower():
                return 'gitlab'
            elif 'github' in domain_part.lower():
                return 'github'
            else:
                # Default to GitHub for unknown domains
                return 'github'
        else:
            parsed = urlparse(repo_url)
            domain = parsed.netloc.lower()
            
            if 'gitlab' in domain:
                return 'gitlab'
            elif 'github' in domain:
                return 'github'
            else:
                # Default to GitHub for unknown domains
                return 'github'
    else:
        # For owner/repo format, check if it contains platform indicators
        if '/' in repo_url:
            owner, repo = repo_url.split('/', 1)
            # Check if owner name suggests a platform (heuristic)
            if 'gitlab' in owner.lower():
                return 'gitlab'
            elif 'github' in owner.lower():
                return 'github'
            # Special case: if owner ends with 'dev', it's likely a GitLab dev account
            elif owner.lower().endswith('dev'):
                return 'gitlab'
            # For plain owner/repo format, default to GitHub unless git remote clearly indicates GitLab
            # This is the most common case - most repos are GitHub unless explicitly GitLab
        
        # Try to detect from git remote ONLY if we haven't already determined
        # AND only for cases that clearly indicate GitLab
        try:
            import subprocess
            # Try to get the remote URL from git
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                remote_url = result.stdout.strip()
                detected_from_remote = detect_repo_platform_from_remote(remote_url)
                # Only use git remote if:
                # 1. It clearly indicates GitLab AND
                # 2. The input repo name suggests GitLab (owner contains gitlab or ends with dev)
                # This prevents GitLab environment from overriding GitHub repos
                if (detected_from_remote == 'gitlab' and 
                    ('gitlab' in repo_url.lower() or repo_url.split('/')[0].lower().endswith('dev'))):
                    return 'gitlab'
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Default to GitHub for owner/repo format (most common case)
        return 'github'


def detect_repo_platform_from_remote(remote_url: str) -> str:
    """
    Detect platform from git remote URL.
    
    Args:
        remote_url: Git remote URL (e.g., https://gitlab.com/user/repo.git)
        
    Returns:
        'github' or 'gitlab'
    """
    return detect_repo_platform(remote_url)


def create_pull_request_unified(repo_name: str, title: str, body: str, head_branch: str, base_branch: str = "main", platform: Optional[str] = None):
    """
    Unified function to create PR/MR based on platform detection.
    
    Args:
        repo_name: Repository name in format 'owner/repo'
        title: PR/MR title
        body: PR/MR body/description
        head_branch: Source branch
        base_branch: Target branch (default: 'main')
        platform: Optional platform override ('github' or 'gitlab')
        
    Returns:
        URL of created PR/MR or None if failed
    """
    if platform is None:
        # Try to detect platform from repository name or assume GitHub
        platform = detect_repo_platform(repo_name)
    
    print(f"🔍 Detected platform: {platform}")
    
    if platform == 'gitlab':
        from .gitlab_client import create_merge_request
        return create_merge_request(repo_name, title, body, head_branch, base_branch)
    else:
        from .github_client import create_pull_request
        return create_pull_request(repo_name, title, body, head_branch, base_branch)


def get_open_pr_unified(repo_name: str, head_branch: str, platform: Optional[str] = None):
    """
    Unified function to check for existing open PR/MR.
    
    Args:
        repo_name: Repository name in format 'owner/repo'
        head_branch: Source branch to check
        platform: Optional platform override ('github' or 'gitlab')
        
    Returns:
        PR/MR object or None if not found
    """
    if platform is None:
        platform = detect_repo_platform(repo_name)
    
    if platform == 'gitlab':
        from .gitlab_client import get_open_merge_request
        return get_open_merge_request(repo_name, head_branch)
    else:
        from .github_client import get_open_pr
        return get_open_pr(repo_name, head_branch)


def update_pull_request_unified(repo_name: str, pr_number: int, title: Optional[str] = None, body: Optional[str] = None, platform: Optional[str] = None):
    """
    Unified function to update existing PR/MR.
    
    Args:
        repo_name: Repository name in format 'owner/repo'
        pr_number: PR/MR number
        title: Optional new title
        body: Optional new body/description
        platform: Optional platform override ('github' or 'gitlab')
        
    Returns:
        URL of updated PR/MR or None if failed
    """
    if platform is None:
        platform = detect_repo_platform(repo_name)
    
    if platform == 'gitlab':
        from .gitlab_client import update_merge_request
        return update_merge_request(repo_name, pr_number, title, body)
    else:
        from .github_client import update_pull_request
        return update_pull_request(repo_name, pr_number, title, body)


def check_pr_status_unified(pr_url: str) -> dict:
    """
    Unified function to check PR/MR status for both GitHub and GitLab.
    
    Args:
        pr_url: Full PR/MR URL
        
    Returns:
        {"merged": True/False, "state": "open|closed|merged", "error": None|str}
    """
    import re
    import json
    
    # Check if it's a GitLab MR URL
    gitlab_match = re.match(r'https://gitlab\.com/([^/]+)/([^/]+)/-/merge_requests/(\d+)', pr_url)
    if gitlab_match:
        owner, repo, mr_number = gitlab_match.groups()
        try:
            from .cli_wrapper import get_cli_wrapper
            wrapper = get_cli_wrapper("glab")
            
            # Use glab to get MR status (no --json flag available)
            args = ["mr", "view", mr_number, "--repo", f"{owner}/{repo}"]
            output = wrapper.run_cli_command(args)
            
            if output.strip():
                # Parse output to extract state
                # glab mr view output contains lines like "State: opened"
                state = "unknown"
                for line in output.split('\n'):
                    line_lower = line.lower().strip()
                    if line_lower.startswith('state:'):
                        state = line_lower.replace('state:', '').strip()
                        break
                
                state = state.lower()
                if state == "merged":
                    return {"merged": True, "state": "merged", "error": None}
                elif state in ["opened", "closed", "locked"]:
                    return {"merged": False, "state": state, "error": None}
                else:
                    return {"merged": False, "state": state, "error": None}
            else:
                return {"merged": False, "state": "unknown", "error": "MR not found or access denied"}
                
        except Exception as e:
            error_str = str(e)
            # Check if it's an authentication error
            if "401" in error_str or "unauthorized" in error_str.lower():
                return {"merged": False, "state": "unknown", "error": "GitLab authentication failed"}
            elif "404" in error_str or "not found" in error_str.lower():
                return {"merged": False, "state": "unknown", "error": "MR not found"}
            elif "returned non-zero exit status" in error_str:
                # Extract more specific error from subprocess
                if hasattr(e, 'stderr') and e.stderr:
                    stderr = e.stderr
                    if "404" in stderr or "Not Found" in stderr:
                        return {"merged": False, "state": "unknown", "error": "MR not found"}
                    elif "401" in stderr or "unauthorized" in stderr.lower():
                        return {"merged": False, "state": "unknown", "error": "GitLab authentication failed"}
                return {"merged": False, "state": "unknown", "error": "MR not found or access denied"}
            else:
                return {"merged": False, "state": "unknown", "error": f"Failed to check MR: {error_str}"}
    
    # Check if it's a GitHub PR URL
    github_match = re.match(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
    if github_match:
        owner, repo, pr_number = github_match.groups()
        try:
            from .cli_wrapper import get_cli_wrapper
            wrapper = get_cli_wrapper("gh")
            
            # Use gh to get PR status
            args = ["pr", "view", pr_number, "--repo", f"{owner}/{repo}", "--json", "state"]
            output = wrapper.run_cli_command(args)
            
            if output.strip():
                data = json.loads(output)
                state = data.get("state", "unknown").lower()
                
                if state == "merged":
                    return {"merged": True, "state": "merged", "error": None}
                else:
                    return {"merged": False, "state": state, "error": None}
            else:
                return {"merged": False, "state": "unknown", "error": "PR not found or access denied"}
                
        except json.JSONDecodeError:
            return {"merged": False, "state": "unknown", "error": "Failed to parse PR response"}
        except Exception as e:
            # Check if it's an authentication error
            if "401" in str(e) or "unauthorized" in str(e).lower():
                return {"merged": False, "state": "unknown", "error": "GitHub authentication failed"}
            elif "404" in str(e) or "not found" in str(e).lower():
                return {"merged": False, "state": "unknown", "error": "PR not found"}
            else:
                return {"merged": False, "state": "unknown", "error": f"Failed to check PR: {str(e)}"}
    
    # If neither format matches
    return {"merged": False, "state": "unknown", "error": "Invalid PR/MR URL"}
