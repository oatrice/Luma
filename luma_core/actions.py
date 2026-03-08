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
from luma_core.agents.publisher import publisher_agent

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
    
    # Filter for Ready, In Progress, or Todo
    valid_statuses = ["Ready", "In Progress", "Todo"]
    selectable_issues = []
    
    for card in all_cards:
        # Case-insensitive check
        if any(s.lower() == card.status.lower() for s in valid_statuses):
            selectable_issues.append(card)
            
    if not selectable_issues:
        print("📭 No 'Ready', 'In Progress', or 'Todo' issues found on Kanban.")
        return False
    
    # Sort: In Progress -> Ready -> Todo
    def sort_key(c):
        status = c.status.lower()
        if status == "in progress":
            return (0, c.issue_number)
        elif status == "ready":
            return (1, c.issue_number)
        elif status == "todo":
            return (2, c.issue_number)
        return (3, c.issue_number)
        
    selectable_issues.sort(key=sort_key)
    
    print("\n--- 📋 Select Issue to Work On ---")
    for i, card in enumerate(selectable_issues, 1):
        status_icon = "🔥" if card.status.lower() == "in progress" else "✅"
        print(f"  [{i}] {status_icon} #{card.issue_number}: {card.title[:50]} ({card.status})")
    print("  [0] Cancel")
    print("  ℹ️  Comma-separated for multi-select (e.g. 1,3)")
    
    choice = input("\nSelect issue(s): ").strip()
    
    if choice == "0":
        return False
    
    # Parse multi-select (e.g. "1,3" or "1")
    try:
        indices = [int(x.strip()) - 1 for x in choice.split(",")]
        selected_cards = []
        for idx in indices:
            if 0 <= idx < len(selectable_issues):
                selected_cards.append(selectable_issues[idx])
            else:
                print(f"❌ Invalid index: {idx + 1}")
                return False
        if selected_cards:
            return _start_issues(state, selected_cards, project)
    except ValueError as e:
        import traceback
        traceback.print_exc()
        pass
    
    print("❌ Invalid selection")
    return False


def _start_issues(state: LumaState, cards: list, project: dict) -> bool:
    """Start working on one or more issues"""
    
    # Check if ALL these issues are already active (re-selecting same set)
    active_nums = {i.number for i in state.active_issues} if state.active_issues else set()
    card_nums = {c.issue_number for c in cards}
    
    if active_nums == card_nums and state.active_branch:
        print(f"\n✅ Already working on {', '.join(f'#{n}' for n in card_nums)} - continuing...")
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
    
    # Create IssueData list
    issues = []
    for card in cards:
        issues.append(IssueData(
            number=card.issue_number,
            title=card.title,
            html_url=card.url,
            body=card.body,
            project_item_id=card.item_id,
            project_id=project["kanban_id"],
            repository=card.repository
        ))
    
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
    
    # Suggest branch name (with multi-issue numbers)
    issue_nums = "-".join(str(c.issue_number) for c in cards)
    primary_title = cards[0].title
    primary_body = cards[0].body or ""
    primary_number = cards[0].issue_number
    
    try:
        from luma_core.agents.analyst import generate_branch_names
        suggestions = generate_branch_names(primary_title, primary_body, primary_number)
        # Replace single issue number with multi-issue numbers in suggestions
        if len(cards) > 1:
            suggestions = [s.replace(f"/{primary_number}-", f"/{issue_nums}-") for s in suggestions]
    except Exception as e:
        print(f"⚠️ AI Agent unavailable: {e}")
        slug = primary_title.lower().replace(" ", "-").replace("[", "").replace("]", "")[:30]
        suggestions = [f"feat/{issue_nums}-{slug}"]

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
        active_issues=issues,
        active_branch=branch_name
    )
    
    if ok:
        issue_display = ", ".join(f"#{c.issue_number}" for c in cards)
        print(f"\n✅ Started: {issue_display}")
        for c in cards:
            print(f"   🎯 #{c.issue_number}: {c.title[:50]}")
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
            
            # Create branches in sibling repos
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
        
        # Sync Kanban for all issues
        for i, card in enumerate(cards):
            if card.item_id and project.get("kanban_id"):
                if i == 0:
                    print("🔄 Syncing Kanban status...")
                sync_kanban_on_action("select_issue", project["kanban_id"], card.item_id)
        
        return True
    else:
        print(f"❌ {msg}")
        return False


def action_add_issue(state: LumaState, project: dict) -> bool:
    """Add an issue to the current active issues (mid-work)"""
    if state.phase not in [WorkflowPhase.CODING, WorkflowPhase.PREFLIGHT]:
        print("❌ Can only add issues during CODING or PREFLIGHT phase.")
        return False
    
    print("\n\u2795 Add Issue to Current Work Session")
    if state.active_issues:
        print(f"   Current issues: {', '.join(f'#{i.number}' for i in state.active_issues)}")
    
    all_cards = fetch_kanban_cards(project["kanban_number"])
    active_nums = {i.number for i in state.active_issues}
    
    valid_statuses = ["Ready", "In Progress", "Todo"]
    selectable = [c for c in all_cards 
                  if any(s.lower() == c.status.lower() for s in valid_statuses)
                  and c.issue_number not in active_nums]
    
    if not selectable:
        print("\ud83d\udced No additional issues available.")
        return False
    
    for i, card in enumerate(selectable, 1):
        print(f"  [{i}] #{card.issue_number}: {card.title[:50]} ({card.status})")
    print("  [0] Cancel")
    
    choice = input("\nSelect issue to add: ").strip()
    if choice == "0":
        return False
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(selectable):
            card = selectable[idx]
            new_issue = IssueData(
                number=card.issue_number,
                title=card.title,
                html_url=card.url,
                body=card.body,
                project_item_id=card.item_id,
                project_id=project["kanban_id"],
                repository=card.repository
            )
            state.active_issues.append(new_issue)
            print(f"✅ Added #{card.issue_number}: {card.title[:40]}")
            print(f"   Active issues: {', '.join(f'#{i.number}' for i in state.active_issues)}")
            
            # Sync Kanban
            if card.item_id and project.get("kanban_id"):
                sync_kanban_on_action("select_issue", project["kanban_id"], card.item_id)
            return True
    except ValueError:
        pass
    
    print("❌ Invalid selection")
    return False


