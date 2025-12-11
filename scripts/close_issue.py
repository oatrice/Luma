import os
import requests
import sys
from dotenv import load_dotenv

# Add parent dir to sys.path to find .env if needed, but load_dotenv handles it if in current dir?
# We are running from Luma/
load_dotenv()

def close_issue(repo, issue_number):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN not found.")
        return

    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    print(f"🔒 Closing Issue #{issue_number} in {repo}...")
    response = requests.patch(url, headers=headers, json={"state": "closed"})
    
    if response.status_code == 200:
        print(f"✅ Issue #{issue_number} Closed Successfully!")
        data = response.json()
        print(f"Status: {data['state']}")
    else:
        print(f"❌ Failed to close issue. Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    repo = "oatrice/Tetris-Battle"
    issue = 6 # Hardcoded based on context
    close_issue(repo, issue)
