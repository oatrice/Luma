import os
import sys
import json
import argparse
import subprocess
from langchain_core.messages import HumanMessage
from luma_core.workflow import build_graph
from luma_core.config import TARGET_DIR as DEFAULT_TARGET_DIR
from luma_core.llm import get_llm
from luma_core.tools import (
    update_android_version_logic,
    generate_branch_suggestions,
    get_user_branch_choice,
    load_or_generate_pr_content,
    generate_test_suggestions,
    get_git_changed_files,
    suggest_version_from_git,
    check_branch_sync,
    create_multi_repo_prs,
    create_branch_in_repos,
    update_multi_repo_docs
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

# --- Multi-Project Configuration ---
# Assuming Luma is in /Users/oatrice/Software-projects/Luma
# and others are siblings in /Users/oatrice/Software-projects/
BASE_PROJECTS_DIR = os.path.abspath(os.path.join(os.getcwd(), ".."))

PROJECTS = {
    "1": {
        "name": "Tetris-Battle (Client)", 
        "path": os.path.join(BASE_PROJECTS_DIR, "Tetris-Battle/client-nuxt"), 
        "repo": "oatrice/Tetris-Battle"
    },
    "2": {
        "name": "JarWise - Root", 
        "path": os.path.join(BASE_PROJECTS_DIR, "JarWise"), 
        "repo": "oatrice/JarWise-Root",
        "version_file": "VERSION"  # Simple VERSION file
    },
    "3": {
        "name": "JarWise - Android", 
        "path": os.path.join(BASE_PROJECTS_DIR, "JarWise/Android"), 
        "repo": "oatrice/JarWise-Android",
        "version_file": "app/build.gradle.kts"  # Android gradle
    },
    "4": {
        "name": "JarWise - Web", 
        "path": os.path.join(BASE_PROJECTS_DIR, "JarWise/Web"), 
        "repo": "oatrice/JarWise-Web",
        "version_file": "package.json"  # Node/Web
    }
}

# JarWise Multi-Repo Config
JARWISE_REPOS = ["2", "3", "4"]  # Root, Android, Web

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

    # Initial Context Setup
    current_project_key = "1" # Default to Tetris for backward compatibility or first item
    
    # Check if default path exists, if not maybe default to JarWise Root
    if not os.path.exists(PROJECTS["1"]["path"]):
         current_project_key = "2" # Fallback

    active_config = PROJECTS[current_project_key]
    current_target_dir = active_config["path"]
    current_repo_slug = active_config["repo"]

    # Default initial state
    initial_state = {
        "task": "",
        "iterations": 0,
        "changes": {},
        "test_errors": "",
        "source_files": ["package.json", "vite.config.ts"],  # Restored
        "repo": current_repo_slug,
        "issue_data": {}
    }

    while True:
        # Check draft existence for UI hint
        draft_path = os.path.join(current_target_dir, ".pr_draft.json")
        draft_hint = " 📄" if os.path.exists(draft_path) else ""
        
        print(f"\n📂 Active Project: {active_config['name']}")
        print(f"📍 Path: {current_target_dir}")
        print(f"🔗 Repo: {current_repo_slug}")
        print("-" * 30)
        
        print(f"1. 📥 Select Next Issue (Start Coding)")
        print(f"2. 🚀 Create Pull Request (Deploy){draft_hint}")
        print("2a. 🚀 Create Multi-Repo PR (JarWise)")
        print("3. 🧐 Code Review (Local)")
        print("4. 📝 Update Docs (Standalone)")
        print("4a. 📝 Update Multi-Repo Docs (JarWise)")
        if current_project_key == "1":
            print("5. 🤖 Update Android Server Version")
        print("9. 🔄 Switch Project / Repo")
        print("0. ❌ Exit")
        
        choice = input("\nSelect Option: ").strip()
        
        if choice == "0":
            print("👋 Bye!")
            break

        elif choice == "9":
            print("\n🔄 Switch Project:")
            for key, proj in PROJECTS.items():
                print(f"   [{key}] {proj['name']}")
            
            p_choice = input("Select Project: ").strip()
            if p_choice in PROJECTS:
                current_project_key = p_choice
                active_config = PROJECTS[current_project_key]
                current_target_dir = active_config["path"]
                current_repo_slug = active_config["repo"]
                # Update initial state repo
                initial_state["repo"] = current_repo_slug
                print(f"✅ Switched to {active_config['name']}")
            else:
                print("❌ Invalid selection.")
            
        elif choice == "1":
            # --- Flow 1: Issue Selection ---
            if not fetch_issues:
                print("❌ GitHub fetcher unavailable.")
                continue
                
            print(f"📡 Fetching issues from {current_repo_slug}...")
            issues = fetch_issues(current_repo_slug)
            selected_issue = select_issue(issues, ai_advisor=get_ai_advice)
            
            if selected_issue:
                print(f"🚀 Starting Task: {selected_issue['title']}")
                update_issue_status(selected_issue, "In Progress")
                
                initial_state["task"] = convert_to_task(selected_issue)
                initial_state["repo"] = current_repo_slug
                initial_state["issue_data"] = selected_issue
                
                app.invoke(initial_state)
                print("✅ Workflow Complete.")
            else:
                print("❌ No issue selected.")

        elif choice == "2":
            # --- Flow 2: Create PR (Full Feature) ---
            print(f"\n🚀 Preparing to Create PR for {current_target_dir}...")
            
            try:
                # 1. Get Current Branch
                res = subprocess.run(["git", "branch", "--show-current"], cwd=current_target_dir, capture_output=True, text=True)
                current_branch = res.stdout.strip()
                if not current_branch:
                    print("❌ Error: Not in a git repository or detached head.")
                    continue

                # If on main, offer to create feature branch
                if current_branch in ['main', 'master']:
                    print(f"⚠️ You are currently on '{current_branch}'.")
                    create_new = input("🌿 Do you want to create a new branch? (y/N): ").lower()
                    if create_new == 'y':
                        new_branch = get_user_branch_choice(target_dir=current_target_dir)
                        if new_branch:
                            try:
                                subprocess.run(["git", "checkout", "-b", new_branch], cwd=current_target_dir, check=True)
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
                        new_name = get_user_branch_choice(target_dir=current_target_dir)
                        if new_name:
                            try:
                                subprocess.run(["git", "branch", "-m", new_name], cwd=current_target_dir, check=True)
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
                                    full_path = os.path.join(current_target_dir, filename)
                                    with open(full_path, "w", encoding="utf-8") as f:
                                        f.write(content)
                                
                                subprocess.run(["git", "add", "."], cwd=current_target_dir, check=True)
                                subprocess.run(["git", "commit", "-m", "docs: update CHANGELOG and version from Luma"], cwd=current_target_dir, check=True)
                                print("   ✅ Docs committed.")
                            else:
                                print("   ⏩ Skipping docs commit.")
                    except Exception as e:
                        print(f"   ⚠️ Docs Agent failed in PR flow: {e}")
                else:
                    print("   ⏩ Skipping Docs Agent.")

                # 2. Load or Generate PR Content
                title, body, draft_file = load_or_generate_pr_content(current_branch, current_repo_slug, target_dir=current_target_dir)
                
                print(f"\n📝 Proposed PR:\nTitle: {title}\nBody:\n{body[:200]}...\n")

                # --- Test Suggestions ---
                generate_test_suggestions(target_dir=current_target_dir)

                # 3. Create PR
                if input("Proceed to Open PR? (y/N): ").lower() == 'y':
                    try:
                        print(f"⬆️ Pushing branch '{current_branch}' to origin...")
                        subprocess.run(["git", "push", "origin", current_branch], cwd=current_target_dir, check=True)
                    except subprocess.CalledProcessError as e:
                        print(f"❌ Failed to push branch: {e}")
                        continue

                    # Check for existing PR
                    existing_pr = get_open_pr(current_repo_slug, current_branch)
                    url = None
                    
                    if existing_pr:
                        print(f"⚠️ Found existing PR #{existing_pr['number']}: {existing_pr['html_url']}")
                        if input("🔄 Update existing PR description? (y/N): ").lower() == 'y':
                            url = update_pull_request(current_repo_slug, existing_pr['number'], title, body)
                        else:
                            print("⏩ Skipping PR update.")
                            continue
                    else:
                        url = create_pull_request(current_repo_slug, title, body, current_branch, "main")
                        
                    if url: 
                        print(f"✅ PR Created: {url}")
                        # CLEANUP
                        if os.path.exists(draft_file):
                            os.remove(draft_file)
                    else:
                        print(f"⚠️ PR Creation failed. Draft preserved at {draft_file}")
                    
            except Exception as e:
                print(f"❌ Error in PR Flow: {e}")

        elif choice == "2a":
            # --- Flow 2a: Multi-Repo PR (JarWise) ---
            print("\n🚀 Multi-Repo PR for JarWise (Root, Android, Web)")
            
            # Get repo configs
            selected_repos = [PROJECTS[k] for k in JARWISE_REPOS if k in PROJECTS]
            
            print("\n📦 Target Repos:")
            for r in selected_repos:
                print(f"   - {r['name']}: {r['repo']}")
            
            # Check branch sync
            print("\n🔍 Checking branch synchronization...")
            is_synced, branches = check_branch_sync(selected_repos)
            
            print("\n🌿 Current Branches:")
            for name, branch in branches.items():
                print(f"   - {name}: {branch}")
            
            if not is_synced:
                print("\n❌ Branch mismatch detected! All repos must be on the same branch.")
                print("\nตัวเลือก:")
                print("   [1] 🌿 Create new branch in all repos")
                print("   [2] ⚠️  Continue anyway (NOT RECOMMENDED)")
                print("   [0] ❌  Cancel")
                
                mismatch_choice = input("\n👉 Select: ").strip()
                
                if mismatch_choice == "1":
                    # Create new branch
                    print("\n🌿 Create new branch in all repos")
                    new_branch = get_user_branch_choice(target_dir=selected_repos[0]['path'])
                    
                    if new_branch:
                        print(f"\n🚀 Creating '{new_branch}' in all repos...")
                        all_success, branch_results = create_branch_in_repos(selected_repos, new_branch)
                        
                        print("\n📊 Branch Creation Results:")
                        for name, result in branch_results.items():
                            print(f"   {name}: {result}")
                        
                        if all_success:
                            print(f"\n✅ All repos now on '{new_branch}'")
                            # Re-check sync
                            is_synced, branches = check_branch_sync(selected_repos)
                        else:
                            print("\n❌ Some repos failed. Please fix manually.")
                            continue
                    else:
                        continue
                        
                elif mismatch_choice == "2":
                    print("⚠️ Continuing with mismatched branches...")
                else:
                    continue
            
            # Check for main/master branch
            branch_values = list(branches.values())
            if any(b in ['main', 'master'] for b in branch_values):
                print("\n⚠️ One or more repos are on 'main' or 'master' branch.")
                print("   Please switch to a feature branch before creating PRs.")
                continue
            
            # Confirm
            confirm = input(f"\n🚀 Create PRs for all {len(selected_repos)} repos? (y/N): ").lower()
            if confirm != 'y':
                continue
            
            # Create PRs
            results = create_multi_repo_prs(selected_repos)
            
            # Summary
            print("\n" + "=" * 40)
            print("📊 Multi-Repo PR Summary:")
            print("=" * 40)
            
            success_count = 0
            for r in results:
                if r["success"]:
                    print(f"   ✅ {r['name']}: {r['url']}")
                    success_count += 1
                else:
                    print(f"   ❌ {r['name']}: {r['error']}")
            
            print(f"\n   Total: {success_count}/{len(results)} successful")

        elif choice == "3":
            # --- Flow 3: Local Code Review (Full Feature) ---
            print(f"\n🧐 Local Code Reviewer ({active_config['name']})")
            
            changes = {}
            
            print("1. Review Changes (origin/main -> HEAD + Dirty)")
            print("2. Review Specific File")
            review_mode = input("Select Mode [1]: ").strip() or "1"
            
            if review_mode == "1":
                try:
                    file_list = get_git_changed_files("all", target_dir=current_target_dir)
                    
                    if not file_list:
                        print("✅ No changes found (Clean vs origin/main).")
                        continue
                        
                    print(f"   🔎 Found {len(file_list)} changed files.")
                    
                    # Limit files
                    if len(file_list) > 30:
                        print(f"⚠️ Too many files ({len(file_list)}). Reviewing top 10.")
                        file_list = file_list[:10]
                        
                    for rel_path in file_list:
                        full_path = os.path.join(current_target_dir, rel_path)
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
                full_path = os.path.join(current_target_dir, target_file)
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

        elif choice == "4a":
            # --- Flow 4a: Update Multi-Repo Docs ---
            print("\n📝 Multi-Repo Documentation Update (JarWise)")
            print("   This will update CHANGELOG.md and README.md in Root, Android, and Web repos")
            
            # Get JarWise repos
            selected_repos = [PROJECTS[key] for key in JARWISE_REPOS if key in PROJECTS]
            
            print("\n📦 Target Repos:")
            for r in selected_repos:
                print(f"   - {r['name']}: {r['path']}")
            
            confirm = input("\n📝 Start docs update for all repos? (y/N): ").lower()
            if confirm != 'y':
                continue
            
            # Run docs update (manual mode - no AI agent passed)
            results = update_multi_repo_docs(selected_repos, docs_agent_func=None)
            
            # Summary
            print("\n" + "=" * 40)
            print("📊 Multi-Repo Docs Summary:")
            print("=" * 40)
            
            success_count = 0
            for r in results:
                if r.get("success"):
                    files = ', '.join(r.get('files_updated', []))
                    print(f"   ✅ {r['name']}: {files}")
                    success_count += 1
                else:
                    print(f"   ⏩ {r['name']}: {r.get('error', 'Unknown error')}")
            
            print(f"\n   Total: {success_count}/{len(results)} updated")

        elif choice == "5" and current_project_key == "1":
            # --- Flow 5: Update Android Version ---
            print("🤖 Update Android Server Version")
            
            # AI-powered version suggestion
            suggested = suggest_version_from_git(target_dir=current_target_dir)
            if suggested:
                version_input = input(f"Target Version [{suggested}]: ").strip()
                version = version_input if version_input else suggested
            else:
                version = input("Target Version (e.g. 1.1.7): ").strip()
            
            if version:
                update_android_version_logic(version, target_dir=current_target_dir)
                
                # Check and Review CHANGELOG

                changelog_path = os.path.join(current_target_dir, "../android-server/CHANGELOG.md")
                if os.path.exists(changelog_path):
                    try:
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
                    except Exception as e:
                        print(f"⚠️ Changelog review failed: {e}")
            else:
                print("❌ Version required.")

if __name__ == "__main__":
    main()
