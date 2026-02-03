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
    ask_sbe = input("❓ Generate Specification by Example (SBE) tables / QA Docs? (Y/n): ").strip().lower()
    if ask_sbe != 'n':
        # Chain call to existing SBE action in this module
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

    plan_state = {
        "feature_dir": feature_dir,
        "target_dir": project["path"]
    }

    print("\n📐 Invoking Architect Agent (Spec Kit)...")
    result = architect_agent(plan_state)
    
    if result.get("plan_file"):
        print(f"\n✨ Plan created at: {result['plan_file']}")

