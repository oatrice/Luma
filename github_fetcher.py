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
    """ดึง Issue ทั้งหมดที่ Open จาก Repository"""
    url = f"https://api.github.com/repos/{repo_name}/issues?state=open"
    headers = get_github_headers()
    
    print(f"🌍 Connecting to GitHub: {repo_name}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        issues = response.json()
        
        # Filter out Pull Requests (GitHub API returns PRs as issues)
        real_issues = [i for i in issues if "pull_request" not in i]
        return real_issues
        
    except Exception as e:
        print(f"❌ Error fetching issues: {e}")
        return []

def select_issue(issues):
    """ให้ User เลือก Issue จากรายการ"""
    if not issues:
        print("📭 No open issues found.")
        return None
        
    print("\n--- 🐙 Open GitHub Issues ---")
    for idx, issue in enumerate(issues):
        print(f"[{idx+1}] #{issue['number']}: {issue['title']}")
    
    while True:
        try:
            selection = input("\nSelect Issue Number (or 0 to cancel): ").strip()
            if selection == '0':
                return None
            
            idx = int(selection) - 1
            if 0 <= idx < len(issues):
                return issues[idx]
            else:
                print("❌ Invalid selection.")
        except ValueError:
            print("❌ Please enter a number.")

def convert_to_task(issue):
    """แปลง Issue เป็น format prompt สำหรับ Luma"""
    return f"""
    Title: {issue['title']}
    Review Issue Link: {issue['html_url']}
    
    Description:
    {issue['body']}
    """
