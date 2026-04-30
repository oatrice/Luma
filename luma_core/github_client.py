import os
import subprocess
import re

import requests
from luma_core.cli_wrapper import get_cli_wrapper

from . import config


_GITHUB_ACCEPT_HEADER = "application/vnd.github.v3+json"


def _build_github_headers(token=None):
    headers = {"Accept": _GITHUB_ACCEPT_HEADER}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_configured_github_token():
    return os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or config.GITHUB_TOKEN


def _get_gh_cli_token():
    try:
        wrapper = get_cli_wrapper()
        result = wrapper.run_cli_command(["auth", "token"])
        return result.strip()
    except subprocess.CalledProcessError:
        return None


def _get_github_auth_tokens():
    tokens = []
    for token in (_get_configured_github_token(), _get_gh_cli_token()):
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def _request_with_github_auth(request_func, url, retry_on_401=False, **kwargs):
    auth_tokens = _get_github_auth_tokens()
    if not auth_tokens:
        return request_func(url, headers=_build_github_headers(), **kwargs)

    last_response = None
    for index, token in enumerate(auth_tokens):
        last_response = request_func(
            url,
            headers=_build_github_headers(token),
            **kwargs,
        )
        should_retry = (
            retry_on_401
            and last_response.status_code == 401
            and index < len(auth_tokens) - 1
        )
        if should_retry:
            print(
                "⚠️ GitHub API returned 401 with the configured token. "
                "Retrying with gh CLI token..."
            )
            continue
        return last_response

    return last_response

def get_github_headers():
    tokens = _get_github_auth_tokens()
    if not tokens:
        print("⚠️ Warning: GITHUB_TOKEN not found. Public rate limits apply.")
        return _build_github_headers()
    return _build_github_headers(tokens[0])

def fetch_issues_rest(repo_name):
    """Fallback: Fetch all issues via REST API (if GraphQL is unavailable)"""
    url = f"https://api.github.com/repos/{repo_name}/issues?state=open"
    print(f"🌍 Connecting to GitHub REST API: {repo_name}...")
    try:
        response = _request_with_github_auth(
            requests.get,
            url,
            retry_on_401=True,
            timeout=10,
        )
        response.raise_for_status()
        issues = response.json()
        
        # Filter out Pull Requests (GitHub API returns PRs as issues)
        real_issues = [i for i in issues if "pull_request" not in i]
        return real_issues
    except Exception as e:
        print(f"⚠️ REST API Fetch failed: {e}")
        return []

