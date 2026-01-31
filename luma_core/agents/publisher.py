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
    
    # 2. Get current branch first
    try:
        res = subprocess.run(["git", "branch", "--show-current"], cwd=target_dir, capture_output=True, text=True)
        current_branch = res.stdout.strip()
    except:
        current_branch = ""
    
    # Determine which branch to use
    if current_branch and current_branch not in ['main', 'master']:
        # Already on a feature branch - use it
        branch_name = current_branch
        print(f"🌲 Using Current Branch: {branch_name}")
    elif state.get('issue_data'):
        # On main/master, derive new branch from issue
        issue = state['issue_data']
        safe_title = issue['title'].lower().replace(" ", "-")
        # Remove special characters that are invalid in git branch names
        safe_title = "".join(c for c in safe_title if c.isalnum() or c in '-_')
        branch_name = f"feat/issue-{issue['number']}-{safe_title}"[:50]
        print(f"🌲 Creating New Branch: {branch_name}")
        # Create and checkout new branch
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=target_dir, capture_output=True)
    else:
        branch_name = "feat/luma-auto"
        print(f"🌲 Using Default Branch: {branch_name}")
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=target_dir, capture_output=True)
    
    # 3. Add & Commit
    try:
        subprocess.run(["git", "add", "."], cwd=target_dir, check=True)
        commit_msg = f"feat: {state['task'][:50]}..."
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=target_dir)
        
    except Exception as e:
        print(f"⚠️ Git Local Ops failed: {e}")
        return {}

    # 3. Generate PR Body with AI
    llm = get_llm(temperature=0.7)
    
    # A. Check for draft_code_review.md first (richer context)
    draft_review_path = os.path.join(target_dir, "draft_code_review.md")
    git_stats = ""
    
    if os.path.exists(draft_review_path):
        print(f"📋 Found draft_code_review.md - using for PR context...")
        try:
            with open(draft_review_path, 'r', encoding='utf-8') as f:
                git_stats = f.read()
            print("✅ Loaded draft with full diff context")
        except Exception as e:
            print(f"⚠️ Failed to read draft: {e}")
            git_stats = ""
    
    # B. Fallback: Generate context on the fly
    if not git_stats:
        print("📊 Generating git context...")
        try:
            # Get list of commits on this branch relative to defaults
            base_branches = ["origin/main", "origin/master", "main", "master"]
            commits = ""
            base_ref = "main" # fallback
            
            for ref in base_branches:
                try:
                    commits = subprocess.check_output(
                        ["git", "log", "--oneline", f"{ref}..HEAD"],
                        cwd=target_dir, text=True, stderr=subprocess.DEVNULL
                    ).strip()
                    if commits:
                        base_ref = ref
                        break
                except subprocess.CalledProcessError:
                    continue

            # Get cumulative stats
            try:
                diff_stats = subprocess.check_output(
                    ["git", "diff", "--stat", f"{base_ref}..HEAD"],
                    cwd=target_dir, text=True
                ).strip()
            except subprocess.CalledProcessError:
                diff_stats = "(diff stats unavailable)"
            
            # Get Smart Diff (Prioritize source code)
            try:
                # 1. Get list of changed files
                changed_files_raw = subprocess.check_output(
                    ["git", "diff", "--name-only", f"{base_ref}..HEAD"],
                    cwd=target_dir, text=True
                ).strip()
                changed_files = changed_files_raw.splitlines()

                # 2. Filter for interesting source files
                INTERESTING_EXTENSIONS = ['.kt', '.xml', '.java', '.py', '.ts', '.tsx', '.js', '.jsx', '.go', '.rs', '.swift', '.gradle.kts', '.toml']
                source_files = [f for f in changed_files if any(f.endswith(ext) for ext in INTERESTING_EXTENSIONS)]
                
                # 3. Get diff for source files first (or all if few)
                files_to_diff = source_files if source_files else changed_files
                
                # 4. Run diff command
                if files_to_diff:
                    # git diff base..HEAD -- file1 file2 ...
                    cmd = ["git", "diff", f"{base_ref}..HEAD", "--"] + files_to_diff
                    full_diff = subprocess.check_output(
                        cmd,
                        cwd=target_dir, text=True
                    ).strip()
                else:
                    full_diff = ""
                
                # 5. Cap size but be generous (20k chars)
                if len(full_diff) > 20000:
                    full_diff = full_diff[:20000] + "\n... (Diff truncated for size) ..."

            except Exception as e:
                print(f"⚠️ Smart diff failed: {e}")
                full_diff = "(diff unavailable)"
            
            git_stats = f"COMMITS:\n{commits}\n\nSTATS:\n{diff_stats}\n\nKEY FILE DIFFS:\n{full_diff}"
        except Exception as e:
            print(f"⚠️ Failed to get git stats: {e}")
            git_stats = "No git context available."

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
6. IMPORTANT: Always use FULL URLs for links to issues and other PRs (e.g., https://github.com/owner/repo/issues/123), do NOT use short syntax (e.g., #123) to ensuring proper linking across platforms.
"""

    # D. Save Draft & Wait for Approval
    draft_path = os.path.join(target_dir, "draft_pr_prompt.md")
    with open(draft_path, "w") as f:
        f.write(f"# PR Draft Prompt\n\n")
        f.write(prompt)
        
    print(f"\n📝 Draft Prompt saved to: {draft_path}")
    print("✋ Waiting for approval... Please review the prompt file.")
    print("👉 Options: [y] Auto-Generate, [m] Use Manual Body, [n] Cancel")
    
    manual_body_path = os.path.join(target_dir, "draft_pr_body.md")
    
    while True:
        choice = input("👉 Select Check: ").strip().lower()
        if choice == 'y':
            # E. Generate Auto
            print("🤖 Generating PR Body with AI...")
            try:
                response = llm.invoke([HumanMessage(content=prompt)])
                body = response.content
                print("✅ AI Generation Complete.")
            except Exception as e:
                print(f"❌ AI Generation Failed: {e}")
                print("Using basic fallback.")
                body = f"implementation for: {state['task']}\n\n(AI Generation failed)"
            break
            
        elif choice == 'm':
            # E. Manual Body
            print(f"📂 Looking for manual body at: {manual_body_path}")
            if os.path.exists(manual_body_path):
                try:
                    with open(manual_body_path, "r") as f:
                        body = f.read()
                    print("✅ Loaded manual PR body.")
                    break
                except Exception as e:
                    print(f"❌ Failed to read manual body: {e}")
                    print("Falling back to Auto-Generate? (y/n)")
                    continue
            else:
                # Create empty template if not exists
                with open(manual_body_path, "w") as f:
                    f.write(f"# {state['task']}\n\n<!-- Paste your generated PR description here -->\n")
                print(f"⚠️ File not found. Created template at: {manual_body_path}")
                print(f"👉 Please edit the file and select 'm' again.")
                continue
                
        elif choice == 'n' or choice == '':
            print("❌ Operation cancelled by user.")
            return {}
        else:
            print("Invalid input. Please enter 'y', 'm', or 'n'.")

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
