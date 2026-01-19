import os
import json
import subprocess
from langchain_core.messages import HumanMessage
from ..state import AgentState
from ..llm import get_llm
from ..config import TARGET_DIR

# GitHub Integration
from ..github_client import get_open_pr, create_pull_request, update_pull_request, update_issue_status

def publisher_agent(state: AgentState):
    """Publisher: Pushes Code, Creates PRs"""
    print("🚀 Auto-Deploy / Publisher Agent...")

    target_dir = state.get('target_dir', TARGET_DIR)
    print(f"📂 Working Directory: {target_dir}")
    
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
        res = subprocess.run(["git", "branch", "--show-current"], cwd=target_dir, capture_output=True, text=True)
        current = res.stdout.strip()
        
        if current != branch_name:
             # Create/Checkout
             print(f"   Switching to {branch_name}...")
             subprocess.run(["git", "checkout", "-b", branch_name], cwd=target_dir, capture_output=True) # Try create
             subprocess.run(["git", "checkout", branch_name], cwd=target_dir, capture_output=True) # Try switch
            
        subprocess.run(["git", "add", "."], cwd=target_dir, check=True)
        commit_msg = f"feat: {state['task'][:50]}..."
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=target_dir)
        
    except Exception as e:
        print(f"⚠️ Git Local Ops failed: {e}")
        return {}

    # 3. Generate PR Body with AI
    llm = get_llm(temperature=0.7)
    
    # A. Capture Git Context
    try:
        # Get list of commits on this branch relative to main
        # We assume 'main' is the base branch as per config
        try:
            commits = subprocess.check_output(
                ["git", "log", "--oneline", "main..HEAD"],
                cwd=target_dir, text=True
            ).strip()
        except subprocess.CalledProcessError:
            # Fallback if main not found, try master
            commits = subprocess.check_output(
                ["git", "log", "--oneline", "master..HEAD"],
                cwd=target_dir, text=True
            ).strip()

        # Get cumulative stats
        diff_stats = subprocess.check_output(
            ["git", "diff", "--stat", "HEAD", "--not", "main", "master"], # diff against whatever base is excluded
            cwd=target_dir, text=True
        ).strip()
        
        git_stats = f"COMMITS:\n{commits}\n\nSTATS:\n{diff_stats}"
    except Exception as e:
        print(f"⚠️ Failed to get git stats: {e}")
        git_stats = "No git context available (or failed to diff against main/master)."

    # B. Load Template
    template_content = ""
    template_path = os.path.join(target_dir, ".github", "pull_request_template.md")
    if os.path.exists(template_path):
        with open(template_path, "r") as f:
            template_content = f.read()

    # C. Construct Prompt
    prompt = f"""You are an AI assistant helping to create a Pull Request description.
    
TASK: {state['task']}
ISSUE: {json.dumps(state.get('issue_data', {}), indent=2)}

GIT CONTEXT:
{git_stats}

PR TEMPLATE:
{template_content}

INSTRUCTIONS:
1. Generate a comprehensive PR description in Markdown format.
2. If a template is provided, fill it out intelligently.
3. If no template, use a standard structure: Summary, Changes, Impact.
4. Focus on 'Why' and 'What'.
5. Do not include 'Here is the PR description' preamble. Just the body.
"""

    # D. Save Draft & Wait for Approval
    draft_path = os.path.join(target_dir, "draft_pr_prompt.txt")
    with open(draft_path, "w") as f:
        f.write(prompt)
        
    print(f"\n📝 Draft Prompt saved to: {draft_path}")
    print("✋ Waiting for approval... Please review the prompt file.")
    input("⌨️  Press Enter to approve and generate PR body (or Ctrl+C to cancel)...")

    # E. Generate
    print("🤖 Generating PR Body with AI...")
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        body = response.content
        print("✅ AI Generation Complete.")
    except Exception as e:
        print(f"❌ AI Generation Failed: {e}")
        print("Using basic fallback.")
        body = f"implementation for: {state['task']}\n\n(AI Generation failed)"

    # Add Test Suggestions appended
    if state.get("test_suggestions"):
        body += f"\n\n## 🧪 Suggested Test Cases\n{state['test_suggestions']}"

    # 4. Push & PR
    try:
        print(f"⬆️ Pushing {branch_name}...")
        subprocess.run(["git", "push", "origin", branch_name], cwd=target_dir, check=True)
        
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

    return {"pr_url": url} if 'url' in locals() else {}
