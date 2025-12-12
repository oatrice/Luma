import os
import requests
import json

def get_github_headers():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("⚠️ Warning: GITHUB_TOKEN not found. Public rate limits apply.")
        return {}
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def fetch_issues_rest(repo_name):
    """Fallback: ดึง Issue ทั้งหมดผ่าน REST API (กรณี GraphQL ใช้ไม่ได้)"""
    url = f"https://api.github.com/repos/{repo_name}/issues?state=open"
    headers = get_github_headers()
    
    print(f"🌍 Connecting to GitHub REST API: {repo_name}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        issues = response.json()
        
        # Filter out Pull Requests
        real_issues = [i for i in issues if "pull_request" not in i]
        return real_issues
    except Exception as e:
        print(f"❌ REST API Error: {e}")
        return []

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
        
    # 2. If GraphQL failed or empty, confirm with user or just do it? 
    # For smooth UX, let's just fallback with a warning.
    print("⚠️ Fallback: Fetching ALL open issues (could not access Project Board).")
    return fetch_issues_rest(repo_name)

def fetch_issues_graphql(repo_name):
    """
    ดึง Issue ทั้งหมดจาก Repository และ Filter เฉพาะที่อยู่ใน Kanban Lane 'Ready'
    โดยใช้ GitHub GraphQL API (รองรับ Projects V2)
    """
    # Split owner/repo
    try:
        owner, name = repo_name.split("/")
    except ValueError:
        print("❌ Invalid repo format. Use 'owner/repo'.")
        return []

    url = "https://api.github.com/graphql"
    headers = get_github_headers()
    
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
        response = requests.post(url, headers=headers, json={"query": query, "variables": variables}, timeout=10)
        
        if response.status_code == 401:
            print("❌ Unauthorized. Please check your GITHUB_TOKEN.")
            return []
            
        if response.status_code != 200:
             # Let main fetcher handle fallback
             return []

        data = response.json()
        
        if "errors" in data:
            print(f"❌ GraphQL Error: {data['errors'][0]['message']}")
            print("   (Hint: Ensure your Token has 'project' scope)")
            return [] # This will trigger fallback
    
        raw_issues = data.get("data", {}).get("repository", {}).get("issues", {}).get("nodes", [])
        
        # Define allowed start statuses (Case-insensitive matching logic below handles variations if needed)
        ACCEPTED_START_STATUSES = ["Ready", "Todo", "To Do", "Backlog", "Open"]
        
        ready_issues = []
        for issue in raw_issues:
            # Check Project Status
            is_ready = False
            project_items = issue.get("projectItems", {}).get("nodes", [])
            
            for item in project_items:
                # Capture IDs for updating status later
                # We need checking if this item belongs to the correct project (usually the first one is fine for 1:1)
                
                # Check formatting:
                # projectItems -> nodes -> ...
                
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
    
    headers = get_github_headers()
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
        resp = requests.post(url, headers=headers, json={"query": schema_query, "variables": {"projectId": project_id}}, timeout=10)
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
        
        resp_mut = requests.post(url, headers=headers, json={"query": mutation, "variables": vars}, timeout=10)
        
        if resp_mut.status_code == 200 and "errors" not in resp_mut.json():
            print(f"✅ Status updated to '{status_name}'")
        else:
            print(f"❌ Failed to update status: {resp_mut.text}")

    except Exception as e:
        print(f"❌ Error updating status: {e}") 

def select_issue(issues, ai_advisor=None):
    """
    ให้ User เลือก Issue จากรายการ
    ai_advisor: ฟังก์ชัน (callback) สำหรับขอความเห็นจาก AI (รับ parameter เป็น list ของ issues)
    """
    if not issues:
        print("📭 No open issues found.")
        return None
        
    while True:
        print("\n--- 🐙 Open GitHub Issues (Ready Lane) ---")
        for idx, issue in enumerate(issues):
            print(f"[{idx+1}] #{issue['number']}: {issue['title']}")
        
        print("-" * 30)
        options_text = "Select Issue Number"
        if ai_advisor:
            print("[A] 🤖 Ask AI for Prioritization Advice")
        print("[0] Cancel")
        
        selection = input(f"\n{options_text}: ").strip().lower()
        
        if selection == '0':
            return None
        
        if selection == 'a' and ai_advisor:
            print("\n🤖 Luma is analyzing tasks...")
            ai_advisor(issues)
            input("\nPress Enter to continue...")
            continue
            
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(issues):
                return issues[idx]
            else:
                print("❌ Invalid selection.")
        except ValueError:
            print("❌ Invalid input.")

def convert_to_task(issue):
    """แปลง Issue เป็น format prompt สำหรับ Luma"""
    return f"""
    Title: {issue['title']}
    Review Issue Link: {issue['html_url']}
    
    Description:
    {issue['body']}
    """

def create_pull_request(repo_name, title, body, head_branch, base_branch="main"):
    """
    สร้าง Pull Request ผ่าน GitHub API
    """
    owner, name = repo_name.split("/")
    url = f"https://api.github.com/repos/{owner}/{name}/pulls"
    headers = get_github_headers()
    
    payload = {
        "title": title,
        "body": body,
        "head": head_branch,
        "base": base_branch
    }
    
    print(f"🌍 Creating PR on {repo_name} ({head_branch} -> {base_branch})...")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
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
