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
            # Convert git@gitlab.com:owner/repo.git to https://gitlab.com/owner/repo
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
            # Check if owner/repo suggests a platform (this is heuristic)
            # For now, we'll try git remote detection first
            pass
        
        # Try to detect from git remote
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
                return detect_repo_platform_from_remote(remote_url)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Default to GitHub if we can't detect
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
