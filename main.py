import os
import sys
import json
import argparse
import subprocess
from langchain_core.messages import HumanMessage
from luma_core.workflow import build_graph
from luma_core.config import TARGET_DIR
from luma_core.llm import get_llm
from luma_core.tools import (
    update_android_version_logic,
    generate_branch_suggestions,
    get_user_branch_choice,
    load_or_generate_pr_content,
    generate_test_suggestions,
    get_git_changed_files,
    suggest_version_from_git
)
from luma_core.agents.reviewer import reviewer_agent, docs_reviewer_agent
from luma_core.agents.docs import docs_agent

# Try to import GitHub Fetcher
try:
    from github_fetcher import (
        fetch_issues, select_issue, convert_to_task, 
        create_pull_request, update_issue_status, 
        get_open_pr, update_pull_request
    )
except ImportError:
    fetch_issues = None
    print("⚠️ github_fetcher.py not found. GitHub features disabled.")

def get_ai_advice(issues):
    """AI Advisor for Issue Selection"""
    if not issues:
        return
        
    summary = "\n".join([f"- Issue #{i['number']}: {i['title']}\n  Body: {(i.get('body') or '')[:200]}..." for i in issues])
    
    prompt = f"""
    You are a Technical Project Manager. 
    Analyze the following GitHub Issues (Priority Tasks) and suggest the execution order.
    
    Tasks:
    {summary}
    
    Output:
    Provide a short recommendation (2-3 sentences per task).
    Be concise. Use bullet points.
    """
    
    llm = get_llm(temperature=0.5)
    response = llm.invoke([HumanMessage(content=prompt)])
    print("\n🔎 AI Recommendation:\n" + response.content)

