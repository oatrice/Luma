import os
import json
import subprocess
from langchain_core.messages import HumanMessage
from ..state import AgentState
from ..llm import get_llm
from ..config import TARGET_DIR

# Try importing github tools
try:
    from github_fetcher import get_open_pr, create_pull_request, update_pull_request, update_issue_status
except ImportError:
    get_open_pr = None

def publisher_agent(state: AgentState):
    """Publisher: Pushes Code, Creates PRs"""
    print("🚀 Auto-Deploy / Publisher Agent...")
    
    if not get_open_pr:
        print("⚠️ GitHub tools not compiled/available. Skipping PR creation.")
        return {}

    # 1. Commit implementation? 
    # The 'Writer' handles file writing. 
    # Publisher handles the Git interactions.
    
    branch_name = "feat/luma-auto" # Default fallback
    if state.get('issue_data'):
        # Derive branch from issue
        issue = state['issue_data']
        safe_title = issue['title'].lower().replace(" ", "-")
        branch_name = f"feat/issue-{issue['number']}-{safe_title}"[:50]
        
    print(f"🌲 Managing Branch: {branch_name}")
    
    # 2. Add & Commit
    try:
        # Check if we are on the branch
        res = subprocess.run(["git", "branch", "--show-current"], cwd=TARGET_DIR, capture_output=True, text=True)
        current = res.stdout.strip()
        
        if current != branch_name:
             # Create/Checkout
             print(f"   Switching to {branch_name}...")
             subprocess.run(["git", "checkout", "-b", branch_name], cwd=TARGET_DIR, capture_output=True) # Try create
             subprocess.run(["git", "checkout", branch_name], cwd=TARGET_DIR, capture_output=True) # Try switch
            
        subprocess.run(["git", "add", "."], cwd=TARGET_DIR, check=True)
        commit_msg = f"feat: {state['task'][:50]}..."
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=TARGET_DIR)
        
    except Exception as e:
        print(f"⚠️ Git Local Ops failed: {e}")
        return {}

    # 3. Generate PR Body
    llm = get_llm(temperature=0.5)
    
    # Check for Template
    body = state['task']
    template_path = os.path.join(TARGET_DIR, ".github", "pull_request_template.md")
    
    if os.path.exists(template_path):
        with open(template_path, "r") as f:
            template = f.read()
        # Basic replacement
        body = template.replace("<!-- Brief description of changes -->", f"Auto-generated implementation for: {state['task']}")
    
    # Add Test Suggestions
    if state.get("test_suggestions"):
        body += f"\n\n## 🧪 Suggested Test Cases\n{state['test_suggestions']}"

    # 4. Push & PR
    try:
        print(f"⬆️ Pushing {branch_name}...")
        subprocess.run(["git", "push", "origin", branch_name], cwd=TARGET_DIR, check=True)
        
        existing = get_open_pr(state['repo'], branch_name)
        if existing:
            print(f"🔄 Updating existing PR #{existing['number']}...")
            url = update_pull_request(state['repo'], existing['number'], title=commit_msg, body=body)
        else:
            print("🆕 Creating new PR...")
            url = create_pull_request(state['repo'], commit_msg, body, branch_name, "main")
            
        print(f"🎉 PR Ready: {url}")
        
        if state.get('issue_data'):
            update_issue_status(state['issue_data'], "In Review")
            
    except Exception as e:
        print(f"❌ Publisher Failed: {e}")

    return {}