def action_remove_issue(state: LumaState, project: dict) -> bool:
    """Remove an issue from the current active issues"""
    if not state.active_issues or len(state.active_issues) <= 1:
        print("❌ Cannot remove: need at least 1 active issue.")
        return False
    
    print("\n\u2796 Remove Issue from Current Work Session")
    for i, issue in enumerate(state.active_issues, 1):
        primary = " (primary)" if i == 1 else ""
        print(f"  [{i}] #{issue.number}: {issue.title[:50]}{primary}")
    print("  [0] Cancel")
    
    choice = input("\nSelect issue to remove: ").strip()
    if choice == "0":
        return False
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(state.active_issues):
            removed = state.active_issues.pop(idx)
            print(f"✅ Removed #{removed.number}: {removed.title[:40]}")
            print(f"   Remaining: {', '.join(f'#{i.number}' for i in state.active_issues)}")
            return True
    except ValueError:
        pass
    
    print("❌ Invalid selection")
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

    # Sort Logic: In Progress -> Ready -> Todo -> Backlog -> Others
    priority = {"In Progress": 0, "Ready": 1, "Todo": 2, "Backlog": 3}
    
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
        elif card.status == "Todo": status_icon = "📝 "
        elif card.status == "Backlog": status_icon = "📥 "
        
        display_status = f"{status_icon}{card.status}"
        
        print(f"#{card.issue_number:<4} {title:<40} {display_status:<15} {card.repository.split('/')[-1]}")
    
    print(f"{'─' * 70}")
    print(f"Total Active: {len(active_cards)} issues")


