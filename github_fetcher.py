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

def fetch_issues(repo_name):
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
    
    # GraphQL Query to fetch issues and their Project Status
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
            
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            print(f"❌ GraphQL Error: {data['errors'][0]['message']}")
            print("   (Hint: Ensure your Token has 'project' scope)")
            return []
            
        raw_issues = data.get("data", {}).get("repository", {}).get("issues", {}).get("nodes", [])
        
        ready_issues = []
        for issue in raw_issues:
            # Check Project Status
            is_ready = False
            project_items = issue.get("projectItems", {}).get("nodes", [])
            
            for item in project_items:
                field_values = item.get("fieldValues", {}).get("nodes", [])
                for fv in field_values:
                    # Check if any field value is explicitly "Ready"
                    # This covers "Status", "Pipeline", etc.
                    if fv.get("name") == "Ready":
                        is_ready = True
                        break
                if is_ready: break
            
            if is_ready:
                # Normalize keys to match REST API format used in other functions
                issue['html_url'] = issue['url'] 
                ready_issues.append(issue)
        
        if not ready_issues:
            print("⚠️ No issues found in 'Ready' lane.")
            
        return ready_issues

    except Exception as e:
        print(f"❌ Error fetching issues: {e}")
        return []

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
