import os
import sys
import datetime
from luma_core.state_manager import (
    LumaState, IssueData, WorkflowPhase,
    transition_to, get_next_step_recommendation
)
from luma_core.context_summarizer import ContextSummarizer
from luma_core.github_project import (
    fetch_kanban_cards, sync_kanban_on_action, KanbanCard
)
from luma_core.tools import (
    get_git_changed_files,
    update_multi_repo_docs,
    generate_draft_code_review
)
from luma_core.config import PROJECTS
from luma_core.preflight_checker import PreflightChecker

# =============================================================================
# Menu Actions
# =============================================================================

def action_select_issue(state: LumaState, project: dict) -> bool:
    """Select an issue from Kanban (Ready or In Progress)"""
    print("\n🔍 Fetching issues from Kanban...")
    
    # Handle Self-Test / Dummy Mode
    if project.get("kanban_id") == "dummy":
        print("🛠️  Self-Test Mode: Entering dummy issue data.")
        dummy_card = KanbanCard(
            issue_number=999,
            title="Self-Test Feature",
            url="http://github.com/oatrice/Luma/issues/999",
            body="Testing Pre-flight checker in dev mode",
            status="In Progress",
            item_id="dummy_item_id",
            repository="oatrice/Luma"
        )
        return _start_issue(state, dummy_card, project)
    
    # Fetch all cards
    all_cards = fetch_kanban_cards(project["kanban_number"])
    
    # Filter for Ready or In Progress
    valid_statuses = ["Ready", "In Progress"]
    selectable_issues = []
    
    for card in all_cards:
        # Case-insensitive check
        if any(s.lower() == card.status.lower() for s in valid_statuses):
            selectable_issues.append(card)
            
    if not selectable_issues:
        print("📭 No 'Ready' or 'In Progress' issues found on Kanban.")
        return False
    
    # Sort: In Progress first, then Ready
    def sort_key(c):
        # 0 = In Progress, 1 = Ready
        prio = 0 if c.status.lower() == "in progress" else 1
        return (prio, c.issue_number)
        
    selectable_issues.sort(key=sort_key)
    
    print("\n--- 📋 Select Issue to Work On ---")
    for i, card in enumerate(selectable_issues, 1):
        status_icon = "🔥" if card.status.lower() == "in progress" else "✅"
        print(f"  [{i}] {status_icon} #{card.issue_number}: {card.title[:50]} ({card.status})")
    print("  [0] Cancel")
    
    choice = input("\nSelect issue: ").strip()
    
    if choice == "0":
        return False
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(selectable_issues):
            return _start_issue(state, selectable_issues[idx], project)
    except ValueError:
        pass
    
    print("❌ Invalid selection")
    return False


