"""GitLab client functions for merge requests and issues."""

import subprocess
import json
from .cli_wrapper import get_cli_wrapper

def create_merge_request(repo_name, title, body, source_branch, target_branch="main"):
    """Create a GitLab merge request using glab CLI."""
    try:
        wrapper = get_cli_wrapper('glab')
        
        # Create merge request command
        args = [
            'mr', 'create',
            '--title', title,
            '--description', body,
            '--source-branch', source_branch,
            '--target-branch', target_branch,
            '--repo', repo_name,
            '--yes'  # Auto-confirm
        ]
        
        output = wrapper.run_cli_command(args)
        
        # Extract URL from output
        # glab typically returns a URL in the output
        lines = output.strip().split('\n')
        for line in lines:
            if 'http' in line and ('merge_requests' in line or '-/merge_requests' in line):
                return line.strip()
        
        # If no URL found, try to parse from repo name
        return f"https://gitlab.com/{repo_name}/-/merge_requests"
        
    except subprocess.CalledProcessError as e:
        print(f"   Failed to create GitLab MR: {e.stderr}")
        return None
    except Exception as e:
        print(f"   Error creating GitLab MR: {e}")
        return None

def get_open_merge_request(repo_name, source_branch):
    """Check if there's an open merge request for the branch."""
    try:
        wrapper = get_cli_wrapper('glab')
        
        args = [
            'mr', 'list',
            '--source-branch', source_branch,
            '--state', 'opened',
            '--repo', repo_name,
            '--json', 'iid,web_url,title'
        ]
        
        output = wrapper.run_cli_command(args)
        
        if output.strip():
            mrs = json.loads(output)
            if mrs:
                # Return the first open MR
                mr = mrs[0]
                return {
                    'number': mr.get('iid'),
                    'url': mr.get('web_url'),
                    'title': mr.get('title')
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
