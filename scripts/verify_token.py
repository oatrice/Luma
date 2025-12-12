
import os
import requests
import json
from dotenv import load_dotenv

# Load .env
load_dotenv()

def get_headers():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ No GITHUB_TOKEN found.")
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def run_query(label, query, variables=None):
    url = "https://api.github.com/graphql"
    headers = get_headers()
    if not headers: return False

    print(f"🔍 Testing {label}...")
    try:
        response = requests.post(url, headers=headers, json={"query": query, "variables": variables}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "errors" in data:
                print(f"   ❌ Failed: {data['errors'][0]['message']}")
                return False
            else:
                print(f"   ✅ Success")
                return True
        else:
            print(f"   ❌ HTTP Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def verify_token_capabilities():
    repo_owner = "oatrice" 
    repo_name = "Tetris-Battle"
    
    # 1. Check Identity (viewer)
    q_viewer = """
    query {
      viewer {
        login
      }
    }
    """
    if not run_query("Viewer Identity (Auth Check)", q_viewer):
        print("\n⚠️  Token is invalid or has no basic access.")
        return

    # 2. Check Repository Access (Issues)
    q_repo = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        name
        issues(first: 1) {
          totalCount
        }
      }
    }
    """
    if not run_query("Repository Access (Read Issues)", q_repo, {"owner": repo_owner, "name": repo_name}):
        print("\n⚠️  Token cannot read repository issues. Check 'Contents' or 'Issues' permission.")
        return

    # 3. Check Project Access
    q_project = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        issues(first: 1) {
          nodes {
            projectItems(first: 1) {
              nodes {
                 id
              }
            }
          }
        }
      }
    }
    """
    if not run_query("Project Access (Read Project Items)", q_project, {"owner": repo_owner, "name": repo_name}):
        print("\n🚩 PROBLEM FOUND: Token allows Repo access but DENIES Project access.")
        print("👉 For Fine-grained Tokens:")
        print("   1. Go to Developer Settings > Personal access tokens > Fine-grained tokens.")
        print("   2. Select your token.")
        print("   3. Under 'Repository permissions', ensure 'Issues' is 'Read and Write'.")
        print("   4. **CRITICAL**: Check if there is a 'Projects' permission. If logic is 'Repository Projects', enable it.")
        print("   5. NOTE: Use of Organization Projects (Projects V2) might require Organization-level permissions, not just Repository permissions.")
        
if __name__ == "__main__":
    verify_token_capabilities()