def _start_issue(state: LumaState, card: KanbanCard, project: dict) -> bool:
    """Start working on an issue"""
    
    # Check if this issue is already active (re-selecting same issue)
    if state.active_issue and state.active_issue.number == card.issue_number:
        print(f"\n✅ Already working on #{card.issue_number} - continuing...")
        print(f"🌿 Branch: {state.active_branch}")
        
        # Ensure git is on the correct branch
        import subprocess
        try:
            result = subprocess.run(
                ["git", "checkout", state.active_branch],
                cwd=project["path"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"✅ Switched to branch '{state.active_branch}'.")
            else:
                # Branch doesn't exist, create it
                create_result = subprocess.run(
                    ["git", "checkout", "-b", state.active_branch],
                    cwd=project["path"],
                    capture_output=True,
                    text=True
                )
                if create_result.returncode == 0:
                    print(f"✅ Created and switched to branch '{state.active_branch}'.")
                else:
                    print(f"⚠️ Git: {create_result.stderr.strip()}")
            
            # Also ensure sibling repos are on the correct branch
            if project.get("type") == "monorepo_root" and project.get("sibling_repos"):
                from luma_core.config import PROJECTS
                print(f"🔄 Syncing sibling repos...")
                for sibling_key in project.get("sibling_repos", []):
                    sibling = PROJECTS.get(sibling_key)
                    if sibling and os.path.exists(sibling["path"]):
                        sib_result = subprocess.run(
                            ["git", "checkout", state.active_branch],
                            cwd=sibling["path"],
                            capture_output=True,
                            text=True
                        )
                        if sib_result.returncode == 0:
                            print(f"   ✅ {sibling['name']}: Switched to branch")
                        else:
                            # Try to create the branch
                            create_sib = subprocess.run(
                                ["git", "checkout", "-b", state.active_branch],
                                cwd=sibling["path"],
                                capture_output=True,
                                text=True
                            )
                            if create_sib.returncode == 0:
                                print(f"   ✅ {sibling['name']}: Branch created")
                            else:
                                print(f"   ⚠️ {sibling['name']}: {sib_result.stderr.strip()}")
                                
        except Exception as e:
            print(f"⚠️ Git error: {e}")
        
        return True
    
    # Transition to selecting first (only if coming from IDLE)
    if state.phase == WorkflowPhase.IDLE:
        transition_to(state, WorkflowPhase.SELECTING)
    # If already CODING, we're switching issues - no need to go through SELECTING
    
    # Create IssueData
    issue = IssueData(
        number=card.issue_number,
        title=card.title,
        html_url=card.url,
        body=card.body,
        project_item_id=card.item_id,
        project_id=project["kanban_id"],
        repository=card.repository
    )
    
    # Show Context
    print("\n🧠 Loading Project Context...")
    try:
        summarizer = ContextSummarizer(project["path"])
        reminders = summarizer.summarize_rules()
        if reminders:
            print("\n📝 Project Reminders & Rules:")
            for r in reminders:
                print(f"  {r}")
        else:
            print("  No specific rules found.")
    except Exception as e:
        print(f"⚠️ Failed to load context: {e}")
    
    # Suggest branch name
    try:
        from luma_core.agents.analyst import generate_branch_names
        suggestions = generate_branch_names(card.title, card.body or "", card.issue_number)
    except Exception as e:
        print(f"⚠️ AI Agent unavailable: {e}")
        slug = card.title.lower().replace(" ", "-").replace("[", "").replace("]", "")[:30]
        suggestions = [f"feat/{card.issue_number}-{slug}"]

    print("\n🌿 Suggested branches:")
    for i, name in enumerate(suggestions, 1):
        print(f"  [{i}] {name}")
    
    choice = input("Select [1-3] or type custom name: ").strip()
    
    branch_name = suggestions[0] # Default
    
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(suggestions):
            branch_name = suggestions[idx]
    elif choice:
        branch_name = choice
    
    # Transition to coding
    ok, msg = transition_to(
        state, 
        WorkflowPhase.CODING,
        active_issue=issue,
        active_branch=branch_name
    )
    
    if ok:
        print(f"\n✅ Started: #{card.issue_number} {card.title}")
        print(f"🌿 Branch: {branch_name}")
        
        # Actually create the branch in Git
        import subprocess
        try:
            print(f"🔄 Creating git branch...")
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=project["path"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"✅ Branch '{branch_name}' created and checked out.")
            else:
                # Branch might already exist, try switching to it
                switch_result = subprocess.run(
                    ["git", "checkout", branch_name],
                    cwd=project["path"],
                    capture_output=True,
                    text=True
                )
                if switch_result.returncode == 0:
                    print(f"✅ Switched to existing branch '{branch_name}'.")
                else:
                    print(f"⚠️ Git error: {result.stderr.strip()}")
            
            # Create branches in sibling repos (Web, Backend, Android)
            if project.get("type") == "monorepo_root" and project.get("sibling_repos"):
                from luma_core.config import PROJECTS
                print(f"\n🔄 Creating branches in sibling repos...")
                for sibling_key in project.get("sibling_repos", []):
                    sibling = PROJECTS.get(sibling_key)
                    if sibling and os.path.exists(sibling["path"]):
                        sib_result = subprocess.run(
                            ["git", "checkout", "-b", branch_name],
                            cwd=sibling["path"],
                            capture_output=True,
                            text=True
                        )
                        if sib_result.returncode == 0:
                            print(f"   ✅ {sibling['name']}: Branch created")
                        else:
                            # Try to switch to existing branch
                            switch_sib = subprocess.run(
                                ["git", "checkout", branch_name],
                                cwd=sibling["path"],
                                capture_output=True,
                                text=True
                            )
                            if switch_sib.returncode == 0:
                                print(f"   ✅ {sibling['name']}: Switched to existing branch")
                            else:
                                print(f"   ⚠️ {sibling['name']}: {sib_result.stderr.strip()}")
                                
        except Exception as e:
            print(f"⚠️ Failed to create branch: {e}")
        
        # Sync Kanban
        if card.item_id and project.get("kanban_id"):
            print("🔄 Syncing Kanban status...")
            sync_kanban_on_action("select_issue", project["kanban_id"], card.item_id)
        
        return True
    else:
        print(f"❌ {msg}")
        return False


def action_view_kanban(project: dict):
    """View Kanban status"""
    print(f"\n📊 Fetching {project['name']} Kanban...")
    
    cards = fetch_kanban_cards(project["kanban_number"])
    
    if not cards:
        print("📭 No cards found")
        return
    
    # Group by status
    by_status = {}
    for card in cards:
        status = card.status
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(card)
    
    print(f"\n{'─' * 60}")
    for status, items in by_status.items():
        print(f"\n📌 {status} ({len(items)})")
        for card in items[:5]:
            print(f"   #{card.issue_number}: {card.title[:45]}")
        if len(items) > 5:
            print(f"   ... and {len(items) - 5} more")
    print(f"\n{'─' * 60}")
    print(f"Total: {len(cards)} cards")


def action_list_active_issues(project: dict):
    """List all active issues (Backlog, Ready, In Progress)"""
    print(f"\n📋 Fetching Active Issues for {project['name']}...")
    
    cards = fetch_kanban_cards(project["kanban_number"])
    
    if not cards:
        print("📭 No cards found")
        return
    
    # Filter out Done/Closed
    ignored_statuses = ["Done", "Closed"]
    active_cards = [c for c in cards if c.status not in ignored_statuses]
    
    if not active_cards:
        print("✅ No active issues! All done.")
        return

    # Sort Logic: In Progress -> Ready -> Backlog -> Others
    priority = {"In Progress": 0, "Ready": 1, "Backlog": 2}
    
    def get_priority(card):
        return priority.get(card.status, 99)
    
    active_cards.sort(key=lambda c: (get_priority(c), c.issue_number))
    
    print(f"\n{'─' * 70}")
    print(f"{'#':<5} {'Title':<40} {'Status':<12} {'Repository'}")
    print(f"{'─' * 70}")
    
    for card in active_cards:
        # Title truncation
        title = card.title[:38] + ".." if len(card.title) > 40 else card.title
        
        # Colorize status (simulated with emojis)
        status_icon = ""
        if card.status == "In Progress": status_icon = "🔥 "
        elif card.status == "Ready": status_icon = "✅ "
        elif card.status == "Backlog": status_icon = "📥 "
        
        display_status = f"{status_icon}{card.status}"
        
        print(f"#{card.issue_number:<4} {title:<40} {display_status:<15} {card.repository.split('/')[-1]}")
    
    print(f"{'─' * 70}")
    print(f"Total Active: {len(active_cards)} issues")


def action_create_pr(state: LumaState, project: dict):
    """Create Pull Request with Pre-flight Checks"""
    if state.phase != WorkflowPhase.CODING:
        print(f"❌ Cannot create PR in '{state.phase.value}' phase")
        print("💡 Start coding first by selecting an issue")
        return
    
    if not state.active_issue or not state.active_branch:
        print("❌ No active issue/branch")
        return
    
    # 1. Transition to PREFLIGHT
    print("\n🔄 Transitioning to PREFLIGHT phase...")
    ok, msg = transition_to(state, WorkflowPhase.PREFLIGHT)
    if not ok:
        print(msg)
        return

    # 2. Run Pre-flight Checks
    print("🛫 Running Pre-flight Checks...")
    checker = PreflightChecker(project["path"])
    results = checker.run_checks()
    
    passed_all = True
    print("-" * 50)
    for res in results:
        icon = "✅" if res.passed else "❌"
        status = "PASS" if res.passed else "FAIL"
        print(f"{icon} [{status}] {res.name}: {res.message}")
        
        if not res.passed:
            passed_all = False
            
    print("-" * 50)
    
    if not passed_all:
        print("\n❌ One or more pre-flight checks failed.")
        print("💡 Please fix the issues above and try again.")
        
        override = input("⚠️ Force create PR anyways? (y/N): ").strip().lower()
        if not override:
            override = 'n'
            
        if override != 'y':
            # Revert to CODING
            transition_to(state, WorkflowPhase.CODING)
            return

    # 3. Proceed to Create PR
    print("\n🚀 Pre-flight checks passed (or overridden). Creating PR...")
    print(f"   Issue: #{state.active_issue.number} {state.active_issue.title}")
    print(f"   Branch: {state.active_branch}")
    
    # Enable GitHub Tools
    try:
        from luma_core.agents.publisher import publisher_agent
    except ImportError:
        print("❌ Publisher agent not available.")
        transition_to(state, WorkflowPhase.CODING)
        return
    
    # Construct a temporary state for the publisher
    pub_state = {
        "task": state.active_issue.title,
        "issue_data": {
            "title": state.active_issue.title,
            "number": state.active_issue.number
        },
        "repo": project["repo"],
        "target_dir": project["path"],
        "test_suggestions": ""
    }
    
    print("\n📤 invoking Publisher Agent...")
    result = publisher_agent(pub_state)
    pr_url = result.get("pr_url")
    
    if pr_url:
        print(f"\n✅ PR Created: {pr_url}")
        ok, msg = transition_to(state, WorkflowPhase.PR_PENDING, pr_url=pr_url)
        if ok:
             print("🔄 State updated to PR_PENDING")
        else:
             print(f"⚠️ Failed to update state: {msg}")
    else:
        print("\n⚠️ Publisher finished but no PR URL returned.")
        # Revert to CODING so they can retry
        transition_to(state, WorkflowPhase.CODING)


def action_code_review(state: LumaState, project: dict):
    """Run local code review agent"""
    print(f"\n🧐 Local Code Reviewer ({project['name']})")
    
    target_dir = project["path"]
    
    # 1. Get changed files
    try:
        from luma_core.agents.reviewer import reviewer_agent
        
        file_list = get_git_changed_files("all", target_dir=target_dir)
        if not file_list:
            print("✅ No changes found (Clean vs origin/main).")
            return
            
        print(f"   🔎 Found {len(file_list)} changed files.")
        
        # Limit files
        if len(file_list) > 30:
            print(f"⚠️ Too many files ({len(file_list)}). Reviewing top 10.")
            file_list = file_list[:10]
        
        changes = {}
        for rel_path in file_list:
            full_path = os.path.join(target_dir, rel_path)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                # Skip binary/large files heuristic
                if rel_path.endswith(('.png', '.jpg', '.ico', '.pdf', '.jar')):
                    continue
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        changes[rel_path] = f.read()
                except:
                    pass
        
        if not changes:
            print("❌ No readable content to review.")
            return

        # 2. Run Reviewer
        print(f"🚀 Running Reviewer on {list(changes.keys())}...")
        
        review_state = {
            "task": "Review local code changes for bugs, security issues, and best practices.",
            "changes": changes,
            "iterations": 0,
            "test_errors": "",
            "skip_coder": False
        }
        
        result = reviewer_agent(review_state)
        
        if result.get("code_content"):
            print("\n📝 Reviewer Feedback:")
            print("--------------------------------------------------")
            print(result["code_content"])
            print("--------------------------------------------------")
        
        if result.get("test_suggestions"):
            print("\n🧪 Test Suggestions:")
            print(result["test_suggestions"])
            
        # Save to file
        report_path = os.path.join(target_dir, "code_review.md")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("# Luma Code Review Report\n\n")
                f.write(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Files Reviewed:** {list(changes.keys())}\n\n")
                
                if result.get("code_content"):
                    f.write("## 📝 Reviewer Feedback\n\n")
                    f.write(result["code_content"] + "\n\n")
                
                if result.get("test_suggestions"):
                    f.write("## 🧪 Test Suggestions\n\n")
                    f.write(result["test_suggestions"] + "\n\n")
            print(f"\n✅ Review Report saved to: {report_path}")
        except Exception as e:
            print(f"\n⚠️ Failed to save report: {e}")
            
        print("\n✅ Review Complete.")
        
    except Exception as e:
        print(f"❌ Error during code review: {e}")


def action_update_docs(state: LumaState, project: dict):
    """Update documentation (Changelog, Version, README)"""
    print("\n📝 Documentation Update")
    print(f"   Project: {project['name']}")
    
    # 1. Determine Scope (Single vs Multi-Repo)
    # Check for explicit multi-repo flag in project config
    is_multi_repo = project.get("type") == "monorepo_root"
    target_repos = [project]
    
    if is_multi_repo:
        print("   Mode: Multi-Repo (JarWise)")
        # In a real dynamic system, we'd lookup sibling projects from the config
        # For now, hardcoded safe-check or assume PROJECTS dictionary has them
        # We will iterate through PROJECTS to find related ones if strict naming
        pass 
    
    print("\n🚀 Ready to update:")
    for repo in target_repos:
        print(f"   - {repo['name']}")
        
    confirm = input("\nProceed with docs update? (y/N): ").lower()
    if confirm != 'y':
        return

    # 2. Run Update
    print("\n⏳ Updating docs (AI-powered)...")
    results = update_multi_repo_docs(target_repos, docs_agent_func=None)
    
    # 3. Summary
    print("\n" + "=" * 40)
    print("📊 Docs Update Summary:")
    print("=" * 40)
    
    for r in results:
        status = "✅" if r.get("success") else "⏩"
        msg = ', '.join(r.get('files_updated', [])) if r.get("success") else r.get('error')
        print(f"   {status} {r['name']}: {msg}")
        
    print("\n✅ Done.")


def action_refine_issue(state: LumaState, project: dict):
    """Run Analyst Agent to refine issue"""
    if not state.active_issue:
        print("❌ No active issue selected to refine.")
        return

    # Enable Analyst Agent
    try:
        from luma_core.agents.analyst import analyst_agent
    except ImportError:
        print("❌ Analyst agent not available.")
        return

    # Create temporary state
    analyst_state = {
        "task": state.active_issue.title,
        "issue_data": {
            "title": state.active_issue.title,
            "number": state.active_issue.number,
            "body": state.active_issue.body
        },
        "target_dir": project["path"]
    }

    print("\n🧠 Invoking Analyst Agent...")
    result = analyst_agent(analyst_state)
    
    if result.get("analysis_file"):
        print(f"\n✨ Analysis complete! Document saved to: {result['analysis_file']}")
        input("Press Enter to continue...")
    else:
        print("\n⚠️ Analysis failed or produced no output.")

def action_switch_project(state: LumaState) -> str:
    """Switch to different project"""
    print("\n🔀 Select Project:")
    for key, proj in PROJECTS.items():
        print(f"  [{key}] {proj['name']}")
    
    choice = input("\nSelect: ").strip()
    
    if choice in PROJECTS:
        return choice
    
    return None


def action_generate_sbe(state: LumaState, project: dict):
    """Generate SBE (Specification by Example) for current issue"""
    if not state.active_issue:
        print("❌ No active issue selected.")
        print("💡 Select an issue first (Menu option 2)")
        return
    
    print("\n📋 SBE (Specification by Example) Generator")
    print(f"   Issue: #{state.active_issue.number} {state.active_issue.title}")
    
    # Enable SBE Agent
    try:
        from luma_core.agents.sbe_agent import sbe_agent
    except ImportError as e:
        print(f"❌ SBE agent not available: {e}")
        return
    
    # Create state for SBE agent
    sbe_state = {
        "task": state.active_issue.title,
        "issue_data": {
            "title": state.active_issue.title,
            "number": state.active_issue.number,
            "body": state.active_issue.body,
            "url": state.active_issue.html_url,
            "repository": state.active_issue.repository
        },
        "target_dir": project["path"]
    }
    
    print("\n🤖 Invoking SBE Agent (Integration -> Spec Agent)...")
    # Redirect legacy SBE to new Spec Agent if possible, or keep separate for now.
    # For now, let's keep SBE as a sub-feature, but we encourage using the full Spec Agent.
    result = sbe_agent(sbe_state)
    
    if result.get("sbe_file"):
        print(f"\n✨ SBE Specification created!")
        print(f"   📁 File: {result['sbe_file']}")
        
        # Preview first few lines
        try:
            with open(result['sbe_file'], 'r') as f:
                lines = f.readlines()[:15]
                print("\n📄 Preview:")
                print("-" * 50)
                for line in lines:
                    print(line.rstrip())
                if len(lines) >= 15:
                    print("...")
                print("-" * 50)
        except:
            pass
    else:
        print("\n⚠️ SBE generation failed or produced no output.")


def action_generate_draft(state: LumaState, project: dict):
    """Generate draft_code_review.md with full diff context"""
    print("\n📊 Generating Draft Code Review...")
    
    try:
        output_path = generate_draft_code_review(project["path"])
        print(f"\n✅ Draft saved to: {output_path}")
        print("   💡 This file can be used for PR creation and code review.")
        print("   📋 Publisher Agent will automatically use this file if present.")
        
        # Open in VS Code
        import subprocess
        try:
            subprocess.run(["code", output_path], capture_output=True)
            print("   📂 Opened in VS Code")
        except:
            pass
            
    except Exception as e:
        print(f"\n❌ Failed to generate draft: {e}")


def action_generate_spec(state: LumaState, project: dict):
    """Generate spec.md using Spec Agent"""
    if not state.active_issue:
        print("❌ No active issue selected.")
        return

    # Enable Spec Agent
    try:
        from luma_core.agents.spec_agent import spec_agent
    except ImportError as e:
        print(f"❌ Spec agent not available: {e}")
        return

    # Create State
    spec_state = {
        "task": state.active_issue.title,
        "issue_data": {
            "title": state.active_issue.title,
            "number": state.active_issue.number,
            "body": state.active_issue.body,
            "url": state.active_issue.html_url,
            "repository": state.active_issue.repository
        },
        "target_dir": project["path"]
    }

    print("\n🧬 Invoking Spec Agent (Spec Kit)...")
    result = spec_agent(spec_state)
    
    if result.get("feature_dir"):
        # Update state with feature dir for subsequent steps
        # In a real app, we might want to persist this in LumaState
        print(f"   📂 Feature Directory: {result['feature_dir']}")
        
        # Determine relative path for display
        rel_path = os.path.relpath(result['feature_dir'], project["path"])
        # Store in state for Plan Agent to use immediately
        state.context["last_feature_dir"] = result['feature_dir'] 
        print(f"   💡 Tip: Now you can generate the Plan (Menu Option 'P').")
        
    # Chain SBE Generation
    print("\n------------------------------------------------")
    # Chain SBE Generation
    print("\n------------------------------------------------")
    print("📋 Auto-generating Specification by Example (SBE)...")
    action_generate_sbe(state, project)


def action_generate_plan(state: LumaState, project: dict):
    """Generate plan.md using Architect Agent"""
    # Try to find feature dir: 1. From context, 2. Ask user
    feature_dir = state.context.get("last_feature_dir")
    
    if not feature_dir:
        # Simple heuristic: Look for valid feature dirs in docs/features
        # and ask user to pick
        features_root = os.path.join(project["path"], "docs", "features")
        if not os.path.exists(features_root):
            print("❌ No features directory found.")
            return

        dirs = [d for d in os.listdir(features_root) if os.path.isdir(os.path.join(features_root, d))]
        if not dirs:
            print("❌ No feature directories found.")
            return
            
        print("\n📂 Select Feature to Plan:")
        for i, d in enumerate(dirs, 1):
            print(f"  [{i}] {d}")
        
        choice = input("Select: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(dirs):
                feature_dir = os.path.join(features_root, dirs[idx])
            else:
                return
        except:
            return

    # Enable Architect Agent
    try:
        from luma_core.agents.architect_agent import architect_agent
    except ImportError as e:
        print(f"❌ Architect agent not available: {e}")
        return

    # Create State
    plan_state = {
        "feature_dir": feature_dir,
        "target_dir": project["path"]
    }

    print("\n🏗️ Invoking Architect Agent...")
    result = architect_agent(plan_state)

    if result.get("plan_file"):
        print(f"\n✨ Plan created at: {result['plan_file']}")


def action_update_roadmap(state: LumaState, project: dict):
    """Update ROADMAP.md status for an issue"""
    print(f"\n🗺️  Updating Roadmap for {project['name']}...")

    # Locate ROADMAP.md
    roadmap_paths = [
        os.path.join(project["path"], "docs", "ROADMAP.md"),
        os.path.join(project["path"], "ROADMAP.md")
    ]
    roadmap_path = next((p for p in roadmap_paths if os.path.exists(p)), None)

    if not roadmap_path:
        print(f"❌ Roadmap not found in docs/ or root.")
        return

    # Read content
    try:
        with open(roadmap_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Failed to read roadmap: {e}")
        return

    # Interactive: Select Issue
    issue_id = input("Enter Issue # to update (e.g. 65): ").strip().replace("#", "")
    if not issue_id:
        return

    # Find the block
    found_idx = -1
    for i, line in enumerate(lines):
        if f"**#{issue_id}" in line or f"#{issue_id} " in line:
            found_idx = i
            break

    if found_idx == -1:
        print(f"❌ Issue #{issue_id} not found in Roadmap.")
        return

    print(f"✅ Found issue at line {found_idx+1}: {lines[found_idx].strip()}")
    
    # Look for status line in next few lines
    status_idx = -1
    indent = "    - " # Default fallback indent
    
    for i in range(found_idx + 1, min(found_idx + 6, len(lines))):
        stripped = lines[i].strip()
        if stripped.startswith("- **Status:**") or stripped.startswith("- ✅ **Done**") or stripped.startswith("- 🟡 **In Progress**") or "Status:" in stripped or "✅ **Done**" in stripped:
            status_idx = i
            print(f"   Current: {stripped}")
            # Capture existing indentation
            indent = lines[i][:lines[i].find(stripped) + 2] # rough guess or just use standard
            if lines[i].startswith("    -"): indent = "    - "
            elif lines[i].startswith("\t-"): indent = "\t- "
            break

    # Ask for new status
    print("\nSelect new status:")
    print("  [1] ✅ Done")
    print("  [2] 🟢 Ready")
    print("  [3] 🟡 In Progress")
    print("  [4] 🔴 Blocked")
    
    status_choice = input("Select [1-4]: ").strip()
    
    new_status_line = ""
    
    if status_choice == "1":
        version = input("Enter Version (e.g. v1.8.0) [default: v1.8.0]: ").strip()
        if not version: version = "v1.8.0"
        note = input("Enter Completion Note: ").strip()
        
        new_status_line = f"{indent}✅ **Done** ({version})"
        if note:
             new_status_line += f" - {note}"
             
    elif status_choice == "2":
        new_status_line = f"{indent}**Status:** 🟢 **Ready**"
    elif status_choice == "3":
        new_status_line = f"{indent}**Status:** 🟡 **In Progress**"
    elif status_choice == "4":
        new_status_line = f"{indent}**Status:** 🔴 **Blocked**"
    else:
        print("❌ Invalid selection")
        return

    # Update logic
    if status_idx != -1:
        lines[status_idx] = new_status_line + "\n"
    else:
        print("⚠️  Status line not found nearby. Appending new status line.")
        lines.insert(found_idx + 2, new_status_line + "\n")

    # Write back
    try:
        with open(roadmap_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"✅ Roadmap updated successfully!")
    except Exception as e:
        print(f"❌ Failed to write roadmap: {e}")


def action_archive_artifacts(state: LumaState, project: dict):
    """Move active artifacts to feature directory"""
    if not state.active_issue:
        print("❌ No active issue to archive for.")
        return

    print(f"\n📦 Archiving artifacts for Issue #{state.active_issue.number}...")

    # Determine Feature Directory
    # Strategy: Try to find existing dir matching issue number
    features_root = os.path.join(project["path"], "docs", "features")
    if not os.path.exists(features_root):
        os.makedirs(features_root)

    feature_dir = None
    
    # 1. Check if we already have a context
    if state.context.get("last_feature_dir"):
        feature_dir = state.context.get("last_feature_dir")

    # 2. Search existing
    if not feature_dir:
        for d in os.listdir(features_root):
            if d.startswith(f"{state.active_issue.number}_") or f"issue-{state.active_issue.number}" in d:
                feature_dir = os.path.join(features_root, d)
                break
    
    # 3. Create new if needed
    if not feature_dir:
        slug = state.active_issue.title.lower().replace(" ", "-").replace("[", "").replace("]", "")[:50]
        dirname = f"{state.active_issue.number}_{slug}"
        feature_dir = os.path.join(features_root, dirname)
        os.makedirs(feature_dir, exist_ok=True)
        print(f"   📂 Created feature dir: {dirname}")
    else:
        print(f"   📂 Target: {os.path.basename(feature_dir)}")

    # Files to move
    # We look for these in the project root
    artifacts = [
        "analysis.md", "spec.md", "plan.md", "task.md", "walkthrough.md",
        "implementation_plan.md", "code_review.md" 
    ]
    # Also support platform specific variations like plan_android.md
    
    import shutil
    
    moved_count = 0
    
    # Scan root for exact matches and checking for prefix variations if needed
    for filename in os.listdir(project["path"]):
        # Check explicit list or pattern
        is_match = filename in artifacts
        
        # Check variations: plan_*.md, walkthrough_*.md
        if not is_match:
            if filename.startswith("plan_") and filename.endswith(".md"): is_match = True
            if filename.startswith("walkthrough_") and filename.endswith(".md"): is_match = True
        
        if is_match:
            src = os.path.join(project["path"], filename)
            dst = os.path.join(feature_dir, filename)
            
            try:
                shutil.move(src, dst)
                print(f"   ➡️  Moved {filename}")
                moved_count += 1
            except Exception as e:
                print(f"   ⚠️  Failed to move {filename}: {e}")

    if moved_count == 0:
        print("   (No artifacts found in root to move)")
    else:
        print(f"✅ Archived {moved_count} files.")


def get_feature_dir(project_path: str, issue_number: int) -> str:
    """Helper to find feature directory for an issue"""
    features_root = os.path.join(project_path, "docs", "features")
    if not os.path.exists(features_root):
        return None
        
    for d in os.listdir(features_root):
        # Match patterns: 71_..., issue-71..., x-issue-71..., etc.
        if d.startswith(f"{issue_number}_") or f"issue-{issue_number}" in d or f"-{issue_number}_" in d:
             return os.path.join(features_root, d)
    return None

def check_planning_artifacts(feature_dir: str) -> dict:
    """Check existence of planning artifacts"""
    artifacts = {
        "analysis": "analysis.md",
        "spec": "spec.md",
        "plan": "plan.md"
    }
    status = {}
    if not feature_dir or not os.path.exists(feature_dir):
        for k in artifacts: status[k] = False
        return status
        
    for key, filename in artifacts.items():
        status[key] = os.path.exists(os.path.join(feature_dir, filename))
    
    return status


def action_guided_workflow(state: LumaState, project: dict):
    """Run a guided end-to-end feature workflow"""
    print("\n⚡ Starting Guided Feature Workflow")
    print("====================================")
    
    # 1. Select Issue
    if not state.active_issue:
        print("\n🔹 Step 1: Select Issue")
        if not action_select_issue(state, project):
            print("❌ No issue selected. Aborting.")
            return
    else:
        print(f"\n🔹 Step 1: Issue #{state.active_issue.number} already selected.")

    # 2. Planning (Refine -> Spec -> Plan)
    print("\n🔹 Step 2: Planning Phase (Analyst -> Spec -> Architect)")
    
    # Check for existing artifacts
    feature_dir = get_feature_dir(project["path"], state.active_issue.number)
    # Also check context if just created
    if not feature_dir and state.context.get("last_feature_dir"):
        feature_dir = state.context.get("last_feature_dir")
    
    # Save to context immediately so action_generate_plan will use it
    if feature_dir:
        state.context["last_feature_dir"] = feature_dir
        
    artifacts_status = check_planning_artifacts(feature_dir)
    has_any = any(artifacts_status.values())
    
    run_planning = True
    planning_mode = "all" # all, missing, selective
    selected_steps = ["analysis", "spec", "plan"]
    
    if has_any:
        print(f"\n   📝 Found existing Planning Docs in {os.path.basename(feature_dir)}:")
        for k, exists in artifacts_status.items():
            icon = "[x]" if exists else "[ ]"
            print(f"      {icon} {k.capitalize()} ({k}.md)")
            
        print("\n   Select action:")
        print("   [1] Run All (Overwrite)")
        print("   [2] Generate Missing Only")
        print("   [3] Select Specific Documents")
        print("   [0] Skip Planning Phase")
        
        p_choice = input("\n   Select [0-3]: ").strip()
        
        if p_choice == "0":
            run_planning = False
        elif p_choice == "2":
            planning_mode = "missing"
        elif p_choice == "3":
            planning_mode = "selective"
            # Ask for selection
            selected_steps = []
            if input("      - Run Analysis? (y/N): ").lower() == 'y': selected_steps.append("analysis")
            if input("      - Run Spec? (y/N): ").lower() == 'y': selected_steps.append("spec")
            if input("      - Run Plan? (y/N): ").lower() == 'y': selected_steps.append("plan")
            if not selected_steps:
                print("      (No steps selected, skipping planning)")
                run_planning = False
        else:
            # Default to Run All
            planning_mode = "all"
            
    else:
        # Standard flow
        if input("   Run Planning Phase? (Y/n): ").lower() == 'n':
            run_planning = False

    if run_planning:
        # Execute based on mode/selection
        
        # 1. Analyst
        should_run_analyst = False
        if planning_mode == "all": should_run_analyst = True
        elif planning_mode == "missing" and not artifacts_status["analysis"]: should_run_analyst = True
        elif planning_mode == "selective" and "analysis" in selected_steps: should_run_analyst = True
        
        if should_run_analyst:
            action_refine_issue(state, project)
            # Update feature dir after analyst runs (it might have created it)
            feature_dir = get_feature_dir(project["path"], state.active_issue.number)
            state.context["last_feature_dir"] = feature_dir

        # 2. Spec
        should_run_spec = False
        if planning_mode == "all": should_run_spec = True
        elif planning_mode == "missing" and not artifacts_status["spec"]: should_run_spec = True
        elif planning_mode == "selective" and "spec" in selected_steps: should_run_spec = True
        
        if should_run_spec:
            action_generate_spec(state, project)
            # Update feature dir
            if state.context.get("last_feature_dir"):
                 feature_dir = state.context.get("last_feature_dir")

        # 3. Plan
        should_run_plan = False
        if planning_mode == "all": should_run_plan = True
        elif planning_mode == "missing" and not artifacts_status["plan"]: should_run_plan = True
        elif planning_mode == "selective" and "plan" in selected_steps: should_run_plan = True
        
        if should_run_plan:
            # Ensure feature_dir is in context so action_generate_plan doesn't ask again
            if feature_dir:
                state.context["last_feature_dir"] = feature_dir
            action_generate_plan(state, project)

    # 3. Coding (User)
    print("\n🔹 Step 3: Coding Phase")
    print("   🤖 AI Assist + 👤 Human Coding")
    
    # Offer Multi-Agent Swarm
    action_run_multi_agent_coding(state, project)
    
    print("   - Use your IDE to implement the feature.")
    print("   - Run 'Luma' > 'Code Review' periodically.")
    
    cont = input("\n   Have you finished coding and verified the feature? (y/N): ").lower()
    if cont != 'y':
        print("\n⏳ Pausing workflow. Come back when you're done!")
        return

    # 4. Review & Docs
    print("\n🔹 Step 4: Quality & Documentation")
    if input("   Run Code Review? (Y/n): ").lower() != 'n':
        action_code_review(state, project)
        
    if input("   Update Docs (Changelog/README/Version)? (Y/n): ").lower() != 'n':
        action_update_docs(state, project)

    # 5. Archive Artifacts
    print("\n🔹 Step 5: Archive Artifacts")
    if input("   Move artifacts to docs/features/...? (Y/n): ").lower() != 'n':
        action_archive_artifacts(state, project)

    # 6. Create PR
    print("\n🔹 Step 6: Create Pull Request")
    if input("   Create PR now? (Y/n): ").lower() != 'n':
        action_create_pr(state, project)
        
        # Poll for Merge?
        if state.phase == WorkflowPhase.PR_PENDING and state.pr_url:
            print(f"\n⏳ PR Created: {state.pr_url}")
            print("   Please merge the PR on GitHub.")
            input("   Press Enter AFTER you have merged the PR...")
            
            # Use the refresh check logic from main loop or just assume
            from luma_core.github_project import check_pr_merged
            pr_status = check_pr_merged(state.pr_url)
            if pr_status["merged"]:
                print("✅ PR Merged confirmed!")
            else:
                 print("⚠️ PR not detected as merged yet, but proceeding...")
    
    # 7. Update Roadmap & Next
    print("\n🔹 Step 7: Finalize")
    
    if input("   Update Project Documentation (README/Changelog)? (Y/n): ").lower() != 'n':
        action_update_docs(state, project)

    if input("   Update Roadmap? (Y/n): ").lower() != 'n':
        action_update_roadmap(state, project)
        
    print("\n🎉 Workflow Completed! You can now select the next issue.")


def action_run_multi_agent_coding(state: LumaState, project: dict):
    """Run sequential AI coding agents for different stacks."""
    print("\n🤖 Multi-Agent Auto-Coding Swarm")
    print("==================================")
    print("Which agents would you like to compile?")
    print("  [1] All (Frontend + Backend + Android)")
    print("  [2] Frontend (Web)")
    print("  [3] Backend (Go/Python)")
    print("  [4] Android (Kotlin)")
    print("  [5] 📝 Generate Prompts Only (for manual use)")
    print("  [0] Skip (Manual Coding)")
    
    choice = input("\nSelect [0-5]: ").strip()
    
    if choice == "0":
        return

    # Define agents config
    agents_to_run = []
    generate_prompts_only = False
    
    if choice == "1":
        agents_to_run = ["frontend", "backend", "android"]
    elif choice == "2":
        agents_to_run = ["frontend"]
    elif choice == "3":
        agents_to_run = ["backend"]
    elif choice == "4":
        agents_to_run = ["android"]
    elif choice == "5":
        agents_to_run = ["frontend", "backend", "android"]
        generate_prompts_only = True
    else:
        print("❌ Invalid selection.")
        return

    # Import Coder
    try:
        from luma_core.agents.coder import coder_agent
    except ImportError:
        print("❌ Coder Agent not found.")
        return

    # Execution Loop
    for agent_type in agents_to_run:
        print(f"\n🚀 Preparing {agent_type.upper()} context...")
        
        # 1. Prepare Context based on type
        # In a real system, we'd read from plan.md to get specific tasks per platform
        # For now, we use a generic task + specific path scope
        
        sub_task = f"Implement {agent_type} components for Issue #{state.active_issue.number}: {state.active_issue.title}"
        source_paths = []
        
        tech_stack = ""
        if agent_type == "frontend":
            tech_stack = "React/Vue/Web technologies. Focus on UI implementation."
            if os.path.exists(os.path.join(project["path"], "Web")):
                source_paths.append("Web/package.json")
        elif agent_type == "backend":
            tech_stack = "Go/Python. Implement API endpoints and business logic."
            if os.path.exists(os.path.join(project["path"], "backend")):
                source_paths.append("backend/go.mod")
        elif agent_type == "android":
            tech_stack = "Kotlin/Jetpack Compose. Implement Mobile UI and ViewModel. IMPORTANT: Do NOT use ./gradlew directly. You MUST use scripts in ./Android/scripts/ (e.g. ./Android/scripts/run_tests.sh, ./Android/scripts/build.sh)."
            if os.path.exists(os.path.join(project["path"], "view")): # Legacy or Luma specific
                 pass
        
        sub_task += f" Use {tech_stack}"
        
        
        # --- NEW: Context from Artifacts ---
        artifact_context = ""
        feature_dir = None
        
        # 1. Try to find feature dir
        if state.context.get("last_feature_dir"):
            feature_dir = state.context.get("last_feature_dir")
        
        if not feature_dir:
             features_root = os.path.join(project["path"], "docs", "features")
             if os.path.exists(features_root):
                 for d in os.listdir(features_root):
                    if d.startswith(f"{state.active_issue.number}_") or f"issue-{state.active_issue.number}" in d:
                        feature_dir = os.path.join(features_root, d)
                        break
        
        if feature_dir and os.path.exists(feature_dir):
            print(f"   📂 Loading context from: {os.path.basename(feature_dir)}...")
            docs_to_read = ["analysis.md", "plan.md", "spec.md", "implementation_plan.md", f"plan_{agent_type}.md"]
            
            for doc in docs_to_read:
                doc_path = os.path.join(feature_dir, doc)
                if os.path.exists(doc_path):
                    try:
                        with open(doc_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            artifact_context += f"\n\n## Reference: {doc}\n{content[:5000]}\n(truncated if too long)\n"
                    except:
                        pass
        else:
             print("   ⚠️ No feature directory found. Using generic context.")

        if generate_prompts_only:
             # Just generate the prompt text file
             prompt_file = os.path.join(project["path"], f"prompt_{agent_type}.txt")
             
             prompt_content = f"""# Role: Senior {agent_type.capitalize()} Developer
# Task: {sub_task}

Please write the code for the following requirements.

## Context
Project: {project['name']}
Issue: #{state.active_issue.number} {state.active_issue.title}
Body:
{state.active_issue.body or "No details provided."}

## Architecture & Plans (AUTHORITATIVE)
The following content is from the approved design documents. **You MUST follow this design.**
{artifact_context}

## Default Guidance (Use only if not specified in Plans)
- Tech Stack: {tech_stack}
- Follow Clean Architecture
- Ensure TDD (Test Driven Development)

**IMPORTANT CONFLICT RESOLUTION:**
If the 'Architecture & Plans' section conflicts with the 'Default Guidance', **FOLLOW THE PLANS**.

## Output Format
Please provide the full code files wrapped in XML tags:
<file path="path/to/file.ext">
... code ...
</file>

## Language
Please explain your solution and comments in Thai only.
"""
             with open(prompt_file, "w", encoding="utf-8") as f:
                 f.write(prompt_content)
             print(f"   📄 Generated prompt file: {os.path.basename(prompt_file)}")
             continue

        # Create scoped state
        agent_state = {
            "task": sub_task,
            "source_files": source_paths,
            "iterations": 0,
            "test_errors": "",
            "skip_coder": False
        }
        
        # 2. Run Agent
        try:
            print(f"   🤖 Running {agent_type} agent...")
            result = coder_agent(agent_state)
            
            # 3. Apply Changes (Simulation)
            changes = result.get("changes", {})
            if changes:
                print(f"   📝 Agent proposed {len(changes)} file changes:")
                for path in changes:
                    print(f"      - {path}")
                
                # In fully auto mode, we might write them. 
                # For safety in this CLI, we ask or just save a patch.
                # Let's save a "patch" file for the user to review.
                patch_file = os.path.join(project["path"], f"agent_{agent_type}_patch.xml")
                with open(patch_file, "w") as f:
                    f.write(result.get("code_content", ""))
                print(f"   💾 Saved proposed changes to: {os.path.basename(patch_file)}")
            else:
                print("   🤷 Agent decided not to change any code.")
                
        except Exception as e:
            print(f"   ⚠️ Agent Error: {e}")
            
    if generate_prompts_only:
        print("\n✅ Prompts generated! You can now use 'prompt_*.txt' files with your preferred AI.")
    else:
        print("\n✅ Multi-Agent session finished. Review the 'agent_*_patch.xml' files.")



