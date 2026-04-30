"""GitLab client functions for merge requests and issues."""

import subprocess
import json
from .cli_wrapper import get_cli_wrapper

def create_merge_request(repo_name, title, body, source_branch, target_branch="main"):
    """Create a GitLab merge request using glab CLI."""
    try:
        wrapper = get_cli_wrapper('glab')
        
        # Create merge request command - simplified flags
        args = [
            'mr', 'create',
            '--title', title,
            '--description', body,
            '--source-branch', source_branch,
            '--target-branch', target_branch
        ]
        
        output = wrapper.run_cli_command(args)
        
        # Extract URL from output
        lines = output.strip().split('\n')
        for line in lines:
            if 'http' in line and ('merge_requests' in line or '-/merge_requests' in line):
                return line.strip()
        
        # If no URL found, construct URL from branch name
        return f"https://gitlab.com/{repo_name}/-/merge_requests/new?merge_request[source_branch]={source_branch}"
        
    except subprocess.CalledProcessError as e:
        stderr = e.stderr or ""
        # Check if MR already exists and extract the number
        if "409" in stderr and "already exists for this source branch:" in stderr:
            import re
            # Extract MR number from error like "Another open merge request already exists for this source branch: !91"
            match = re.search(r'!(\d+)', stderr)
            if match:
                mr_number = match.group(1)
                url = f"https://gitlab.com/{repo_name}/-/merge_requests/{mr_number}"
                print(f"   Found existing MR #{mr_number}")
                return url
        
        print(f"   Failed to create GitLab MR: {stderr}")
        return None
    except Exception as e:
        print(f"   Error creating GitLab MR: {e}")
        return None

def get_open_merge_request(repo_name, source_branch):
    """Check if there's an open merge request for the branch."""
    try:
        wrapper = get_cli_wrapper('glab')
        
        # Try to get MR list without source branch filter first
        args = ['mr', 'list', '--repo', repo_name]
        
        output = wrapper.run_cli_command(args)
        
        if output.strip():
            # Parse output to find MR info for our branch
            lines = output.strip().split('\n')
            for line in lines:
                # Look for lines that contain MR numbers and our branch
                if '!' in line and (source_branch in line or any(word in line for word in source_branch.split('-'))):
                    # Extract MR number from line like "!123 Merge request"
                    parts = line.split()
                    for part in parts:
                        if part.startswith('!'):
                            mr_number = part[1:]  # Remove '!'
                            # Construct URL
                            url = f"https://gitlab.com/{repo_name}/-/merge_requests/{mr_number}"
                            return {
                                'number': mr_number,
                                'url': url,
                                'title': line.strip()
                            }
        
        return None
        
    except subprocess.CalledProcessError as e:
        print(f"   Failed to check open GitLab MRs: {e.stderr}")
        return None
    except Exception as e:
        print(f"   Error checking GitLab MRs: {e}")
        return None

def update_merge_request(repo_name, mr_number, title=None, body=None):
    """Update an existing GitLab merge request."""
    try:
        wrapper = get_cli_wrapper('glab')
        
        args = ['mr', 'edit', str(mr_number), '--repo', repo_name]
        
        if title:
            args.extend(['--title', title])
        if body:
            args.extend(['--description', body])
        
        output = wrapper.run_cli_command(args)
        
        # Try to extract URL from output
        lines = output.strip().split('\n')
        for line in lines:
            if 'http' in line and ('merge_requests' in line or '-/merge_requests' in line):
                return line.strip()
        
        # Fallback: construct URL
        return f"https://gitlab.com/{repo_name}/-/merge_requests/{mr_number}"
        
    except subprocess.CalledProcessError as e:
        print(f"   Failed to update GitLab MR: {e.stderr}")
        return None
    except Exception as e:
        print(f"   Error updating GitLab MR: {e}")
        return None