def main():
    parser = argparse.ArgumentParser(description="Luma AI Architect")
    parser.add_argument("--github", action="store_true", help="Fetch task from GitHub Issues")
    parser.add_argument("--repo", type=str, default="oatrice/Tetris-Battle", help="GitHub Repository (user/repo)")
    args = parser.parse_args()

    # Build the Agent Graph
    app = build_graph()

    print("\n==============================")
    print("🤖 Luma AI Architect")
    print("==============================")

    # Default initial state
    initial_state = {
        "task": "",
        "iterations": 0,
        "changes": {},
        "test_errors": "",
        "source_files": ["package.json", "vite.config.ts"],  # Restored
        "repo": args.repo,
        "issue_data": {}
    }

    while True:
        # Check draft existence for UI hint
        draft_path = os.path.join(TARGET_DIR, ".pr_draft.json")
        draft_hint = " 📄" if os.path.exists(draft_path) else ""
        
        print(f"\n1. 📥 Select Next Issue (Start Coding)")
        print(f"2. 🚀 Create Pull Request (Deploy){draft_hint}")
        print("3. 🧐 Code Review (Local)")
        print("4. 📝 Update Docs (Standalone)")
        print("5. 🤖 Update Android Server Version")
        print("0. ❌ Exit")
        
        choice = input("\nSelect Option: ").strip()
        
        if choice == "0":
            print("👋 Bye!")
            break
            
        elif choice == "1":
            # --- Flow 1: Issue Selection ---
            if not fetch_issues:
                print("❌ GitHub fetcher unavailable.")
                continue
                
            print(f"📡 Fetching issues from {args.repo}...")
            issues = fetch_issues(args.repo)
            selected_issue = select_issue(issues, ai_advisor=get_ai_advice)
            
            if selected_issue:
                print(f"🚀 Starting Task: {selected_issue['title']}")
                update_issue_status(selected_issue, "In Progress")
                
                initial_state["task"] = convert_to_task(selected_issue)
                initial_state["issue_data"] = selected_issue
                
                app.invoke(initial_state)
                print("✅ Workflow Complete.")
            else:
                print("❌ No issue selected.")

        elif choice == "2":
            # --- Flow 2: Create PR (Full Feature) ---
            print(f"\n🚀 Preparing to Create PR for {TARGET_DIR}...")
            
            try:
                # 1. Get Current Branch
                res = subprocess.run(["git", "branch", "--show-current"], cwd=TARGET_DIR, capture_output=True, text=True)
                current_branch = res.stdout.strip()
                if not current_branch:
                    print("❌ Error: Not in a git repository or detached head.")
                    continue

                # If on main, offer to create feature branch
                if current_branch in ['main', 'master']:
                    print(f"⚠️ You are currently on '{current_branch}'.")
                    create_new = input("🌿 Do you want to create a new branch? (y/N): ").lower()
                    if create_new == 'y':
                        new_branch = get_user_branch_choice()
                        if new_branch:
                            try:
                                subprocess.run(["git", "checkout", "-b", new_branch], cwd=TARGET_DIR, check=True)
                                current_branch = new_branch
                                print(f"✅ Switched to new branch: {current_branch}")
                            except subprocess.CalledProcessError as e:
                                print(f"❌ Failed to create branch: {e}")
                                continue
                    
                print(f"🌿 Current Branch: {current_branch}")

                # If NOT on main, offer to rename
                if current_branch not in ['main', 'master']:
                    rename_opt = input(f"✏️  Do you want to rename '{current_branch}'? (y/N): ").lower()
                    if rename_opt == 'y':
                        new_name = get_user_branch_choice()
                        if new_name:
                            try:
                                subprocess.run(["git", "branch", "-m", new_name], cwd=TARGET_DIR, check=True)
                                current_branch = new_name
                                print(f"✅ Renamed to: {current_branch}")
                            except subprocess.CalledProcessError as e:
                                print(f"❌ Failed to rename: {e}")
                
                # Confirm
                confirm = input(f"Create PR for '{current_branch}' -> 'main'? (y/N): ").lower()
                if confirm != 'y':
                    continue
                    
                # --- OPTIONAL: Run Docs Agent before PR ---
                run_docs = input("\n📚 Do you want to update docs & versioning before PR? (y/N): ").lower()
                if run_docs == 'y':
                    print("📚 Running Docs Agent (Pre-PR Check)...")
                    try:
                        doc_state = initial_state.copy()
                        doc_state["task"] = f"Update documentation for PR: {current_branch}"
                        doc_state["skip_coder"] = True
                        
                        doc_result = docs_agent(doc_state)
                        
                        # Debug log
                        print(f"   [DEBUG] doc_result type: {type(doc_result)}")
                        print(f"   [DEBUG] doc_result: {doc_result}")
                        print(f"   [DEBUG] doc_result.get('changes'): {doc_result.get('changes') if doc_result else 'N/A'}")
                        
                        if doc_result and doc_result.get('changes'):
                            changes = doc_result['changes']
                            
                            # Run Docs Reviewer
                            print("   🧐 Running Docs Reviewer validation...")
                            review_state = {"changes": changes}
                            review_result = docs_reviewer_agent(review_state)
                            if review_result and review_result.get('changes'):
                                changes = review_result['changes']
                                print("   ✅ Docs Reviewer applied corrections.")

                            print(f"   📝 Docs Agent proposes updates to: {list(changes.keys())}")
                            
                            if input("   💾 Commit documentation updates now? (Y/n): ").lower() not in ['n', 'no']:
                                for filename, content in changes.items():
                                    full_path = os.path.join(TARGET_DIR, filename)
                                    with open(full_path, "w", encoding="utf-8") as f:
                                        f.write(content)
                                
                                subprocess.run(["git", "add", "."], cwd=TARGET_DIR, check=True)
                                subprocess.run(["git", "commit", "-m", "docs: update CHANGELOG and version from Luma"], cwd=TARGET_DIR, check=True)
                                print("   ✅ Docs committed.")
                            else:
                                print("   ⏩ Skipping docs commit.")
                    except Exception as e:
                        print(f"   ⚠️ Docs Agent failed in PR flow: {e}")
                else:
                    print("   ⏩ Skipping Docs Agent.")

                # 2. Load or Generate PR Content
                title, body, draft_file = load_or_generate_pr_content(current_branch, args.repo)
                
                print(f"\n📝 Proposed PR:\nTitle: {title}\nBody:\n{body[:200]}...\n")

                # --- Test Suggestions ---
                generate_test_suggestions()

                # 3. Create PR
                if input("Proceed to Open PR? (y/N): ").lower() == 'y':
                    try:
                        print(f"⬆️ Pushing branch '{current_branch}' to origin...")
                        subprocess.run(["git", "push", "origin", current_branch], cwd=TARGET_DIR, check=True)
                    except subprocess.CalledProcessError as e:
                        print(f"❌ Failed to push branch: {e}")
                        continue

                    # Check for existing PR
                    existing_pr = get_open_pr(args.repo, current_branch)
                    url = None
                    
                    if existing_pr:
                        print(f"⚠️ Found existing PR #{existing_pr['number']}: {existing_pr['html_url']}")
                        if input("🔄 Update existing PR description? (y/N): ").lower() == 'y':
                            url = update_pull_request(args.repo, existing_pr['number'], title, body)
                        else:
                            print("⏩ Skipping PR update.")
                            continue
                    else:
                        url = create_pull_request(args.repo, title, body, current_branch, "main")
                        
                    if url: 
                        print(f"✅ PR Created: {url}")
                        # CLEANUP
                        if os.path.exists(draft_file):
                            os.remove(draft_file)
                    else:
                        print(f"⚠️ PR Creation failed. Draft preserved at {draft_file}")
                    
            except Exception as e:
                print(f"❌ Error in PR Flow: {e}")

        elif choice == "3":
            # --- Flow 3: Local Code Review (Full Feature) ---
            print("\n🧐 Local Code Reviewer")
            
            changes = {}
            
            print("1. Review Changes (origin/main -> HEAD + Dirty)")
            print("2. Review Specific File")
            review_mode = input("Select Mode [1]: ").strip() or "1"
            
            if review_mode == "1":
                try:
                    file_list = get_git_changed_files("all")
                    
                    if not file_list:
                        print("✅ No changes found (Clean vs origin/main).")
                        continue
                        
                    print(f"   🔎 Found {len(file_list)} changed files.")
                    
                    # Limit files
                    if len(file_list) > 30:
                        print(f"⚠️ Too many files ({len(file_list)}). Reviewing top 10.")
                        file_list = file_list[:10]
                        
                    for rel_path in file_list:
                        full_path = os.path.join(TARGET_DIR, rel_path)
                        if os.path.exists(full_path) and os.path.isfile(full_path):
                            if rel_path.endswith(('.png', '.jpg', '.ico', '.pdf')):
                                continue
                            try:
                                with open(full_path, 'r', encoding='utf-8') as f:
                                    changes[rel_path] = f.read()
                            except:
                                pass
                                
                except Exception as e:
                    print(f"❌ Error reading git status: {e}")
                    continue
                    
            elif review_mode == "2":
                target_file = input("Enter relative file path: ").strip()
                full_path = os.path.join(TARGET_DIR, target_file)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        changes[target_file] = f.read()
                else:
                    print(f"❌ File not found: {target_file}")
                    continue
            
            if not changes:
                print("❌ No content to review.")
                continue
                
            # Run Reviewer Agent
            print(f"🚀 Running Reviewer on {list(changes.keys())}...")
            
            review_state = {
                "task": "Review local code changes for bugs, security issues, and best practices.",
                "changes": changes,
                "iterations": 0,
                "test_errors": ""
            }
            
            result = reviewer_agent(review_state)
            
            if result.get("code_content"):
                print("\n📝 Reviewer Feedback:")
                print("--------------------------------------------------")
                print(result["code_content"])
                print("--------------------------------------------------")
            
            print("\n✅ Review Complete.")

        elif choice == "4":
            # --- Flow 4: Update Docs Only ---
            print("📝 Starting Documentation Update...")
            print("   This will check for local Git changes and update CHANGELOG.md + package.json")
            
            confirm = input("   Continue? (Y/n): ").strip().lower()
            if confirm not in ['n', 'no']:
                doc_state = initial_state.copy()
                doc_state["task"] = "Update all documentation based on local file changes."
                doc_state["skip_coder"] = True
                
                app.invoke(doc_state)
                print("✅ Documentation Update Complete.")

        elif choice == "5":
            # --- Flow 5: Update Android Version ---
            print("🤖 Update Android Server Version")
            
            # AI-powered version suggestion
            suggested = suggest_version_from_git()
            if suggested:
                version_input = input(f"Target Version [{suggested}]: ").strip()
                version = version_input if version_input else suggested
            else:
                version = input("Target Version (e.g. 1.1.7): ").strip()
            
            if version:
                update_android_version_logic(version)
                
                # Check and Review CHANGELOG

                changelog_path = os.path.join(TARGET_DIR, "../android-server/CHANGELOG.md")
                if os.path.exists(changelog_path):
                    with open(changelog_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    review_state = {"changes": {"android-server/CHANGELOG.md": content}}
                    print("   🧐 Running Docs Reviewer validation...")
                    review_result = docs_reviewer_agent(review_state)
                    
                    if review_result and review_result.get('changes'):
                        new_content = review_result['changes']["android-server/CHANGELOG.md"]
                        if new_content != content:
                            with open(changelog_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            print("   ✅ Docs Reviewer corrected CHANGELOG.md")
                            
                            # Amend commit if previous logic committed it (heuristic)
                            subprocess.run(["git", "add", changelog_path], cwd=os.path.dirname(changelog_path), check=False)
                            subprocess.run(["git", "commit", "--amend", "--no-edit"], cwd=os.path.dirname(changelog_path), check=False)
                            print("   ✅ Amended previous commit with corrected docs.")
            else:
                print("❌ Version required.")

if __name__ == "__main__":
    main()