def create_issue(repo_name: str, title: str, body: str, labels: list = None) -> dict:
    """Create a new GitHub issue using gh CLI and return the result."""
    gh_args = ["issue", "create", "--title", title, "--body", body]
    if repo_name:
        gh_args.extend(["--repo", repo_name])
    if labels:
        for label in labels:
            gh_args.extend(["--label", label])

    try:
        # We need the output to get the URL of the created issue
        wrapper = get_cli_wrapper()
        output = wrapper.run_cli_command(gh_args).strip()
        # Usually 'gh issue create' returns the URL of the created issue
        # e.g. https://github.com/owner/repo/issues/123
        issue_url = output
        issue_number = None
        match = re.search(r"/issues/(\d+)", issue_url)
        if match:
            issue_number = int(match.group(1))

        return {
            "success": True,
            "url": issue_url,
            "number": issue_number,
            "title": title
        }
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        return {
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def fetch_issues(repo_name):
    """
    Main Entry: Try GraphQL (Ready Lane) -> Fallback to REST (All Open)
    """
    # 1. Try GraphQL first
    try:
        issues = fetch_issues_graphql(repo_name)
        if issues:
            return issues
    except Exception:
        pass
        
    # 2. If GraphQL failed or empty, fallback
    print("⚠️ Fallback: Fetching ALL open issues (could not access Project Board).")
    return fetch_issues_rest(repo_name)

def fetch_issues_graphql(repo_name):
    """
    Fetch all issues from Repository and Filter only those in Kanban Lane 'Ready'
    using GitHub GraphQL API (Supports Projects V2)
    """
    # Split owner/repo
    try:
        owner, name = repo_name.split("/")
    except ValueError:
        print("❌ Invalid repo format. Use 'owner/repo'.")
        return []

    url = "https://api.github.com/graphql"
    # GraphQL Query
    query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        issues(first: 50, states: OPEN) {
          nodes {
            number
            title
            body
            url
            projectItems(first: 5) {
              nodes {
                id 
                project {
                    id
                }
                fieldValues(first: 10) {
                  nodes {
                    ... on ProjectV2ItemFieldSingleSelectValue {
                      name
                      field {
                        ... on ProjectV2FieldCommon {
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    variables = {"owner": owner, "name": name}
    
    print(f"🌍 Connecting to GitHub GraphQL: {repo_name} (Filter: Status='Ready')...")
    try:
        response = _request_with_github_auth(
            requests.post,
            url,
            retry_on_401=True,
            json={"query": query, "variables": variables},
            timeout=10,
        )
        
        if response.status_code == 401:
            print("❌ Unauthorized. Please check your GITHUB_TOKEN.")
            return []
            
        if response.status_code != 200:
             # Let main fetcher handle fallback
             return []

        data = response.json()
        
        if "errors" in data:
            msg = data['errors'][0]['message']
            print(f"❌ GraphQL Error: {msg}")
            
            if "Resource not accessible by personal access token" in msg:
                 print("\n   💡 DIAGNOSIS: Missing Permissions")
                 print("   The token works for the Repo, but cannot access 'Project Board' data.")
                 print("   👉 Fix for Fine-grained Token:")
                 print("      1. Go to GitHub > Settings > Developer Settings > Fine-grained tokens")
                 print("      2. Select this token")
                 print("      3. Permissions > Repository permissions")
                 print("      4. Ensure 'Projects' is set to 'Read and Write' (or Read-only)")
                 print("      5. Ensure 'Issues' is 'Read and Write'")
            
            print("   (Switching to REST API fallback...)\n")
            return [] # This will trigger fallback
    
        raw_issues = data.get("data", {}).get("repository", {}).get("issues", {}).get("nodes", [])
        
        # Define allowed start statuses (Case-insensitive matching logic below handles variations if needed)
        ACCEPTED_START_STATUSES = ["Ready"]
        
        ready_issues = []
        for issue in raw_issues:
            # Check Project Status
            is_ready = False
            project_items = issue.get("projectItems", {}).get("nodes", [])
            
            for item in project_items:
                # Capture IDs for updating status later
                # We need checking if this item belongs to the correct project (usually the first one is fine for 1:1)
                
                field_values = item.get("fieldValues", {}).get("nodes", [])
                
                # Check for "Ready" or equivalent status
                for fv in field_values:
                    if fv.get("name") in ACCEPTED_START_STATUSES:
                        is_ready = True
                        break
                
                if is_ready: 
                    # Store IDs
                    issue['project_item_id'] = item.get("id") 
                    issue['project_id'] = item.get("project", {}).get("id")
                    break
            
            if is_ready:
                issue['html_url'] = issue['url'] 
                ready_issues.append(issue)
        
        if not ready_issues:
            print(f"⚠️ No issues found in columns: {ACCEPTED_START_STATUSES}")
            
        return ready_issues

    except Exception as e:
        print(f"❌ Error fetching graphql: {e}")
        return []

def update_issue_status(issue, status_name="In Progress"):
    """
    Update the status of an issue in GitHub Project V2.
    """
    item_id = issue.get("project_item_id")
    project_id = issue.get("project_id")
    
    if not item_id or not project_id:
        print("⚠️ Issue data missing Project IDs. Cannot update status.")
        return

    print(f"🔄 Moving Issue '{issue['title']}' to '{status_name}'...")
    
    url = "https://api.github.com/graphql"

    # Step 1: Find Field ID and Option ID
    schema_query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 20) {
            nodes {
              ... on ProjectV2FieldSingleSelect {
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
    
    try:
        resp = _request_with_github_auth(
            requests.post,
            url,
            retry_on_401=True,
            json={"query": schema_query, "variables": {"projectId": project_id}},
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"❌ Failed to fetch project schema: {resp.text}")
            return
            
        data = resp.json()
        fields = data.get("data", {}).get("node", {}).get("fields", {}).get("nodes", [])
        
        status_field = None
        target_option = None
        
        for field in fields:
            if field.get("name") == "Status":
                status_field = field
                # Find Option
                for opt in field.get("options", []):
                    if opt.get("name").lower() == status_name.lower():
                        target_option = opt
                        break
                break
        
        if not status_field or not target_option:
            print(f"❌ Could not find Status field or Option '{status_name}' in project.")
            return
            
        # Step 2: Mutate
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
        
        vars = {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": status_field["id"],
            "optionId": target_option["id"]
        }
        
        resp_mut = _request_with_github_auth(
            requests.post,
            url,
            retry_on_401=True,
            json={"query": mutation, "variables": vars},
            timeout=10,
        )
        
        if resp_mut.status_code == 200 and "errors" not in resp_mut.json():
            print(f"✅ Status updated to '{status_name}'")
        else:
            print(f"❌ Failed to update status: {resp_mut.text}")

    except Exception as e:
        print(f"❌ Error updating status: {e}") 

def create_pull_request(repo_name, title, body, head_branch, base_branch="main"):
    """
    Create a Pull Request via GitHub API
    """
    owner, name = repo_name.split("/")
    url = f"https://api.github.com/repos/{owner}/{name}/pulls"
    payload = {
        "title": title,
        "body": body,
        "head": head_branch,
        "base": base_branch
    }
    
    print(f"🌍 Creating PR on {repo_name} ({head_branch} -> {base_branch})...")
    try:
        response = _request_with_github_auth(
            requests.post,
            url,
            retry_on_401=True,
            json=payload,
            timeout=10,
        )
        
        if response.status_code == 201:
            pr_data = response.json()
            print(f"✅ PR Created Successfully: {pr_data['html_url']}")
            return pr_data['html_url']
        else:
            print(f"❌ Failed to create PR: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating PR: {e}")
        return None

def get_open_pr(repo_name, head_branch):
    """
    Check if there is an open PR for the given head branch.
    Returns the PR object (dict) or None.
    """
    owner, name = repo_name.split("/")
    # GitHub API expects head as 'user:branch'
    url = f"https://api.github.com/repos/{owner}/{name}/pulls?head={owner}:{head_branch}&state=open"
    try:
        response = _request_with_github_auth(
            requests.get,
            url,
            retry_on_401=True,
            timeout=10,
        )
        if response.status_code == 200:
            prs = response.json()
            if prs:
                return prs[0] # Return the first matching open PR
        return None
    except Exception as e:
        print(f"⚠️ Error checking for open PR: {e}")
        return None

def update_pull_request(repo_name, pr_number, title=None, body=None):
    """
    Update an existing Pull Request.
    """
    owner, name = repo_name.split("/")
    url = f"https://api.github.com/repos/{owner}/{name}/pulls/{pr_number}"
    payload = {}
    if title:
        payload["title"] = title
    if body:
        payload["body"] = body
    
    if not payload:
        return None
        
    print(f"🌍 Updating PR #{pr_number} on {repo_name}...")
    try:
        response = _request_with_github_auth(
            requests.patch,
            url,
            retry_on_401=True,
            json=payload,
            timeout=10,
        )
        
        if response.status_code == 200:
            pr_data = response.json()
            print(f"✅ PR Updated Successfully: {pr_data['html_url']}")
            return pr_data['html_url']
        else:
            print(f"❌ Failed to update PR: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error updating PR: {e}")
        return None
