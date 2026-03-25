import re
import subprocess
from .utils import *

def action_code_review(state: LumaState, project: dict):
    """Run local code review agent"""
    print("\n🧐 Local Code Reviewer")

    # Determine target repos (Multi-Repo Support)
    # ── ใช้ค่าจาก Step 2 ถ้ามี (ไม่ถามซ้ำ) ───────────────────────────────────
    preselected_repos = state.context.get("target_planning_repos")
    if preselected_repos:
        target_projects = preselected_repos
        repo_names = ", ".join(p["name"] for p in target_projects)
        print(f"\n   ♻️  Using repositories selected in Step 2: {repo_names}")
    else:
        # ── Fallback: ถาม (กรณีเรียกแยกจาก Guided Workflow) ─────────────────
        potential_projects = [project]
        if project.get("type") == "monorepo_root" and project.get("sibling_repos"):
            try:
                for sibling_key in project.get("sibling_repos", []):
                    if str(sibling_key) in PROJECTS:
                        potential_projects.append(PROJECTS[str(sibling_key)])
            except Exception:
                pass

        target_projects = []
        if len(potential_projects) > 1:
            print("\n   Select repositories to review (e.g., 1, 2 or 'all'):")
            for i, proj in enumerate(potential_projects, 1):
                print(f"   [{i}] {proj['name']} ({proj.get('type', 'unknown')})")

            choice = input("\n   Select [all]: ").strip().lower()
            if not choice or choice == "all":
                target_projects = potential_projects
            else:
                try:
                    indices = [int(i.strip()) - 1 for i in choice.split(",") if i.strip()]
                    for idx in indices:
                        if 0 <= idx < len(potential_projects):
                            target_projects.append(potential_projects[idx])
                except ValueError:
                    print("   ⚠️ Invalid input. Reviewing all repositories.")
                    target_projects = potential_projects
        else:
            target_projects = potential_projects

    if not target_projects:
        print("   ❌ No repositories selected.")
        return

    for proj in target_projects:
        print(f"\n🚀 Reviewing {proj['name']}...")
        target_dir = proj["path"]

        # 1. Get changed files
        try:
            import subprocess

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
                    if rel_path.endswith((".png", ".jpg", ".ico", ".pdf", ".jar")):
                        continue
                    try:
                        # 1. Try to get diff against origin/main (includes local commits)
                        diff_cmd = ["git", "diff", "origin/main", "--", rel_path]
                        diff_res = subprocess.run(
                            diff_cmd, cwd=target_dir, capture_output=True, text=True
                        )

                        if diff_res.returncode == 0 and diff_res.stdout.strip():
                            changes[rel_path] = diff_res.stdout.strip()
                        else:
                            # 2. If no origin/main diff, try just checking uncommitted changes
                            diff_cmd = ["git", "diff", "HEAD", "--", rel_path]
                            diff_res = subprocess.run(
                                diff_cmd, cwd=target_dir, capture_output=True, text=True
                            )

                            if diff_res.returncode == 0 and diff_res.stdout.strip():
                                changes[rel_path] = diff_res.stdout.strip()
                            else:
                                # 3. Fallback to reading the full file if it's untracked or we can't get diff
                                with open(full_path, "r", encoding="utf-8") as f:
                                    changes[rel_path] = f.read()
                    except Exception:
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
                "skip_coder": False,
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
                    f.write(
                        f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    f.write(f"**Files Reviewed:** {list(changes.keys())}\n\n")

                    if result.get("code_content"):
                        f.write("## 📝 Reviewer Feedback\n\n")
                        f.write(result["code_content"] + "\n\n")

                    if result.get("test_suggestions"):
                        f.write("## 🧪 Test Suggestions\n\n")
                        f.write(result["test_suggestions"] + "\n\n")
                print(f"\n   ✅ Review Report saved to: {report_path}")

                # Append the raw prompt to draft_code_review.md if available
                if result.get("prompt_used"):
                    draft_path = os.path.join(target_dir, "draft_code_review.md")
                    try:
                        with open(draft_path, "a", encoding="utf-8") as f:
                            f.write(
                                "\n\n---\n\n## 🤖 Prompt Used by Reviewer\n\n```text\n"
                            )
                            f.write(result["prompt_used"])
                            f.write("\n```\n")
                        print(f"   ✅ Appended review prompt to: {draft_path}")
                    except Exception as e:
                        print(f"   ⚠️ Could not append prompt to {draft_path}: {e}")

            except Exception as e:
                print(f"\n   ⚠️ Failed to save report: {e}")

            print(f"\n   ✅ Review Complete for {proj['name']}.")

            # Print the prompt for the user to copy and paste to the AI assistant
            print("\n" + "=" * 60)
            print("💡 COPY THIS PROMPT FOR THE AI ASSISTANT:")
            print("=" * 60)
            prompt_text = _build_code_review_followup_prompt(
                multi_repo=len(target_projects) > 1
            )
            print(prompt_text)
            print("=" * 60)

            prompt_path = os.path.join(target_dir, "code_review_prompt.txt")
            try:
                with open(prompt_path, "w", encoding="utf-8") as f:
                    f.write(prompt_text)
                print(f"\n   📝 Prompt saved to: {prompt_path}")
            except Exception as e:
                print(f"\n   ⚠️ Failed to save prompt: {e}")

            print("\n" + "🧪" * 10 + " ต้อง RE-MANUAL VERIFY อย่างไร " + "🧪" * 10)

        except Exception as e:
            print(f"   ❌ Error during code review for {proj['name']}: {e}")

def action_update_docs(state: LumaState, project: dict, skip_confirm: bool = False):
    """Update documentation (Changelog, Version, README)"""
    print("\n📝 Documentation Update")
    print(f"   Project: {project['name']}")

    # 1. Determine Scope (Single vs Multi-Repo)
    # Check for explicit multi-repo flag in project config
    is_multi_repo = project.get("type") == "monorepo_root"
    target_repos = [project]

    if is_multi_repo:
        print("   Mode: Multi-Repo (JarWise)")
        # Check if we already selected repos during planning phase
        target_planning_repos = state.context.get("target_planning_repos", [])
        if target_planning_repos:
            print("   ✅ Using selected repositories from Planning Phase")
            target_repos = target_planning_repos
        else:
            # Dynamically load sibling repos
            all_candidates = [project]
            try:
                for sibling_key in project.get("sibling_repos", []):
                    # Ensure key is string
                    if str(sibling_key) in PROJECTS:
                        all_candidates.append(PROJECTS[str(sibling_key)])
                    else:
                        print(f"   ⚠️ Sibling key '{sibling_key}' not found in PROJECTS config.")
            except Exception as e:
                print(f"⚠️ Failed to load sibling repos: {e}")
                import traceback
    
                traceback.print_exc()
                
            if not skip_confirm:
                print("\n   📦 Select projects to update docs:")
                for idx, cand in enumerate(all_candidates, 1):
                    print(f"      [{idx}] {cand['name']}")
                print("      [a] All (Default)")
    
                selected = input("\n   Select indices (e.g., 1,3) or 'a' for all: ").strip().lower()
                if selected and selected != 'a':
                    target_repos = []
                    for s in selected.split(','):
                        s = s.strip()
                        if s.isdigit():
                            idx = int(s) - 1
                            if 0 <= idx < len(all_candidates):
                                target_repos.append(all_candidates[idx])
                    if not target_repos:
                        print("   ⚠️ No valid projects selected. Defaulting to 'All'.")
                        target_repos = all_candidates
                else:
                    target_repos = all_candidates
            else:
                target_repos = all_candidates

    print("\n🚀 Ready to update:")
    for repo in target_repos:
        print(f"   - {repo['name']}")

    if not skip_confirm:
        confirm = input("\nProceed with docs update? (y/N): ").lower()
        if confirm != "y":
            return []

    # 2. Run Update
    print("\n⏳ Updating docs (AI-powered)...")
    results = update_multi_repo_docs(target_repos, docs_agent_func=None)

    # 3. Summary
    print("\n" + "=" * 40)
    print("📊 Docs Update Summary:")
    print("=" * 40)

    for r in results:
        status = "✅" if r.get("success") else "⏩"
        msg = (
            ", ".join(r.get("files_updated", []))
            if r.get("success")
            else r.get("error")
        )
        print(f"   {status} {r['name']}: {msg}")

    print("\n✅ Done.")
    refresh_pending_doc_updates(state, project)
    return results


def sync_roadmap_for_closed_issues(project: dict, issue_numbers: list) -> int:
    """
    Auto-detect which issues from the list are CLOSED on GitHub, then silently
    update their status in Roadmap.md to ✅ Complete.
    Returns the number of issues that were synced.
    """
    if not issue_numbers:
        return 0

    roadmap_paths = [
        os.path.join(project["path"], "docs", "ROADMAP.md"),
        os.path.join(project["path"], "ROADMAP.md"),
    ]
    roadmap_path = next((p for p in roadmap_paths if os.path.exists(p)), None)
    if not roadmap_path:
        return 0

    try:
        with open(roadmap_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return 0

    repo_name = project.get("repo")
    synced = 0

    for issue_id in issue_numbers:
        issue_id_str = str(issue_id)
        # Check gh cli if issue is closed
        gh_args = ["issue", "view", issue_id_str, "--json", "number,title,state,url"]
        if repo_name:
            gh_args.extend(["--repo", repo_name])

        output = run_gh_command(gh_args, timeout=10)
        if not output:
            continue
        try:
            data = json.loads(output)
        except Exception:
            continue

        if data.get("state", "").upper() != "CLOSED":
            continue

        # Find issue in roadmap
        found_idx = -1
        for i, line in enumerate(lines):
            if f"#{issue_id_str} " in line or f"[#{issue_id_str}]" in line or f"**#{issue_id_str}" in line:
                found_idx = i
                break

        if found_idx == -1:
            # Issue not in roadmap — append it
            section_title = "## Synced From GitHub"
            insert_at = len(lines)
            for idx, line in enumerate(lines):
                if line.strip().lower() == section_title.lower():
                    insert_at = idx + 1
                    break
            else:
                if lines and lines[-1].strip():
                    lines.append("\n")
                lines.append(section_title + "\n")
                lines.append("\n")
                insert_at = len(lines)

            issue_url = data.get("url", "")
            title = (data.get("title") or "").replace("\n", " ").strip() or "Untitled"
            block = [f"### Issue #{issue_id_str} - {title}\n"]
            if issue_url:
                block.append(f"- **GitHub:** [#{issue_id_str}]({issue_url})\n")
            block.append(f"- **State:** {data.get('state', 'CLOSED')}\n")
            block.append(f"- ✅ **Done**\n")
            block.append("\n")
            lines[insert_at:insert_at] = block
            print(f"   📌 Issue #{issue_id_str} (CLOSED) → appended to Roadmap as ✅ Done")
            synced += 1
            continue

        # Update existing row/line
        is_table_row = lines[found_idx].strip().startswith("|")
        if is_table_row:
            parts = lines[found_idx].split("|")
            status_col = -2 if lines[found_idx].rstrip().endswith("|") else -1
            if len(parts) >= 3:
                parts[status_col] = " ✅ Complete "
                lines[found_idx] = "|".join(parts)
                if not lines[found_idx].endswith("\n"):
                    lines[found_idx] += "\n"
                print(f"   ✅ Issue #{issue_id_str} (CLOSED) → Roadmap table updated to ✅ Complete")
                synced += 1
        else:
            # Look for status line nearby
            for i in range(found_idx + 1, min(found_idx + 6, len(lines))):
                stripped = lines[i].strip()
                if "Status:" in stripped or "**Done**" in stripped or "**In Progress**" in stripped or "**Blocked**" in stripped:
                    indent = "    - " if lines[i].startswith("    -") else "- "
                    lines[i] = f"{indent}✅ **Done**\n"
                    print(f"   ✅ Issue #{issue_id_str} (CLOSED) → Roadmap status updated to ✅ Done")
                    synced += 1
                    break

    if synced > 0:
        try:
            with open(roadmap_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            print(f"   ⚠️ Could not write roadmap: {e}")
            return 0

    return synced


def sync_roadmap_for_new_issues(project: dict, cards: list) -> int:
    """
    Append OPEN Kanban cards that are NOT yet referenced in Roadmap.md.
    Returns the number of issues appended.
    """
    if not cards:
        return 0

    roadmap_paths = [
        os.path.join(project["path"], "docs", "ROADMAP.md"),
        os.path.join(project["path"], "ROADMAP.md"),
    ]
    roadmap_path = next((p for p in roadmap_paths if os.path.exists(p)), None)
    if not roadmap_path:
        return 0

    try:
        with open(roadmap_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines(keepends=True)
    except Exception:
        return 0

    # Status emoji mapping (Kanban status → display label)
    STATUS_ICON = {
        "ready": "🟢 **Ready**",
        "in progress": "🟡 **In Progress**",
        "blocked": "🔴 **Blocked**",
        "backlog": "🔵 **Backlog**",
    }

    def _status_label(status: str) -> str:
        return STATUS_ICON.get(status.lower().strip(), f"🔵 **{status}**")

    synced = 0
    new_blocks: list = []

    for card in cards:
        issue_id_str = str(card.issue_number)
        # Check if issue is already referenced anywhere in roadmap
        if (f"#{issue_id_str} " in content
                or f"[#{issue_id_str}]" in content
                or f"**#{issue_id_str}" in content
                or f"#{issue_id_str}\n" in content):
            continue

        title = (card.title or "Untitled").replace("\n", " ").strip()
        url = getattr(card, "url", "") or ""
        label = _status_label(getattr(card, "status", "Ready"))

        block = [f"### Issue #{issue_id_str} - {title}\n"]
        if url:
            block.append(f"- **GitHub:** [#{issue_id_str}]({url})\n")
        block.append(f"- **Status:** {label}\n")
        block.append("\n")
        new_blocks.extend(block)
        print(f"   📌 Issue #{issue_id_str} ({card.status}) → appended to Roadmap as new")
        synced += 1

    if synced == 0:
        return 0

    # Find or create "## Synced From GitHub" section
    section_title = "## Synced From GitHub"
    insert_at = len(lines)
    for idx, line in enumerate(lines):
        if line.strip().lower() == section_title.lower():
            insert_at = idx + 1
            break
    else:
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append(section_title + "\n")
        lines.append("\n")
        insert_at = len(lines)

    lines[insert_at:insert_at] = new_blocks

    try:
        with open(roadmap_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"   ⚠️ Could not write roadmap: {e}")
        return 0

    return synced


def action_update_roadmap(state: LumaState, project: dict):  # PATCHED: multi-issue support
    """Update ROADMAP.md status for one or more issues (supports comma-separated input)."""
    print(f"\n🗺️  Updating Roadmap for {project['name']}...")

    # Locate ROADMAP.md
    roadmap_paths = [
        os.path.join(project["path"], "docs", "ROADMAP.md"),
        os.path.join(project["path"], "ROADMAP.md"),
    ]
    roadmap_path = next((p for p in roadmap_paths if os.path.exists(p)), None)

    if not roadmap_path:
        print("❌ Roadmap not found in docs/ or root.")
        return

    try:
        with open(roadmap_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Failed to read roadmap: {e}")
        return

    # ── Input: รองรับ single ("65"), comma-separated ("33, 34"), หรือพิมพ์ "new" เพื่อสร้างใหม่ ──
    issue_input = input("Enter Issue # to update, or 'new' to create one: ").strip()
    if not issue_input:
        return

    raw_ids = issue_input.replace(",", " ").split()
    issue_ids = [x.strip().replace("#", "") for x in raw_ids if x.strip().replace("#", "").isdigit()]

    if issue_input.lower() == "new":
        print("\n➕ Creating new GitHub Issue...")
        title = input("   Issue Title: ").strip()
        if not title:
            print("❌ Title cannot be empty.")
            return

        body = input("   Issue Body (optional): ").strip()
        
        gh_args = ["issue", "create", "--title", title, "--body", body]
        repo_name = project.get("repo")
        if repo_name:
            gh_args.extend(["--repo", repo_name])
            
        print(f"   🚀 Running: gh {' '.join(gh_args)}")
        try:
            gh_res = subprocess.run(
                ["gh"] + gh_args,
                cwd=project["path"],
                capture_output=True,
                text=True,
            )
            if gh_res.returncode == 0:
                output = gh_res.stdout.strip()
                print(f"   ✅ Created: {output}")
                
                # extracting issue URL from gh output (usually returns the issue URL)
                url = output.splitlines()[-1].strip()
                match = re.search(r"/issues/(\d+)", url)
                if match:
                    new_issue_id = match.group(1)
                    issue_ids.append(new_issue_id)
                else:
                    print("   ⚠️ Could not parse issue ID from output. Will not update Roadmap.")
            else:
                print(f"   ❌ GitHub CLI error: {gh_res.stderr.strip()}")
                return
        except Exception as e:
            print(f"   ❌ GitHub CLI execution failed: {e}")
            return
            
    if not issue_ids:
        print(f"❌ No valid issue numbers found to update.")
        return

    def _fetch_issue_from_github(issue_id: str):
        gh_args = ["issue", "view", issue_id, "--json", "number,title,state,url"]
        repo_name = project.get("repo")
        if repo_name:
            gh_args.extend(["--repo", repo_name])

        output = run_gh_command(gh_args, timeout=15)
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError as e:
                print(f"   ⚠️ Failed to parse gh output for issue #{issue_id}: {e}")

        import subprocess

        try:
            fallback_cmd = ["gh", "issue", "view", issue_id, "--json", "number,title,state,url"]
            if repo_name:
                fallback_cmd.extend(["--repo", repo_name])

            gh_res = subprocess.run(
                fallback_cmd,
                cwd=project["path"],
                capture_output=True,
                text=True,
            )
            if gh_res.returncode == 0:
                return json.loads(gh_res.stdout)

            error_text = gh_res.stderr.strip()
            if error_text:
                print(f"   ⚠️ Could not verify issue via gh: {error_text}")
        except Exception as e:
            print(f"   ⚠️ GitHub CLI check failed: {e}")

        return None

    verified_issues = {}

    # ── Verify each issue via gh CLI and keep metadata for sync ──────────────
    for issue_id in issue_ids:
        print(f"🔍 Verifying Issue #{issue_id} via GitHub CLI...")
        issue_data = _fetch_issue_from_github(issue_id)
        if issue_data:
            verified_issues[issue_id] = issue_data
            issue_number = issue_data.get("number", issue_id)
            title = (issue_data.get("title") or "").replace("\n", " ").strip() or "(Untitled issue)"
            state_name = issue_data.get("state", "UNKNOWN")
            print(f"   ✅ Found: #{issue_number} {title} ({state_name})")
        else:
            print(f"   ⚠️ Could not verify issue #{issue_id}. Existing Roadmap entry can still be updated.")

    # ── Helper: find issue in roadmap and return metadata ────────────────────
    def _find_issue(issue_id, lines):
        found_idx = -1
        for i, line in enumerate(lines):
            if (
                f"**#{issue_id}" in line
                or f"#{issue_id} " in line
                or f"[#{issue_id}]" in line
            ):
                found_idx = i
                break

        if found_idx == -1:
            return found_idx, False, -1, "    - "

        is_table_row = lines[found_idx].strip().startswith("|")
        status_idx = -1
        indent = "    - "

        if is_table_row:
            status_idx = found_idx
            print(f"   Current row: {lines[found_idx].strip()}")
        else:
            for i in range(found_idx + 1, min(found_idx + 6, len(lines))):
                stripped = lines[i].strip()
                if (
                    stripped.startswith("- **Status:**")
                    or stripped.startswith("- ✅ **Done**")
                    or stripped.startswith("- 🟡 **In Progress**")
                    or "Status:" in stripped
                    or "✅ **Done**" in stripped
                ):
                    status_idx = i
                    print(f"   Current: {stripped}")
                    if lines[i].startswith("    -"):
                        indent = "    - "
                    elif lines[i].startswith("\t-"):
                        indent = "\t- "
                    break

        return found_idx, is_table_row, status_idx, indent

    def _ensure_synced_issue_section(lines):
        section_title = "## Synced From GitHub"

        for idx, line in enumerate(lines):
            if line.strip().lower() == section_title.lower():
                for next_idx in range(idx + 1, len(lines)):
                    if lines[next_idx].startswith("## "):
                        return next_idx
                return len(lines)

        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append(section_title + "\n")
        lines.append("\n")
        return len(lines)

    def _build_missing_issue_block(issue_data, status_line):
        issue_number = issue_data.get("number", "")
        title = (issue_data.get("title") or "").replace("\n", " ").strip() or "(Untitled issue)"
        issue_url = (issue_data.get("url") or "").strip()
        issue_state = (issue_data.get("state") or "UNKNOWN").strip()

        block = [f"### Issue #{issue_number} - {title}\n"]
        if issue_url:
            block.append(f"- **GitHub:** [#{issue_number}]({issue_url})\n")
        block.append(f"- **State:** {issue_state}\n")
        block.append(status_line.strip() + "\n")
        block.append("\n")
        return block

    # ── Find all requested issues ─────────────────────────────────────────────
    found_issues = []
    missing_issues = []
    for issue_id in issue_ids:
        found_idx, is_table_row, status_idx, indent = _find_issue(issue_id, lines)
        if found_idx == -1:
            if issue_id in verified_issues:
                print(f"⚠️  Issue #{issue_id} not found in Roadmap. Will append it from GitHub metadata.")
                missing_issues.append(issue_id)
            else:
                print(f"⚠️  Issue #{issue_id} not found in Roadmap and could not be verified via gh. Skipping.")
        else:
            print(f"✅ Found issue #{issue_id} at line {found_idx + 1}: {lines[found_idx].strip()}")
            found_issues.append((issue_id, found_idx, is_table_row, status_idx, indent))

    if not found_issues and not missing_issues:
        print("❌ No requested issues could be updated in the Roadmap.")
        return

    # ── Ask for status ONCE — applies to all found issues ────────────────────
    issues_to_update = [x[0] for x in found_issues] + missing_issues
    issue_list = ", ".join(f"#{issue_id}" for issue_id in issues_to_update)
    print(f"\nSelecting status for {len(issues_to_update)} issue(s): {issue_list}")
    # Check if all verified issues being updated are CLOSED
    all_closed = False
    if verified_issues:
        states = [
            verified_issues[i].get("state", "OPEN").upper() 
            for i in issues_to_update if i in verified_issues
        ]
        if states and all(s == "CLOSED" for s in states):
            all_closed = True

    if all_closed:
        print("\n💡 GitHub state is CLOSED, auto-selecting ✅ Done (press Enter to confirm, or choose manually)")
        prompt_str = "Select [1-4] (Enter for '1'): "
    else:
        print("\nSelect new status:")
        prompt_str = "Select [1-4]: "

    print("  [1] ✅ Done / Complete")
    print("  [2] 🟢 Ready")
    print("  [3] 🟡 In Progress / Todo")
    print("  [4] 🔴 Blocked")

    status_choice = input(prompt_str).strip()
    if all_closed and status_choice == "":
        status_choice = "1"
    if status_choice not in ("1", "2", "3", "4"):
        print("❌ Invalid selection")
        return

    version = ""
    note = ""
    if status_choice == "1":
        version = input("Enter Version (e.g. v1.8.0, Enter to skip): ").strip()
        note = input("Enter Completion Note (Enter to skip): ").strip()

    def _build_status_strings(is_table_row, indent):
        if status_choice == "1":
            status_prefix = "✅ Complete" if is_table_row else "✅ **Done**"
            if version and note:
                new_table_status = f"{status_prefix} ({version}) - {note}"
            elif version:
                new_table_status = f"{status_prefix} ({version})"
            elif note:
                new_table_status = f"{status_prefix} - {note}"
            else:
                new_table_status = f"{status_prefix}"
            new_status_line = (
                f"{indent}✅ **Done**"
                + (f" ({version})" if version else "")
                + (f" - {note}" if note else "")
            )
        elif status_choice == "2":
            new_table_status = "🟢 Ready"
            new_status_line = f"{indent}**Status:** 🟢 **Ready**"
        elif status_choice == "3":
            new_table_status = "🔲 Todo" if is_table_row else "🟡 In Progress"
            new_status_line = f"{indent}**Status:** 🟡 **In Progress**"
        else:
            new_table_status = "🔴 Blocked"
            new_status_line = f"{indent}**Status:** 🔴 **Blocked**"
        return new_table_status, new_status_line

    # ── Apply updates in reverse line order to preserve indices ──────────────
    for issue_id, found_idx, is_table_row, status_idx, indent in sorted(
        found_issues, key=lambda x: x[1], reverse=True
    ):
        new_table_status, new_status_line = _build_status_strings(is_table_row, indent)

        if is_table_row:
            parts = lines[found_idx].split("|")
            status_col_index = -2 if lines[found_idx].rstrip().endswith("|") else -1
            if len(parts) >= 3:
                parts[status_col_index] = f" {new_table_status} "
                lines[found_idx] = "|".join(parts)
                if not lines[found_idx].endswith("\n"):
                    lines[found_idx] += "\n"
            else:
                print(f"⚠️  Issue #{issue_id}: row does not have standard table formatting.")
        elif status_idx != -1:
            lines[status_idx] = new_status_line + "\n"
        else:
            print(f"⚠️  Issue #{issue_id}: status line not found nearby. Appending.")
            lines.insert(found_idx + 2, new_status_line + "\n")

        print(f"   ✅ Issue #{issue_id} → updated.")

    added_issue_count = 0
    if missing_issues:
        insert_at = _ensure_synced_issue_section(lines)
        new_issue_lines = []
        for issue_id in missing_issues:
            issue_data = verified_issues.get(issue_id)
            if not issue_data:
                continue
            _, new_status_line = _build_status_strings(False, "- ")
            new_issue_lines.extend(_build_missing_issue_block(issue_data, new_status_line))
            added_issue_count += 1
            print(f"   ✅ Issue #{issue_id} → added to Roadmap from GitHub.")
        if new_issue_lines:
            lines[insert_at:insert_at] = new_issue_lines

    # ── Write back once ───────────────────────────────────────────────────────
    try:
        with open(roadmap_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        updated_count = len(found_issues) + added_issue_count
        print(f"\n✅ Roadmap updated successfully! ({updated_count} issue(s))")
    except Exception as e:
        print(f"❌ Failed to write roadmap: {e}")