def action_create_pr(state: LumaState, project: dict, auto_approve: bool = False):
    """Create Pull Request with Pre-flight Checks"""
    # Allow if Coding OR (PR_Pending to sync other repos) OR Preflight (Retry)
    allowed_phases = [WorkflowPhase.CODING, WorkflowPhase.PR_PENDING, WorkflowPhase.PREFLIGHT]
    if state.phase not in allowed_phases:
        print(f"❌ Cannot create PR in '{state.phase.value}' phase")
        print("💡 Start coding first by selecting an issue")
        return
    
    if not state.active_issues or not state.active_branch:
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
        
        override = 'y' if auto_approve else input("⚠️ Force create PR anyways? (y/N): ").strip().lower()
        if override != 'y':
            # Revert to CODING
            transition_to(state, WorkflowPhase.CODING)
            return

    # 3. Ask for Mode if not auto-approved already
    if not auto_approve:
        print("\n🤖 PR Creation Mode:")
        mode = input("   [y] Interactive (Confirm each)\n   [a] Auto-Approve ALL\n   [n] Cancel / Back to Coding\n   Select: ").strip().lower()
        
        if mode == 'n':
            print("❌ Operation cancelled.")
            transition_to(state, WorkflowPhase.CODING)
            return

        if mode == 'a':
            print("   ✅ Auto-Approve enabled for all repos.")
            auto_approve = True

    # Determine target repos (Multi-Repo Support)
    target_projects = [project]
    if project.get("type") == "monorepo_root" and project.get("sibling_repos"):
        print("   Mode: Multi-Repo (JarWise) - Checking all repos...")
        try:
             for sibling_key in project.get("sibling_repos", []):
                 if sibling_key in PROJECTS:
                     target_projects.append(PROJECTS[sibling_key])
        except Exception:
            pass

    # --- SCREENSHOT LOGIC ---
    screenshot_md = ""
    feature_dir = state.context.get("last_feature_dir")
    screenshots_to_sync = []
    
    if feature_dir:
        sc_dir = os.path.join(feature_dir, "screenshots")
        if os.path.exists(sc_dir):
            files = [f for f in os.listdir(sc_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
            if files:
                print(f"   📸 Found {len(files)} screenshots to attach...")
                for f in files:
                    screenshots_to_sync.append(os.path.join(sc_dir, f))

    for proj in target_projects:
        print(f"\n🚀 Processing {proj['name']}...")
        
        # Check if this repo is on the correct branch or has relevant changes
        # Simple check: Is current branch == active_branch?
        import subprocess
        try:
            br_res = subprocess.run(["git", "branch", "--show-current"], cwd=proj["path"], capture_output=True, text=True)
            curr_br = br_res.stdout.strip()
            if curr_br != state.active_branch:
                print(f"   ⏩ Skipping {proj['name']} (Branch mismatch: {curr_br} != {state.active_branch})")
                continue
            
            # Check for commits ahead of main
            commits_res = subprocess.run(
                ["git", "rev-list", "--count", "origin/main..HEAD"], 
                cwd=proj["path"], capture_output=True, text=True
            )
            commits_ahead = int(commits_res.stdout.strip() or "0")
            
            if commits_ahead == 0:
                print(f"   ⏩ Skipping {proj['name']} (No commits ahead of main)")
                continue

        except Exception as e:
            print(f"   ⚠️ Error checking repo {proj['name']}: {e}")
            continue

        # Check for existing PR
        from luma_core.github_client import get_open_pr
        repo_name = proj.get("repo")
        if repo_name:
            existing = get_open_pr(repo_name, state.active_branch)
            if existing:
                 print(f"   ⏩ Skipping {proj['name']} (PR already exists: {existing['html_url']})")
                 continue
        
        # --- SYNC SCREENSHOTS TO TARGET REPO ---
        repo_screenshot_section = ""
        ai_brain_section = ""
        if screenshots_to_sync:
            try:
                # 1. Create docs/screenshots/issue-N/ in target repo
                issue_id = state.active_issue.number
                target_sc_dir = os.path.join(proj["path"], "docs", "screenshots", f"issue-{issue_id}")
                os.makedirs(target_sc_dir, exist_ok=True)
                
                repo_screenshot_section = "\n\n## 📸 Screenshots\n"
                
                import shutil
                git_add_files = []
                
                for src_path in screenshots_to_sync:
                    filename = os.path.basename(src_path)
                    dst_path = os.path.join(target_sc_dir, filename)
                    
                    if not os.path.exists(dst_path) or os.path.getsize(src_path) != os.path.getsize(dst_path):
                        shutil.copy2(src_path, dst_path)
                        print(f"      - Copied {filename} to {proj['name']}")
                    
                    # Relative path for file operation
                    rel_path = f"docs/screenshots/issue-{issue_id}/{filename}"
                    git_add_files.append(rel_path)
                    
                    # Markdown Link for PR Body (Must use Raw URL for new files to render in PR description)
                    # format: https://raw.githubusercontent.com/{owner_repo}/{branch}/{path}
                    if proj.get("repo") and state.active_branch:
                        raw_url = f"https://raw.githubusercontent.com/{proj['repo']}/{state.active_branch}/{rel_path}"
                        # Encoding spaces just in case, though filenames likely safe
                        from urllib.parse import quote
                        # We only encode the path part if needed, but simple f-string is usually fine for strict filenames
                        repo_screenshot_section += f"![{filename}]({raw_url})\n"
                    else:
                        # Fallback if repo info missing
                        repo_screenshot_section += f"![{filename}]({rel_path})\n"
                
                # 2. Git Add the screenshots
                if git_add_files:
                    subprocess.run(["git", "add"] + git_add_files, cwd=proj["path"], check=False)
                    subprocess.run(["git", "commit", "-m", "docs: add screenshots"], cwd=proj["path"], check=False, capture_output=True)
                    
            except Exception as e:
                print(f"   ⚠️ Failed to sync screenshots: {e}")

        # --- SYNC AI BRAIN ARTIFACTS ---
        try:
            from luma_core.ai_brain_sync import AntigravityBrain
            print("   🔄 Syncing AI Agent Brain Artifacts...")
            brain_session = state.context.get("selected_brain_session")
            synced_docs = AntigravityBrain.sync_to_repo(proj["path"], state.active_issue.number, session_path=brain_session)
            
            if synced_docs:
                subprocess.run(["git", "add"] + synced_docs, cwd=proj["path"], check=False)
                subprocess.run(["git", "commit", "-m", "docs: sync AI brain artifacts"], cwd=proj["path"], check=False, capture_output=True)
                print(f"   ✅ Merged AI Brain Context to {proj['name']}")
                
                ai_brain_section = "\n\n## 🧠 AI Brain Context\n"
                for doc in synced_docs:
                    filename = os.path.basename(doc)
                    if proj.get("repo") and state.active_branch:
                        raw_url = f"https://raw.githubusercontent.com/{proj['repo']}/{state.active_branch}/{doc}"
                        ai_brain_section += f"- [{filename}]({raw_url})\n"
                    else:
                        ai_brain_section += f"- [{filename}]({doc})\n"
        except Exception as e:
            print(f"   ⚠️ Failed to sync AI brain artifacts: {e}")

        # 3. Proceed to Create PR for this repo
        if not auto_approve:
            confirm = input(f"   ✨ Create PR for {proj['name']}? (Y/n): ").strip().lower()
            if confirm == 'n': continue

        print(f"   ✨ Creating PR for {proj['name']}...")
        
        # Construct a temporary state for the publisher
        # Append screenshots and AI brain context to body
        # Multi-issue: combine all issue bodies + closing references
        primary_issue = state.active_issue
        
        if len(state.active_issues) > 1:
            closes_line = ", ".join(f"Closes #{i.number}" for i in state.active_issues)
            issues_section = "\n\n## Issues\n" + "\n".join(
                f"- #{i.number}: {i.title}" for i in state.active_issues
            )
            combined_body = (primary_issue.body or "") + issues_section + repo_screenshot_section + ai_brain_section
            pr_title = f"{primary_issue.title} (#{', #'.join(str(i.number) for i in state.active_issues)})"
        else:
            closes_line = f"Closes #{primary_issue.number}"
            combined_body = (primary_issue.body or "") + repo_screenshot_section + ai_brain_section
            pr_title = primary_issue.title
        
        # Add closes line at the end
        combined_body += f"\n\n{closes_line}"
        
        pub_state = {
            "task": pr_title,
            "issue_data": {
                "title": pr_title,
                "number": primary_issue.number,
                "body": combined_body,
                "url": getattr(primary_issue, 'html_url', f"https://github.com/{project['repo']}/issues/{primary_issue.number}")
            },
            "repo": proj["repo"],
            "issue_source_repo": project["repo"],
            "target_dir": proj["path"],
            "test_suggestions": "",
            "auto_approve": auto_approve
        }
        
        print(f"   📤 Invoking Publisher Agent for {proj['name']}...")
        result = publisher_agent(pub_state)
        pr_url = result.get("pr_url")
        
        if pr_url:
            print(f"   ✅ PR Created: {pr_url}")
            # Update state with the created PR url
            if proj == project:
                 ok, msg = transition_to(state, WorkflowPhase.PR_PENDING, pr_url=pr_url)
                 if ok:
                      print("   🔄 State updated to PR_PENDING")
        else:
            print(f"   ⚠️ Publisher finished but no known PR URL.")

def action_sync_ai_brain(state: LumaState, project: dict) -> bool:
    """Manually trigger AI Brain Sync with preview + confirm + session picker. Supports Antigravity and Gemini CLI."""
    if not state.active_issue:
        print("❌ No active issue selected. Please select an issue first.")
        return False
        
    print(f"\n🧠 Syncing AI Agent Brain Artifacts for {project['name']}...")
    all_synced_docs = []
    
    # 1. Try Antigravity Brain
    try:
        from luma_core.ai_brain_sync import AntigravityBrain, GeminiCLIBrain
        
        sessions = AntigravityBrain.get_all_sessions()
        if sessions:
            # Preview latest session
            latest = sessions[0]
            print(f"\n   📂 [Antigravity] Latest Session: {latest['session_id'][:12]}...")
            print(f"   📄 Preview: {latest['preview']}")
            
            confirm = input("\n   ✅ Use this Antigravity session? (Y/n/s to skip): ").strip().lower()
            
            if confirm != "s":
                selected_path = latest["path"]
                
                if confirm == "n":
                    # Show session picker
                    print(f"\n   📋 Available Antigravity Sessions:")
                    display_limit = min(8, len(sessions))
                    for i, s in enumerate(sessions[:display_limit]):
                        print(f"   [{i+1}] {s['session_id'][:12]}... — {s['preview'][:50]}")
                    
                    choice = input(f"\n   Select session [1-{display_limit}] or [c] Cancel: ").strip().lower()
                    if choice != "c" and choice:
                        try:
                            idx = int(choice) - 1
                            if 0 <= idx < display_limit:
                                selected_path = sessions[idx]["path"]
                                print(f"   🔗 Selected: {sessions[idx]['session_id'][:12]}...")
                                synced_antigravity = AntigravityBrain.sync_to_repo(project["path"], state.active_issue.number, session_path=selected_path)
                                all_synced_docs.extend(synced_antigravity)
                                state.context["selected_brain_session"] = selected_path
                        except ValueError:
                            pass
                else:
                    synced_antigravity = AntigravityBrain.sync_to_repo(project["path"], state.active_issue.number, session_path=selected_path)
                    all_synced_docs.extend(synced_antigravity)
                    state.context["selected_brain_session"] = selected_path
        else:
            print("ℹ️ No Antigravity sessions found.")

    except Exception as e:
        print(f"⚠️ Antigravity sync failed: {e}")

    # 2. Try Gemini CLI Brain
    try:
        from luma_core.ai_brain_sync import GeminiCLIBrain
        print("\n   🔍 Checking Gemini CLI session artifacts...")
        
        gemini_sessions = GeminiCLIBrain.get_all_sessions()
        if gemini_sessions:
            latest = gemini_sessions[0]
            print(f"\n   📂 [Gemini CLI] Latest Session: {latest['session_id'][:12]}...")
            print(f"   📄 Preview: {latest['preview'][:80]}")
            
            confirm = input("\n   ✅ Sync this Gemini CLI session? (Y/n/s to skip): ").strip().lower()
            
            if confirm != "s":
                selected_path = latest["path"]
                
                if confirm == "n":
                    # Show session picker
                    print(f"\n   📋 Available Gemini CLI Sessions:")
                    display_limit = min(8, len(gemini_sessions))
                    for i, s in enumerate(gemini_sessions[:display_limit]):
                        print(f"   [{i+1}] {s['session_id'][:12]}... — {s['preview'][:60]}")
                    
                    choice = input(f"\n   Select session [1-{display_limit}] or [c] Cancel: ").strip().lower()
                    if choice != "c" and choice:
                        try:
                            idx = int(choice) - 1
                            if 0 <= idx < display_limit:
                                selected_path = gemini_sessions[idx]["path"]
                                print(f"   🔗 Selected: {gemini_sessions[idx]['session_id'][:12]}...")
                                synced_gemini = GeminiCLIBrain.sync_to_repo(project["path"], state.active_issue.number, session_path=selected_path)
                                all_synced_docs.extend(synced_gemini)
                        except ValueError:
                            pass
                else:
                    synced_gemini = GeminiCLIBrain.sync_to_repo(project["path"], state.active_issue.number, session_path=selected_path)
                    all_synced_docs.extend(synced_gemini)
        else:
            print("   ℹ️ No Gemini CLI session artifacts found.")
    except Exception as e:
        print(f"⚠️ Gemini CLI sync failed: {e}")

    if all_synced_docs:
        print(f"\n✅ Successfully synced {len(all_synced_docs)} files from AI Brain(s).")
        for doc in all_synced_docs:
            print(f"  - {doc}")
        print(f"💡 The files have been copied to the project. You can review and commit them manually.")
        return True
    else:
        print("\n⚠️ No new artifacts to sync (content unchanged or no sources found).")
        return False

def action_code_review(state: LumaState, project: dict):
    """Run local code review agent"""
    print(f"\n🧐 Local Code Reviewer")
    
    # Determine target repos (Multi-Repo Support)
    target_projects = [project]
    if project.get("type") == "monorepo_root" and project.get("sibling_repos"):
        print("   Mode: Multi-Repo (JarWise) - Checking all repos...")
        try:
             for sibling_key in project.get("sibling_repos", []):
                 if str(sibling_key) in PROJECTS:
                     target_projects.append(PROJECTS[str(sibling_key)])
        except Exception:
            pass

    for proj in target_projects:
        print(f"\n🚀 Reviewing {proj['name']}...")
        target_dir = proj["path"]
    
        # 1. Get changed files
        try:
            from luma_core.agents.reviewer import reviewer_agent
            
            file_list = get_git_changed_files("all", target_dir=target_dir)
            if not file_list:
                print(f"   ✅ {proj['name']}: No changes found (Clean vs origin/main).")
                continue
                
            print(f"   🔎 Found {len(file_list)} changed files in {proj['name']}.")
            
            # Limit files
            if len(file_list) > 30:
                print(f"   ⚠️ Too many files ({len(file_list)}). Reviewing top 10.")
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
                print("   ❌ No readable content to review.")
                continue

            # 2. Run Reviewer
            print(f"   🚀 Running Reviewer on {list(changes.keys())}...")
            
            review_state = {
                "task": "Review local code changes for bugs, security issues, and best practices.",
                "changes": changes,
                "iterations": 0,
                "test_errors": "",
                "skip_coder": False
            }
            
            result = reviewer_agent(review_state)
            
            if result.get("code_content"):
                print("\n   📝 Reviewer Feedback:")
                print("   --------------------------------------------------")
                print(result["code_content"])
                print("   --------------------------------------------------")
            
            if result.get("test_suggestions"):
                print("\n   🧪 Test Suggestions:")
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
                print(f"\n   ✅ Review Report saved to: {report_path}")
            except Exception as e:
                print(f"\n   ⚠️ Failed to save report: {e}")
                
            print(f"\n   ✅ Review Complete for {proj['name']}.")
            
            # Print the prompt for the user to copy and paste to the AI assistant
            print("\n" + "="*60)
            print("💡 COPY THIS PROMPT FOR THE AI ASSISTANT:")
            print("="*60)
            if len(target_projects) > 1:
                print("นำ code review จาก terminal และ code_review.md (อาจจะติด gitignored ต้องเข้าไปอ่านตรงๆ) ในทุก repo มาอธิบาย และถามเพื่อ clarify ด้วย และให้ทำตาม Test suggestion ทั้งหมดด้วย")
            else:
                print("นำ code review จาก terminal และ code_review.md (อาจจะติด gitignored ต้องเข้าไปอ่านตรงๆ) มาอธิบาย และถามเพื่อ clarify ด้วย และให้ทำตาม Test suggestion ทั้งหมดด้วย")
            print("="*60)
            
            print("\n" + "🧪"*10 + " RE-VERIFY INSTRUCTION " + "🧪"*10)
            print("หลังจากแก้ไขโค้ดตาม Code Review เสร็จแล้ว:")
            print("1. ให้ทำการ Re-verify (Regression Test) ในส่วนที่เกี่ยวข้องทั้งหมด")
            print("2. ตรวจสอบว่า Test Suggestions ที่ AI แนะนำได้รับการแก้ไขและรันผ่านแล้ว")
            print("3. ตรวจสอบ manual_test_checklist.md (ถ้ามี) อีกครั้งเพื่อให้มั่นใจว่าไม่มี regression")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"   ❌ Error during code review for {proj['name']}: {e}")


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
        # Dynamically load sibling repos
        try:
            for sibling_key in project.get("sibling_repos", []):
                # Ensure key is string
                if str(sibling_key) in PROJECTS:
                    target_repos.append(PROJECTS[str(sibling_key)])
                    print(f"   ➕ Added sibling: {PROJECTS[str(sibling_key)]['name']}")
                else:
                    print(f"   ⚠️ Sibling key '{sibling_key}' not found in PROJECTS config.")
        except Exception as e:
            print(f"⚠️ Failed to load sibling repos: {e}") 
            import traceback
            traceback.print_exc() 
    
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

    # Combine properties if multiple issues
    issues = state.active_issues
    combined_title = " & ".join([issue.title for issue in issues])
    combined_number = "-".join([str(issue.number) for issue in issues])
    combined_body = "\n\n---\n\n".join([f"### Issue #{issue.number}\n{issue.body or ''}" for issue in issues])

    # Create temporary state
    analyst_state = {
        "task": combined_title,
        "issue_data": {
            "title": combined_title,
            "number": combined_number,
            "body": combined_body
        },
        "target_dir": project["path"]
    }

    print("\n🧠 Invoking Analyst Agent...")
    result = analyst_agent(analyst_state)
    
    if result.get("analysis_file"):
        print(f"\n✨ Analysis complete! Document saved to: {result['analysis_file']}")
    else:
        print("\n⚠️ Analysis failed or produced no output.")

def action_switch_project(state: LumaState) -> str:
    """Switch to different project"""
    # Collect all sibling repo keys to hide from menu
    sibling_keys = set()
    for key, proj in PROJECTS.items():
        for sib_key in proj.get("sibling_repos", []):
            sibling_keys.add(str(sib_key))
    
    print("\n🔀 Select Project:")
    for key, proj in PROJECTS.items():
        if key in sibling_keys:
            continue  # Hide sibling repos from menu
        print(f"  [{key}] {proj['name']}")
    
    print("  [+] Add New Project")
    
    choice = input("\nSelect: ").strip()
    
    if choice == "+":
        return _add_new_project(state)
        
    if choice in PROJECTS:
        return choice
    
    return None

def _add_new_project(state: LumaState) -> str:
    """Interactively add a new project and save it to config"""
    print("\n✨ Add New Project")
    print("=================")
    
    name = input("Project Name: ").strip()
    if not name:
        print("❌ Project Name is required.")
        return None
        
    path = input("Absolute Path to Project: ").strip()
    if not path or not os.path.isabs(path):
        print("❌ Absolute Path is required.")
        return None
        
    repo = input("GitHub Repo (e.g. oatrice/Akasa) [Optional]: ").strip()
    kanban_number_str = input("GitHub Project Board Number [Optional]: ").strip()
    
    # Generate a unique key
    import time
    new_key = str(int(time.time()))
    
    new_project = {
        "name": name,
        "path": path,
        "repo": repo if repo else "",
        "kanban_number": int(kanban_number_str) if kanban_number_str.isdigit() else 1,
        "kanban_id": "" # Cannot easily infer this via CLI right now
    }
    
    # 1. Add to current session runtime
    PROJECTS[new_key] = new_project
    
    # 2. Save to global config
    from luma_core.config import GLOBAL_CONFIG_FILE
    import json
    
    try:
        current_config = {}
        if os.path.exists(GLOBAL_CONFIG_FILE):
             with open(GLOBAL_CONFIG_FILE, "r") as f:
                  current_config = json.load(f)
        
        if "custom_projects" not in current_config:
            current_config["custom_projects"] = {}
            
        current_config["custom_projects"][new_key] = new_project
        
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            json.dump(current_config, f, indent=2)
            
        print(f"\n✅ Project '{name}' added successfully!")
        return new_key
    except Exception as e:
        print(f"\n❌ Failed to save project: {e}")
        return None

def action_settings():
    """Settings menu to configure LLM Provider and Agent CLI"""
    import os
    import json
    from luma_core.config import GLOBAL_CONFIG_FILE, LLM_PROVIDER, AGENT_CLI
    
    print("\n⚙️  Settings")
    print("==========")
    
    # Load current config
    current_config = {}
    if os.path.exists(GLOBAL_CONFIG_FILE):
        try:
            with open(GLOBAL_CONFIG_FILE, "r") as f:
                current_config = json.load(f)
        except Exception:
            pass
            
    current_llm = current_config.get("LLM_PROVIDER", LLM_PROVIDER)
    current_cli = current_config.get("AGENT_CLI", AGENT_CLI)
    
    while True:
        print(f"\nCurrent Configuration:")
        print(f"  [1] LLM Provider: {current_llm}")
        print(f"  [2] Agent CLI:    {current_cli}")
        print(f"  [3] 🔙 Back")
        
        choice = input("\nSelect setting to change [1-3]: ").strip()
        
        if choice == "1":
            print("\nSelect LLM Provider:")
            print("  [1] gemini (API)")
            print("  [2] openrouter")
            print("  [3] gemini_cli (Local CLI)")
            
            p_choice = input("Select [1-3]: ").strip()
            if p_choice == "1":
                current_llm = "gemini"
            elif p_choice == "2":
                current_llm = "openrouter"
            elif p_choice == "3":
                current_llm = "gemini_cli"
                
        elif choice == "2":
            print("\nSelect Agent CLI:")
            print("  [1] gemini_cli")
            print("  [2] opencode")
            
            c_choice = input("Select [1-2]: ").strip()
            if c_choice == "1":
                current_cli = "gemini_cli"
            elif c_choice == "2":
                current_cli = "opencode"
                
        elif choice == "3" or choice == "":
            break
        else:
            print("❌ Invalid option")
            
    # Save back to config
    current_config["LLM_PROVIDER"] = current_llm
    current_config["AGENT_CLI"] = current_cli
    
    try:
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            json.dump(current_config, f, indent=2)
            
        # Hot-reload config module so get_llm picks up the change immediately
        import importlib
        import luma_core.config
        importlib.reload(luma_core.config)
            
        print("\n✅ Settings saved!")
    except Exception as e:
        print(f"\n❌ Failed to save settings: {e}")



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
    
    # Combine properties if multiple issues
    issues = state.active_issues
    combined_title = " & ".join([issue.title for issue in issues])
    combined_number = "-".join([str(issue.number) for issue in issues])
    combined_body = "\n\n---\n\n".join([f"### Issue #{issue.number}\n{issue.body or ''}" for issue in issues])
    
    first_issue = issues[0]
    
    # Create state for SBE agent
    sbe_state = {
        "task": combined_title,
        "issue_data": {
            "title": combined_title,
            "number": combined_number,
            "body": combined_body,
            "url": getattr(first_issue, "html_url", ""),
            "repository": getattr(first_issue, "repository", "")
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

    # Combine properties if multiple issues
    issues = state.active_issues
    combined_title = " & ".join([issue.title for issue in issues])
    combined_number = "-".join([str(issue.number) for issue in issues])
    combined_body = "\n\n---\n\n".join([f"### Issue #{issue.number}\n{issue.body or ''}" for issue in issues])
    
    # Use the first issue's URL and repository for simplicity
    first_issue = issues[0]

    # Create State
    spec_state = {
        "task": combined_title,
        "issue_data": {
            "title": combined_title,
            "number": combined_number,
            "body": combined_body,
            "url": getattr(first_issue, "html_url", ""),
            "repository": getattr(first_issue, "repository", "")
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

    # Verify via gh cli
    print(f"🔍 Verifying Issue #{issue_id} via GitHub CLI...")
    import subprocess
    try:
        gh_res = subprocess.run(
            ["gh", "issue", "view", issue_id, "--json", "title,state", "-t", "{{.title}} ({{.state}})"],
            cwd=project["path"], capture_output=True, text=True
        )
        if gh_res.returncode == 0:
            print(f"   ✅ Found: {gh_res.stdout.strip()}")
        else:
            print(f"   ⚠️ Could not verify issue via gh: {gh_res.stderr.strip()}")
    except Exception as e:
        print(f"   ⚠️ GitHub CLI check failed: {e}")

    # Find the block
    found_idx = -1
    for i, line in enumerate(lines):
        if f"**#{issue_id}" in line or f"#{issue_id} " in line or f"[#{issue_id}]" in line:
            found_idx = i
            break

    if found_idx == -1:
        print(f"❌ Issue #{issue_id} not found in Roadmap.")
        return

    print(f"✅ Found issue at line {found_idx+1}: {lines[found_idx].strip()}")
    
    # Check if this is a table row (starts with |)
    is_table_row = lines[found_idx].strip().startswith("|")
    
    status_idx = -1
    indent = "    - " # Default fallback indent
    
    if is_table_row:
        status_idx = found_idx
        # In a markdown table, status is likely the last or second to last column
        print(f"   Current row: {lines[found_idx].strip()}")
    else:
        # Look for status line in next few lines (list format)
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
    print("  [1] ✅ Done / Complete")
    print("  [2] 🟢 Ready")
    print("  [3] 🟡 In Progress / Todo")
    print("  [4] 🔴 Blocked")
    
    status_choice = input("Select [1-4]: ").strip()
    
    new_status_line = ""
    new_table_status = ""
    
    if status_choice == "1":
        # Version prompt for 'Done'
        version = input("Enter Version (e.g. v1.8.0, Enter to skip): ").strip()
        note = input("Enter Completion Note (Enter to skip): ").strip()
        
        status_prefix = "✅ Complete" if is_table_row else "✅ **Done**"
        
        if version and note:
            new_table_status = f"{status_prefix} ({version}) - {note}"
        elif version:
            new_table_status = f"{status_prefix} ({version})"
        elif note:
            new_table_status = f"{status_prefix} - {note}"
        else:
            new_table_status = f"{status_prefix}"
            
        new_status_line = f"{indent}✅ **Done**" + (f" ({version})" if version else "") + (f" - {note}" if note else "")
            
    elif status_choice == "2":
        new_table_status = "🟢 Ready"
        new_status_line = f"{indent}**Status:** 🟢 **Ready**"
    elif status_choice == "3":
        new_table_status = "🔲 Todo" if is_table_row else "🟡 In Progress"
        new_status_line = f"{indent}**Status:** 🟡 **In Progress**"
    elif status_choice == "4":
        new_table_status = "🔴 Blocked"
        new_status_line = f"{indent}**Status:** 🔴 **Blocked**"
    else:
        print("❌ Invalid selection")
        return

    # Update logic
    if is_table_row:
        # Split by | and update the last column (or second to last if line ends with |)
        parts = lines[found_idx].split("|")
        
        # Determine the status column index
        # Usually format is: | Priority | ID | Title | Status |
        # So it's typically the 4th column (index 4) if it starts and ends with |
        status_col_index = -2 if lines[found_idx].rstrip().endswith("|") else -1
        
        if len(parts) >= 3: # To handle basic | ID | Title | Status |
            parts[status_col_index] = f" {new_table_status} "
            lines[found_idx] = "|".join(parts)
            if not lines[found_idx].endswith("\n"):
                lines[found_idx] += "\n"
        else:
             print("⚠️  Row does not seem to have the standard formatting.")
    elif status_idx != -1:
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

    combined_number = "-".join([str(i.number) for i in state.active_issues])
    print(f"\n📦 Archiving artifacts for Issue #{combined_number}...")

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
            if d.startswith(f"{combined_number}_") or f"issue-{combined_number}" in d:
                feature_dir = os.path.join(features_root, d)
                break
    
    # 3. Create new if needed
    if not feature_dir:
        combined_title = " & ".join([i.title for i in state.active_issues])
        slug = combined_title.lower().replace(" ", "-").replace("[", "").replace("]", "")[:50]
        dirname = f"{combined_number}_{slug}"
        feature_dir = os.path.join(features_root, dirname)
        os.makedirs(feature_dir, exist_ok=True)
        print(f"   📂 Created feature dir: {dirname}")
    else:
        print(f"   📂 Target: {os.path.basename(feature_dir)}")

    # Only archive locally generated planning/documentation artifacts.
    # AI Brain artifacts (task.md, walkthrough.md, etc.) are handled by ai_brain_sync.py
    # and placed in the ai_brain/ subdirectory.
    search_dirs = [project["path"]]
    
    artifacts = [
        "analysis.md", "spec.md", "plan.md", "sbe.md", "code_review.md" 
    ]
    # Also support platform specific variations like plan_android.md
    
    import shutil
    
    moved_count = 0
    
    for sdir in search_dirs:
        if not os.path.exists(sdir): continue
        for filename in os.listdir(sdir):
            is_match = filename in artifacts
            if not is_match:
                if filename.startswith("plan_") and filename.endswith(".md"): is_match = True
                if filename.startswith("spec_") and filename.endswith(".md"): is_match = True
            
            if is_match:
                src = os.path.join(sdir, filename)
                dst = os.path.join(feature_dir, filename)
                try:
                    shutil.move(src, dst)
                    print(f"   ➡️  Moved {filename}")
                    moved_count += 1
                except Exception as e:
                    print(f"   ⚠️  Failed to process {filename}: {e}")

    if moved_count == 0:
        print("   (No local artifacts found to archive)")
    else:
        print(f"✅ Archived {moved_count} local files.")


def get_feature_dir(project_path: str, issue_number: str) -> str:
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
        combined_number = "-".join([str(i.number) for i in state.active_issues])
        print(f"\n🔹 Step 1: Issue #{combined_number} already selected.")

    # 2. Planning (Refine -> Spec -> Plan)
    print("\n🔹 Step 2: Planning Phase (Analyst -> Spec -> Architect)")
    
    # Check for existing artifacts
    combined_number = "-".join([str(i.number) for i in state.active_issues])
    feature_dir = get_feature_dir(project["path"], combined_number)
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
    
    rel_feat_dir = "docs/features/..."
    if feature_dir:
        try:
            rel_feat_dir = os.path.relpath(feature_dir, project.get("path", "."))
        except:
            pass
            
    print("\n   💡 [AI Prompt] Copy this text to your preferred AI:")
    print("   " + "-"*75)
    print(f"   อ่านไฟล์ทั้งหมดใน {rel_feat_dir} และไฟล์ prompt_*.txt (ระวังปัญหาติด .gitignore ให้ใช้วิธีอ่านไฟล์โดยตรง)")
    print("   มาวิเคราะห์ อธิบาย และถามคำถามเพื่อ clarify ก่อนที่จะเริ่มลงมือ implement")
    print("   " + "-"*75)
    
    cont = input("\n   Have you finished coding and verified the feature? (y/N): ").lower()
    if cont != 'y':
        print("\n⏳ Pausing workflow. Come back when you're done!")
        return

    print("\n   " + "🛠️"*5 + " MANUAL VERIFY INSTRUCTION " + "🛠️"*5)
    print("   ขอบคุณที่ยืนยัน! กรุณาตรวจสอบ Checklist สุดท้ายอีกครั้งเพื่อให้มั่นใจ:")
    print(f"   1. อ่านขั้นตอนใน {rel_feat_dir}/walkthrough.md (ถ้ามี)")
    print(f"   2. รัน Manual Test ตามไฟล์ manual_test_checklist.md (ถ้ามี)")
    print("   3. รัน Unit/Integration Test ที่เกี่ยวข้องทั้งหมด")
    print("   " + "-"*75)

    # 4. Review & Docs & Roadmap
    print("\n🔹 Step 4: Quality, Documentation & Roadmap")
    if input("   Run Code Review? (Y/n): ").lower() != 'n':
        action_code_review(state, project)
        
        print("\n   " + "🔍"*5 + " RE-VERIFY AFTER REVIEW " + "🔍"*5)
        print("   กรุณา Re-verify ฟังก์ชันต่างๆ อีกครั้งหลังจากทำการแก้ไขตาม Code Review")
        print("   เพื่อยืนยันว่าไม่มีผลกระทบ (Regression) ต่อส่วนอื่นๆ ของระบบ")
        print("   " + "-"*75)
        
    if input("   Update Docs (Changelog/README/Version)? (Y/n): ").lower() != 'n':
        action_update_docs(state, project)

    if input("   Update Roadmap? (Y/n): ").lower() != 'n':
        action_update_roadmap(state, project)

    # 5. Archive Artifacts
    print("\n🔹 Step 5: Archive Artifacts")
    if input("   Move artifacts to docs/features/...? (Y/n): ").lower() != 'n':
        action_archive_artifacts(state, project)

    # 6. Create PR (With Auto Option)
    print("\n🔹 Step 6: Create Pull Request")
    
    # Check for "Yes to All" preference
    auto_approve_pr = False
    choice = input("   Create PRs? [y] Yes (confirm each), [a] Yes to All (auto), [n] No: ").strip().lower()
    
    if choice == 'a':
        action_create_pr(state, project, auto_approve=True)
    elif choice == 'y' or choice == '':
        action_create_pr(state, project, auto_approve=False)
        
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
            
    print("\n🎉 Workflow Completed! You can now select the next issue.")


def action_run_multi_agent_coding(state: LumaState, project: dict):
    """Run sequential AI coding agents for different stacks."""
    print("\n🤖 Multi-Agent Auto-Coding Swarm")
    print("==================================")
    print("Which agents would you like to compile?")
    print("  [1] All (Frontend + Backend + Android + iOS)")
    print("  [2] Frontend (Web)")
    print("  [3] Backend (Go/Python)")
    print("  [4] Android (Kotlin)")
    print("  [5] iOS (Swift)")
    print("  [6] 📝 Generate Prompts Only (for manual use)")
    print("  [0] Skip (Manual Coding)")
    
    choice = input("\nSelect [0-6]: ").strip()
    
    if choice == "0":
        return

    # Define agents config
    agents_to_run = []
    generate_prompts_only = False
    
    if choice == "1":
        agents_to_run = ["frontend", "backend", "android", "ios"]
    elif choice == "2":
        agents_to_run = ["frontend"]
    elif choice == "3":
        agents_to_run = ["backend"]
    elif choice == "4":
        agents_to_run = ["android"]
    elif choice == "5":
        agents_to_run = ["ios"]
    elif choice == "6":
        agents_to_run = ["frontend", "backend", "android", "ios"]
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
        
        combined_number = "-".join([str(i.number) for i in state.active_issues])
        combined_title = " & ".join([i.title for i in state.active_issues])
        sub_task = f"Implement {agent_type} components for Issue #{combined_number}: {combined_title}"
        source_paths = []
        
        tech_stack = ""
        if agent_type == "frontend":
            tech_stack = "React/Vue/Web technologies. Focus on UI implementation."
            if os.path.exists(os.path.join(project["path"], "Web")):
                source_paths.append("Web/package.json")
        elif agent_type == "backend":
            tech_stack = "Go. Implement API endpoints and business logic."
            if os.path.exists(os.path.join(project["path"], "backend")):
                source_paths.append("backend/go.mod")
        elif agent_type == "android":
            tech_stack = "Kotlin/Jetpack Compose. Implement Mobile UI and ViewModel. You can use ./gradlew directly."
            if os.path.exists(os.path.join(project["path"], "view")): # Legacy or Luma specific
                 pass
        elif agent_type == "ios":
            tech_stack = "Swift/SwiftUI. Implement iOS UI + MVVM. Use XCTest."
            # Ideally look for xcodeproj but we don't have a specific file to append yet
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
                 combined_number = "-".join([str(i.number) for i in state.active_issues])
                 for d in os.listdir(features_root):
                     if d.startswith(f"{combined_number}_") or f"issue-{combined_number}" in d:
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
             combined_number = "-".join([str(i.number) for i in state.active_issues])
             combined_title = " & ".join([i.title for i in state.active_issues])
             combined_body = "\n\n---\n\n".join([f"### Issue #{issue.number}\n{issue.body or ''}" for issue in state.active_issues])

             android_specific_instruction = ""
             if agent_type == "android":
                 android_specific_instruction = "\n**⚠️ สำคัญมากๆ สำหรับ Android:**\nหากคุณต้องการ Test หรือ Build ระบบ **ห้ามรันผ่าน Command Line `gradlew` เด็ดขาด** ให้คุณรันการ Build และ Test ผ่าน UI ของช่องทาง path ของ **Android Studio** เท่านั้น\n"

             prompt_content = f"""# Role: Senior {agent_type.capitalize()} Developer
# Task: {sub_task}
{android_specific_instruction}
**💡 คำสั่งสำหรับ AI Assistant (Cursor/Claude/etc):**
ให้อ่านไฟล์ทั้งหมดใน `docs/features/{os.path.basename(feature_dir) if feature_dir else "[feature_dir]"}` และไฟล์ `prompt_{agent_type}.txt` นี้ (ระวังปัญหาติด .gitignore ให้ใช้วิธีอ่านไฟล์โดยตรง) 
มาวิเคราะห์ อธิบาย และถามคำถามเพื่อ clarify ก่อนที่จะเริ่มลงมือ implement

Please write the code for the following requirements.

## Context
Project: {project['name']}
Issue: #{combined_number} {combined_title}
Body:
{combined_body or "No details provided."}

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



