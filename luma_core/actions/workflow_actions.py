import luma_core.ui as ui
from luma_core.ui import safe_input
from luma_core.state_manager import LumaState, WorkflowPhase, transition_to
from luma_core.preflight_checker import PreflightChecker
from luma_core.config import PROJECTS
import luma_core.usage_tracker as usage_tracker
from luma_core.agents.publisher import publisher_agent
from .utils import (
    get_status_workflow,
    fetch_kanban_cards,
    _get_selectable_cards,
    _status_key,
    _confirm_pending_doc_updates_before_pr,
    get_feature_dir,
    auto_fill_issue_metrics,
    check_planning_artifacts
)
from .admin_actions import action_archive_artifacts
from .issue_actions import action_select_issue
from .plan_actions import action_generate_plan, action_generate_spec, action_refine_issue
from .quality_actions import action_code_review, action_update_docs, action_update_roadmap, sync_roadmap_for_closed_issues
import sys
import os

def action_create_pr(state: LumaState, project: dict, auto_approve: bool = False, target_repos: list = None):
    """Create Pull Request with Pre-flight Checks"""
    # Allow if Coding OR (PR_Pending to sync other repos) OR Preflight (Retry)
    allowed_phases = [
        WorkflowPhase.CODING,
        WorkflowPhase.REVIEWING,
        WorkflowPhase.PR_PENDING,
        WorkflowPhase.PREFLIGHT,
    ]
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

        override = (
            "y"
            if auto_approve
            else ui.safe_input("⚠️ Force create PR anyways? (y/N): ").strip().lower()
        )
        if override != "y":
            # Revert to CODING
            transition_to(state, WorkflowPhase.CODING)
            return

    if not _confirm_pending_doc_updates_before_pr(state, project, auto_approve=auto_approve):
        transition_to(state, WorkflowPhase.CODING)
        return

    # 3. Ask for Mode if not auto-approved already
    if not auto_approve:
        print("\n🤖 PR Creation Mode:")
        mode = (
            ui.safe_input(
                "   [y] Interactive (Confirm each)\n   [a] Auto-Approve ALL\n   [n] Cancel / Back to Coding\n   Select: "
            )
            .strip()
            .lower()
        )

        if mode == "n":
            print("❌ Operation cancelled.")
            transition_to(state, WorkflowPhase.CODING)
            return

        if mode == "a":
            print("   ✅ Auto-Approve enabled for all repos.")
            auto_approve = True

    # Determine target repos (Multi-Repo Support)
    if target_repos is not None:
        target_projects = target_repos
        if len(target_projects) > 1:
            print("   Mode: Multi-Repo (JarWise) - Using explicitly selected repos...")
    else:
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
    feature_dir = state.context.get("last_feature_dir")
    screenshots_to_sync = []
    
    created_prs = []

    if feature_dir:
        sc_dir = os.path.join(feature_dir, "screenshots")
        if os.path.exists(sc_dir):
            files = [
                f
                for f in os.listdir(sc_dir)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
            ]
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
            br_res = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=proj["path"],
                capture_output=True,
                text=True,
            )
            curr_br = br_res.stdout.strip()
            if curr_br != state.active_branch:
                print(
                    f"   ⏩ Skipping {proj['name']} (Branch mismatch: {curr_br} != {state.active_branch})"
                )
                continue

            # Check for commits ahead of main
            commits_res = subprocess.run(
                ["git", "rev-list", "--count", "origin/main..HEAD"],
                cwd=proj["path"],
                capture_output=True,
                text=True,
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
                print(
                    f"   ⏩ Skipping {proj['name']} (PR already exists: {existing['html_url']})"
                )
                continue

        # --- SYNC SCREENSHOTS TO TARGET REPO ---
        repo_screenshot_section = ""
        ai_brain_section = ""
        if screenshots_to_sync:
            try:
                # 1. Create docs/screenshots/issue-N/ in target repo
                issue_id = state.active_issue.number
                target_sc_dir = os.path.join(
                    proj["path"], "docs", "screenshots", f"issue-{issue_id}"
                )
                os.makedirs(target_sc_dir, exist_ok=True)

                repo_screenshot_section = "\n\n## 📸 Screenshots\n"

                import shutil

                git_add_files = []

                for src_path in screenshots_to_sync:
                    filename = os.path.basename(src_path)
                    dst_path = os.path.join(target_sc_dir, filename)

                    if not os.path.exists(dst_path) or os.path.getsize(
                        src_path
                    ) != os.path.getsize(dst_path):
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

                        # We only encode the path part if needed, but simple f-string is usually fine for strict filenames
                        repo_screenshot_section += f"![{filename}]({raw_url})\n"
                    else:
                        # Fallback if repo info missing
                        repo_screenshot_section += f"![{filename}]({rel_path})\n"

                # 2. Git Add the screenshots
                if git_add_files:
                    subprocess.run(
                        ["git", "add"] + git_add_files, cwd=proj["path"], check=False
                    )
                    subprocess.run(
                        ["git", "commit", "-m", "docs: add screenshots"],
                        cwd=proj["path"],
                        check=False,
                        capture_output=True,
                    )

            except Exception as e:
                print(f"   ⚠️ Failed to sync screenshots: {e}")

        # --- SYNC AI BRAIN ARTIFACTS ---
        try:
            from luma_core.ai_brain_sync import AntigravityBrain

            print("   🔄 Syncing AI Agent Brain Artifacts...")
            brain_session = state.context.get("selected_brain_session")
            synced_docs = AntigravityBrain.sync_to_repo(
                proj["path"], state.active_issue.number, session_path=brain_session
            )

            if synced_docs:
                subprocess.run(
                    ["git", "add"] + synced_docs, cwd=proj["path"], check=False
                )
                subprocess.run(
                    ["git", "commit", "-m", "docs: sync AI brain artifacts"],
                    cwd=proj["path"],
                    check=False,
                    capture_output=True,
                )
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
            confirm = (
                ui.safe_input(f"   ✨ Create PR for {proj['name']}? (Y/n): ").strip().lower()
            )
            if confirm == "n":
                continue

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
            combined_body = (
                (primary_issue.body or "")
                + issues_section
                + repo_screenshot_section
                + ai_brain_section
            )
            pr_title = f"{primary_issue.title} (#{', #'.join(str(i.number) for i in state.active_issues)})"
        else:
            closes_line = f"Closes #{primary_issue.number}"
            combined_body = (
                (primary_issue.body or "") + repo_screenshot_section + ai_brain_section
            )
            pr_title = primary_issue.title

        # Add closes line at the end
        combined_body += f"\n\n{closes_line}"

        pub_state = {
            "task": pr_title,
            "issue_data": {
                "title": pr_title,
                "number": primary_issue.number,
                "body": combined_body,
                "url": getattr(
                    primary_issue,
                    "html_url",
                    f"https://github.com/{project['repo']}/issues/{primary_issue.number}",
                ),
            },
            "repo": proj["repo"],
            "issue_source_repo": project["repo"],
            "target_dir": proj["path"],
            "test_suggestions": "",
            "auto_approve": auto_approve,
        }

        print(f"   📤 Invoking Publisher Agent for {proj['name']}...")
        result = publisher_agent(pub_state)
        pr_url = result.get("pr_url")

        if pr_url:
            print(f"   ✅ PR Created: {pr_url}")
            created_prs.append((proj["name"], pr_url))
            # Update state with the created PR url
            if proj == project:
                ok, msg = transition_to(state, WorkflowPhase.PR_PENDING, pr_url=pr_url)
                if ok:
                    print("   🔄 State updated to PR_PENDING")
        else:
            print("   ⚠️ Publisher finished but no known PR URL.")

    if created_prs:
        print("\n📋 PR Summary:")
        for name, url in created_prs:
            print(f"  ✅ {name:<20} → {url}")

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

    # 1.5. Metrics Check
    from luma_core.issue_metrics import get_issue_metrics
    issues_missing_metrics = []
    
    for issue in state.active_issues:
        metrics = get_issue_metrics(project["path"], project.get("repo", ""), issue.number)
        has_metrics = metrics is not None and metrics.estimate_points is not None
        if not has_metrics:
            issues_missing_metrics.append(issue)
            
    if issues_missing_metrics:
        ans = ui.safe_input("\nการประเมินชั่วโมงการทำงาน (Estimate Points) ยังไม่สมบูรณ์ ต้องการให้ AI ช่วยประเมินและเติมให้ไหม? (y/n): ").strip().lower()
        if ans == 'y':
            auto_fill_issue_metrics(state, project, issues_missing_metrics)


    # 2. Planning (Refine -> Spec -> Plan)
    print("\n🔹 Step 2: Planning Phase (Analyst -> Spec -> Architect)")

    target_planning_repos = [project]
    if project.get("sibling_repos"):
        print("\n   📂 Select repos for Planning:")
        print(f"   [1] ✅ {project['name']} (current)")
        
        selectable_repos = [project]
        # We need to access global PROJECTS dictionary if it's available, otherwise skip sibling lookup
        from luma_core.actions import PROJECTS
        for sib_id in project["sibling_repos"]:
            if sib_id in PROJECTS:
                selectable_repos.append(PROJECTS[sib_id])
                
        for i, sib in enumerate(selectable_repos[1:], start=2):
            print(f"   [{i}] ☐  {sib['name']}")
            
        repo_choice = safe_input("   Select (e.g. 1,2,3 or 'a' for all, Enter for current only): ").lower()
        if repo_choice in ['a', 'all']:
            target_planning_repos = selectable_repos
        elif repo_choice:
            selected_indices = [idx.strip() for idx in repo_choice.split(",") if idx.strip().isdigit()]
            new_targets = []
            for idx_str in selected_indices:
                idx = int(idx_str) - 1
                if 0 <= idx < len(selectable_repos):
                    new_targets.append(selectable_repos[idx])
            if new_targets:
                target_planning_repos = new_targets

    # Save target planning repos to context so AI agents can use it to build context
    state.context["target_planning_repos"] = target_planning_repos
    
    # We only run the actual document generation in the root project
    planning_proj = project
    
    # Check for existing artifacts
    combined_number = "-".join([str(i.number) for i in state.active_issues])
    feature_dir = get_feature_dir(planning_proj["path"], combined_number)
    # Also check context if just created
    if not feature_dir and state.context.get("last_feature_dir"):
        feature_dir = state.context.get("last_feature_dir")

    artifacts_status = check_planning_artifacts(feature_dir) if feature_dir else {"analysis": False, "spec": False, "plan": False}
    has_any_artifact = any(artifacts_status.values())

    skip_planning = (state.checklist.get("step_planning", False) or state.phase in [
        WorkflowPhase.REVIEWING, WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING
    ]) and has_any_artifact
    
    if skip_planning:
        print("\n🔹 Step 2: Planning Phase (Skipped - already completed)")
    else:
        if len(target_planning_repos) > 1:
            print(f"\n   ────────────── Planning for {planning_proj['name']} (including {len(target_planning_repos)-1} siblings) ──────────────")
        else:
            print(f"\n   ────────────── Planning for {planning_proj['name']} ──────────────")

        # Save to context immediately so action_generate_plan will use it
        if feature_dir:
            state.context["last_feature_dir"] = feature_dir

        has_any = has_any_artifact

        run_planning = True
        planning_mode = "all"  # all, missing, selective
        selected_steps = ["analysis", "spec", "plan"]

        if has_any:
            print(
                f"\n   📝 Found existing Planning Docs in {os.path.basename(feature_dir)}:"
            )
            for k, exists in artifacts_status.items():
                icon = "[x]" if exists else "[ ]"
                print(f"      {icon} {k.capitalize()} ({k}.md)")

            print("\n   Select action:")
            print("   [1] Run All (Overwrite)")
            print("   [2] Generate Missing Only")
            print("   [3] Select Specific Documents")
            print("   [0] Skip Planning Phase")

            p_choice = ui.safe_input("\n   Select [0-3]: ").strip()

            if p_choice == "0":
                run_planning = False
            elif p_choice == "2":
                planning_mode = "missing"
            elif p_choice == "3":
                planning_mode = "selective"
                # Ask for selection
                selected_steps = []
                if ui.safe_input("      - Run Analysis? (y/N): ").lower() == "y":
                    selected_steps.append("analysis")
                if ui.safe_input("      - Run Spec? (y/N): ").lower() == "y":
                    selected_steps.append("spec")
                if ui.safe_input("      - Run Plan? (y/N): ").lower() == "y":
                    selected_steps.append("plan")
                if not selected_steps:
                    print("      (No steps selected, skipping planning)")
                    run_planning = False
            else:
                # Default to Run All
                planning_mode = "all"

        else:
            # Standard flow
            if ui.safe_input("   Run Planning Phase? (Y/n): ").lower() == "n":
                run_planning = False

        if run_planning:
            # Execute based on mode/selection

            # 1. Analyst
            should_run_analyst = False
            if planning_mode == "all":
                should_run_analyst = True
            elif planning_mode == "missing" and not artifacts_status["analysis"]:
                should_run_analyst = True
            elif planning_mode == "selective" and "analysis" in selected_steps:
                should_run_analyst = True

            if should_run_analyst:
                usage_tracker.set_sub_action("Auto:Planning/Analyst")
                action_refine_issue(state, planning_proj)
                # Update feature dir after analyst runs (it might have created it)
                feature_dir = get_feature_dir(planning_proj["path"], state.active_issues[0].number if state.active_issues else combined_number)
                state.context["last_feature_dir"] = feature_dir

            # 2. Spec
            should_run_spec = False
            if planning_mode == "all":
                should_run_spec = True
            elif planning_mode == "missing" and not artifacts_status["spec"]:
                should_run_spec = True
            elif planning_mode == "selective" and "spec" in selected_steps:
                should_run_spec = True

            if should_run_spec:
                usage_tracker.set_sub_action("Auto:Planning/Spec")
                action_generate_spec(state, planning_proj)
                # Update feature dir
                if state.context.get("last_feature_dir"):
                    feature_dir = state.context.get("last_feature_dir")

            # 3. Plan
            should_run_plan = False
            if planning_mode == "all":
                should_run_plan = True
            elif planning_mode == "missing" and not artifacts_status["plan"]:
                should_run_plan = True
            elif planning_mode == "selective" and "plan" in selected_steps:
                should_run_plan = True

            if should_run_plan:
                # Ensure feature_dir is in context so action_generate_plan doesn't ask again
                if feature_dir:
                    state.context["last_feature_dir"] = feature_dir
                usage_tracker.set_sub_action("Auto:Planning/Plan")
                action_generate_plan(state, planning_proj)

        state.checklist["step_planning"] = True
        from luma_core.state_manager import save_state
        save_state(state, project["path"])

    # 3. Coding (User)
    skip_coding = (state.checklist.get("step_coding", False) or state.phase in [
        WorkflowPhase.REVIEWING, WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING
    ]) and has_any_artifact
    
    if skip_coding:
        print("\n🔹 Step 3: Coding Phase (Skipped - already completed)")
    else:
        # If we are in a later phase but artifacts are missing, we should probably be in CODING
        if state.phase in [WorkflowPhase.REVIEWING, WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING] and not has_any_artifact:
            print(f"⚠️ Current phase is {state.phase.value} but no planning artifacts found.")
            print("   Reverting to CODING phase to ensure proper implementation.")
            transition_to(state, WorkflowPhase.CODING)
            from luma_core.state_manager import save_state
            save_state(state, project["path"])

        print("\n🔹 Step 3: Coding Phase")
        print("   🤖 AI Assist + 👤 Human Coding")
    
        # Offer Multi-Agent Swarm
        usage_tracker.set_sub_action("Auto:Coding/Multi-Agent")
        action_run_multi_agent_coding(state, project)
    
        print("   - Use your IDE to implement the feature.")
        print("   - Run 'Luma' > 'Code Review' periodically.")
    
        if feature_dir:
            try:
                os.path.relpath(feature_dir, project.get("path", "."))
            except Exception:
                pass
    
        cont = ui.safe_input(
            "\n   Have you finished coding and verified the feature? (y/N): "
        ).lower()
        if cont != "y":
            print("\n⏳ Pausing workflow. Come back when you're done!")
            return
    
        state.checklist["step_coding"] = True
        if state.phase == WorkflowPhase.CODING:
            transition_to(state, WorkflowPhase.REVIEWING)
        from luma_core.state_manager import save_state
        save_state(state, project["path"])
    
        print("\n   " + "🛠️" * 5 + " ต้อง Manual verify อย่างไรบ้าง " + "🛠️" * 5)

    # 4. Review & Docs & Roadmap
    print("\n🔹 Step 4: Quality, Documentation & Roadmap")
    if not state.checklist.get("step_review", False) and state.phase not in [WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING]:
        if ui.safe_input("   Run Code Review? (Y/n): ").lower() != "n":
            usage_tracker.set_sub_action("Auto:Quality/CodeReview")
            action_code_review(state, project)
    
            print("\n   " + "🔍" * 5 + " RE-VERIFY AFTER REVIEW " + "🔍" * 5)
            print("   กรุณา Re-verify ฟังก์ชันต่างๆ อีกครั้งหลังจากทำการแก้ไขตาม Code Review")
            print("   เพื่อยืนยันว่าไม่มีผลกระทบ (Regression) ต่อส่วนอื่นๆ ของระบบ")
            print("   " + "-" * 75)
        
        state.checklist["step_review"] = True
        from luma_core.state_manager import save_state
        save_state(state, project["path"])

    if not state.checklist.get("step_docs", False) and state.phase not in [WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING]:
        if ui.safe_input("   Update Docs (Changelog/README/Version)? (Y/n): ").lower() != "n":
            usage_tracker.set_sub_action("Auto:Quality/Docs")
            action_update_docs(state, project)
        state.checklist["step_docs"] = True
        from luma_core.state_manager import save_state
        save_state(state, project["path"])

    if not state.checklist.get("step_roadmap", False) and state.phase not in [WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING]:
        if ui.safe_input("   Update Roadmap? (Y/n): ").lower() != "n":
            usage_tracker.set_sub_action("Auto:Quality/Roadmap")
            # Auto-sync closed issues first
            if state.active_issues:
                issue_nums = [i.number for i in state.active_issues]
                synced = sync_roadmap_for_closed_issues(project, issue_nums)
                if synced:
                    print(f"\n   🔄 Auto-synced {synced} closed issue(s) → Roadmap.md")
            action_update_roadmap(state, project)
        state.checklist["step_roadmap"] = True
        from luma_core.state_manager import save_state
        save_state(state, project["path"])

    # 5. Archive Artifacts
    print("\n🔹 Step 5: Archive Artifacts")
    if not state.checklist.get("step_archive", False) and state.phase not in [WorkflowPhase.PREFLIGHT, WorkflowPhase.PR_PENDING]:
        user_input = ui.safe_input("   Move artifacts to docs/features/...? (Y/n): ").lower()
        if user_input != "n":
            action_archive_artifacts(state, project)
        state.checklist["step_archive"] = True
        from luma_core.state_manager import save_state
        save_state(state, project["path"])

    # 6. Create PR (With Auto Option)
    print("\n🔹 Step 6: Create Pull Request")

    # Check for "Yes to All" preference
    choice = (
        ui.safe_input("   Create PRs? [y] Yes (confirm each), [a] Yes to All (auto), [n] No: ")
        .strip()
        .lower()
    )

    if choice == "a":
        usage_tracker.set_sub_action("Auto:PR/Auto-Approve")
        action_create_pr(state, project, auto_approve=True, target_repos=target_planning_repos)
    elif choice == "y" or choice == "":
        usage_tracker.set_sub_action("Auto:PR/Interactive")
        action_create_pr(state, project, auto_approve=False, target_repos=target_planning_repos)

    # Poll for Merge?
    if state.phase == WorkflowPhase.PR_PENDING and state.pr_url:
        print(f"\n⏳ PR Created: {state.pr_url}")

        # 7. CI Check
        print("\n🔹 Step 7: Check CI Status")
        if ui.safe_input("   Check CI status in background? (Y/n): ").strip().lower() != "n":
            import subprocess
            import sys
            
            parts = state.pr_url.split("/")
            if len(parts) >= 7 and "github.com" in state.pr_url:
                ci_repo = f"{parts[-4]}/{parts[-3]}"
                ci_pr_num = parts[-1]
                
                print("   ✅ ส่งคำสั่งตรวจสอบ CI ไปทำงานเป็น Background แล้ว")
                print("      (เมื่อพบว่า CI สำเร็จหรือผิดพลาด ระบบจะแจ้งเตือนผ่าน Telegram)")
                
                luma_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "luma_core.ci_checker",
                        ci_pr_num,
                        ci_repo,
                        project.get("name", "Unknown"),
                        state.pr_url
                    ],
                    cwd=luma_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            else:
                print("   ⚠️ Could not parse PR URL to check CI.")

        print("\n   Please merge the PR on GitHub.")
        ui.safe_input("   Press Enter AFTER you have merged the PR...")

        # Use the refresh check logic from main loop or just assume
        from luma_core.github_project import check_pr_merged

        pr_status = check_pr_merged(state.pr_url)
        if pr_status["merged"]:
            print("✅ PR Merged confirmed!")

    # Clear sub_action at the end of the auto workflow so future usage is clean
    usage_tracker.set_sub_action(None)

    # 8. Send Summary to Telegram
    try:
        from luma_core.metrics_summarizer import (
            summarize_usage_stats,
            summarize_issue_metrics,
            format_summary_message,
        )
        from luma_core.notifier import notify_task_complete as _notify
        from luma_core.issue_metrics import prefill_metrics_from_roadmap, sync_github_metrics_for_project

        print("\n   🔄 Auto-syncing issue metrics from Roadmap...")
        prefill_result = prefill_metrics_from_roadmap(
            project["path"],
            project.get("name"),
            project.get("repo"),
        )
        if prefill_result["created"] or prefill_result["updated"]:
            print(f"   🗺️  Synced (created {prefill_result['created']}, updated {prefill_result['updated']})")
            
        print("\n   🐙 Auto-syncing issue metrics from GitHub...")
        gh_sync_result = sync_github_metrics_for_project(
            project["path"],
            project.get("name"),
            project.get("repo"),
        )
        if gh_sync_result["updated"] > 0:
            print(f"   📊 Synced {gh_sync_result['updated']} records from GH.")

        usage_summary = summarize_usage_stats(
            usage_tracker.get_log_path(), project, usage_tracker._SESSION_ID,
            branch=state.active_branch
        )
        # Fallback: If current session has 0 calls (e.g. session restart), 
        # get project stats from the branch (now prioritized) or last 24 hours.
        if usage_summary.get("total_calls", 0) == 0:
            usage_summary = summarize_usage_stats(
                usage_tracker.get_log_path(), project, session_id=None, 
                since_hours=24, branch=state.active_branch
            )
        metrics_path = os.path.join(project["path"], ".luma_metrics.json")
        metrics_summary = summarize_issue_metrics(metrics_path)
        summary_msg = format_summary_message(usage_summary, metrics_summary)
        _notify(
            project=project.get("name", "Unknown"),
            task="Workflow Summary",
            status="success",
            message=summary_msg,
        )
        print("\n📊 Summary sent to Telegram!")
    except Exception as e:
        print(f"\n⚠️ Could not send summary: {e}")

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

    choice = ui.safe_input("\nSelect [0-6]: ").strip()

    if choice == "0":
        feature_dir = None
        if state.context.get("last_feature_dir"):
            feature_dir = state.context.get("last_feature_dir")

        if not feature_dir:
            features_root = os.path.join(project["path"], "docs", "features")
            if os.path.exists(features_root):
                combined_number = "-".join([str(i.number) for i in state.active_issues])
                for d in os.listdir(features_root):
                    if (
                        d.startswith(f"{combined_number}_")
                        or f"issue-{combined_number}" in d
                    ):
                        feature_dir = os.path.join(features_root, d)
                        break

        feature_label = os.path.basename(feature_dir) if feature_dir else "[feature_dir]"
        prompt_instruction_brief = (
            f"ให้อ่านไฟล์ทั้งหมดใน `docs/features/{feature_label}` "
            "(ระวังปัญหาติด .gitignore ให้ใช้วิธีอ่านไฟล์โดยตรง)\n"
            "มาวิเคราะห์ อธิบาย และถามคำถามเพื่อ clarify ก่อนที่จะเริ่มลงมือ implement"
        )
        print("   💡 Prompt Instruction:")
        print(f"   {prompt_instruction_brief}")
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
            if os.path.exists(
                os.path.join(project["path"], "view")
            ):  # Legacy or Luma specific
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
                    if (
                        d.startswith(f"{combined_number}_")
                        or f"issue-{combined_number}" in d
                    ):
                        feature_dir = os.path.join(features_root, d)
                        break

        if feature_dir and os.path.exists(feature_dir):
            print(f"   📂 Loading context from: {os.path.basename(feature_dir)}...")
            docs_to_read = [
                "analysis.md",
                "plan.md",
                "spec.md",
                "implementation_plan.md",
                f"plan_{agent_type}.md",
            ]

            for doc in docs_to_read:
                doc_path = os.path.join(feature_dir, doc)
                if os.path.exists(doc_path):
                    try:
                        with open(doc_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            artifact_context += f"\n\n## Reference: {doc}\n{content[:5000]}\n(truncated if too long)\n"
                    except Exception:
                        pass
        else:
            print("   ⚠️ No feature directory found. Using generic context.")

        feature_label = os.path.basename(feature_dir) if feature_dir else "[feature_dir]"
        prompt_instruction = (
            f"ให้อ่านไฟล์ทั้งหมดใน `docs/features/{feature_label}` "
            f"และไฟล์ `prompt_{agent_type}.txt` นี้ (ระวังปัญหาติด .gitignore ให้ใช้วิธีอ่านไฟล์โดยตรง)\n"
            "มาวิเคราะห์ อธิบาย และถามคำถามเพื่อ clarify ก่อนที่จะเริ่มลงมือ implement"
        )
        prompt_instruction_brief = (
            f"ให้อ่านไฟล์ทั้งหมดใน `docs/features/{feature_label}` "
            "(ระวังปัญหาติด .gitignore ให้ใช้วิธีอ่านไฟล์โดยตรง)\n"
            "มาวิเคราะห์ อธิบาย และถามคำถามเพื่อ clarify ก่อนที่จะเริ่มลงมือ implement"
        )

        if generate_prompts_only:
            # Just generate the prompt text file
            prompt_file = os.path.join(project["path"], f"prompt_{agent_type}.txt")
            combined_number = "-".join([str(i.number) for i in state.active_issues])
            combined_title = " & ".join([i.title for i in state.active_issues])
            combined_body = "\n\n---\n\n".join(
                [
                    f"### Issue #{issue.number}\n{issue.body or ''}"
                    for issue in state.active_issues
                ]
            )

            android_specific_instruction = ""
            if agent_type == "android":
                android_specific_instruction = "\n**⚠️ สำคัญมากๆ สำหรับ Android:**\nหากคุณต้องการ Test หรือ Build ระบบ **ห้ามรันผ่าน Command Line `gradlew` เด็ดขาด** ให้คุณรันการ Build และ Test ผ่าน UI ของช่องทาง path ของ **Android Studio** เท่านั้น\n"

            prompt_content = f"""# Role: Senior {agent_type.capitalize()} Developer
# Task: {sub_task}
{android_specific_instruction}
**💡 คำสั่งสำหรับ AI Assistant (Cursor/Claude/etc):**
{prompt_instruction}

Please write the code for the following requirements.

## Context
Project: {project["name"]}
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
            print("   💡 Prompt Instruction:")
            print(f"   {prompt_instruction}")
            continue

        # Create scoped state
        agent_state = {
            "task": sub_task,
            "source_files": source_paths,
            "iterations": 0,
            "test_errors": "",
            "skip_coder": False,
        }

        print("   💡 Prompt Instruction:")
        print(f"   {prompt_instruction_brief}")

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
                patch_file = os.path.join(
                    project["path"], f"agent_{agent_type}_patch.xml"
                )
                with open(patch_file, "w") as f:
                    f.write(result.get("code_content", ""))
                print(
                    f"   💾 Saved proposed changes to: {os.path.basename(patch_file)}"
                )
            else:
                print("   🤷 Agent decided not to change any code.")

        except Exception as e:
            print(f"   ⚠️ Agent Error: {e}")

    if generate_prompts_only:
        print(
            "\n✅ Prompts generated! You can now use 'prompt_*.txt' files with your preferred AI."
        )
    else:
        print(
            "\n✅ Multi-Agent session finished. Review the 'agent_*_patch.xml' files."
        )
