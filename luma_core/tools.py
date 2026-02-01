import os
import subprocess
import json
import re
from typing import Optional
from langchain_core.messages import HumanMessage
from .llm import get_llm
from .config import TARGET_DIR as DEFAULT_TARGET_DIR


def suggest_version_from_git(target_dir: str = DEFAULT_TARGET_DIR) -> Optional[str]:
    """
    Analyzes git commit messages and diff to suggest the next version.
    Uses AI to determine if it should be a PATCH, MINOR, or MAJOR bump.
    Returns the suggested version string or None if unable to determine.
    """
    project_root = os.path.dirname(target_dir)
    
    # 1. Get current version from android-server/build.gradle or CHANGELOG.md
    current_version = None
    
    # Try to get version from bump_version.sh output or CHANGELOG
    try:
        changelog_path = os.path.join(project_root, "android-server/CHANGELOG.md")
        version_cmd = ["grep", "-oE", r"[0-9]+\.[0-9]+\.[0-9]+", changelog_path]
        version_res = subprocess.run(version_cmd, cwd=project_root, capture_output=True, text=True)
        if version_res.returncode == 0 and version_res.stdout.strip():
            current_version = version_res.stdout.strip().split("\n")[0]
    except Exception:
        pass
    
    if not current_version:
        print("⚠️ Could not determine current version.")
        return None
    
    print(f"📊 Current Version: {current_version}")
    
    # 2. Get recent git commits and diff for ANDROID SERVER related files ONLY
    # Exclude client-nuxt, frontend, CSS, TypeScript, Vue files
    android_server_paths = [
        "server.go", "server_test.go", "server_parity_test.go", "tools.go",
        "android-server/",  # Core Android server code
        "cmd/",             # CLI entry points
        "go.mod", "go.sum", # Go dependencies
        "scripts/bump_version.sh",  # Version script
    ]
    
    # Get commit messages (filtered to android-server related)
    log_cmd = ["git", "log", "-n", "15", "--pretty=format:%s", "--"] + android_server_paths
    try:
        log_res = subprocess.run(log_cmd, cwd=project_root, capture_output=True, text=True)
        commit_messages = log_res.stdout[:3000]
    except Exception:
        commit_messages = ""
    
    # Get diff summary (android-server only)
    diff_cmd = ["git", "diff", "--stat", "origin/main...HEAD", "--"] + android_server_paths
    try:
        diff_res = subprocess.run(diff_cmd, cwd=project_root, capture_output=True, text=True)
        diff_stat = diff_res.stdout[:2000]
    except Exception:
        diff_stat = ""
    
    # Check if there are any android-server related changes
    if not commit_messages.strip() and not diff_stat.strip():
        print("ℹ️ No android-server related changes detected.")
        return None
    
    # 3. Ask AI to determine bump type
    llm = get_llm(temperature=0.3)
    
    prompt = f"""
    Analyze the following git history for ANDROID SERVER and determine the appropriate version bump.
    
    **IMPORTANT**: This is for Android Server versioning ONLY.
    
    Current Version: {current_version}
    
    Recent Commit Messages (Android Server Related):
    {commit_messages}
    
    Changed Files Summary (Android Server Related):
    {diff_stat}
    
    **CRITICAL FILTER - ONLY consider changes to:**
    - Go files (*.go) - server.go, *_test.go, tools.go
    - android-server/ directory (gomobile, .aar builds)
    - Go dependencies (go.mod, go.sum)
    - Version scripts
    
    **COMPLETELY IGNORE (do NOT factor into version bump):**
    - client-nuxt/ changes
    - Vue/TypeScript/CSS/JavaScript changes
    - Frontend UI changes
    - package.json, nuxt.config.ts, etc.
    
    Instructions:
    - Output ONLY one of: PATCH, MINOR, MAJOR, or NONE
    - PATCH: Bug fixes, small improvements, dependency updates
    - MINOR: New server features, new API endpoints, significant improvements
    - MAJOR: Breaking API changes, major architectural changes
    - NONE: If no server-related changes exist
    
    Output (only one word):
    """
    
    try:
        ai_response = llm.invoke([HumanMessage(content=prompt)]).content.strip().upper()
        
        # Parse current version
        version_parts = current_version.split(".")
        if len(version_parts) != 3:
            return None
            
        major, minor, patch = map(int, version_parts)
        
        # Calculate new version based on AI recommendation
        if "NONE" in ai_response:
            print("ℹ️ AI detected no server-related changes requiring version bump.")
            return None
        elif "MAJOR" in ai_response:
            new_version = f"{major + 1}.0.0"
        elif "MINOR" in ai_response:
            new_version = f"{major}.{minor + 1}.0"
        else:  # Default to PATCH
            new_version = f"{major}.{minor}.{patch + 1}"
        
        print(f"🤖 AI Recommendation: {ai_response} → {new_version}")
        return new_version
        
    except Exception as e:
        print(f"⚠️ AI version suggestion failed: {e}")
        return None


def update_android_version_logic(version: str, target_dir: str = DEFAULT_TARGET_DIR):
    """Orchestrates the Android Version Bump and Changelog Generation"""
    project_root = os.path.dirname(target_dir) 
    cmd = ["./scripts/bump_version.sh", version]
    
    try:
        print(f"🚀 Running: {' '.join(cmd)} in {project_root}")
        subprocess.run(cmd, cwd=project_root, check=True)
        print("✅ Version Update Complete.")
        
        # --- Auto-Fill Changelog Logic ---
        print("📝 Generating Auto-Changelog from Git History (Server Files Only)...")
        
        server_paths = [
            "server.go", "server_test.go", "server_parity_test.go", "tools.go",
            "android-server", "cmd", "scripts", "go.mod", "Makefile"
        ]
        
        # git log -p (patch) with path formatting to filter ONLY server files
        # We limit to 15 commits to avoid token overflow with diffs
        log_cmd = ["git", "log", "-n", "15", "--pretty=format:---%nCommit: %s%nDate: %cd%n", "-p", "--"] + server_paths
        
        try:
            log_res = subprocess.run(log_cmd, cwd=project_root, capture_output=True, text=True)
            commit_logs = log_res.stdout[:20000] # Safety truncation
        except Exception as e:
            print(f"⚠️ Failed to fetch git logs: {e}")
            commit_logs = ""
        
        llm = get_llm(temperature=0.5)
        changelog_prompt = f"""
        Task: Summarize these git changes for a Changelog.
        Target Audience: Android Server Users.
        
        Input Data (Commit Messages & Diffs):
        {commit_logs}
        
        Note: The input is ALREADY filtered to server-related files (Go, Scripts, Android Config).
        
        Instructions:
        1. Analyze the 'diffs' to understand the specific implementation details.
        2. Group into 'Fixed' (bug fixes) and 'Added' (new features).
        3. Return ONLY the bullet points (markdown format). 
        4. Do not include headers like '### Fixed', just the bullet points.
        5. Use technical but concise language (e.g., "Fixed nil pointer in join_game" instead of "Fixed a crash").
        6. If NO relevant changes found, return "No server changes in this release."
        
        Format Example:
        - Fixed asset bundling for embedded frontend
        - Added POST /debug/log endpoint
        """
        
        ai_summary = llm.invoke([HumanMessage(content=changelog_prompt)]).content.strip()
        
        # Read & Replace
        changelog_path = os.path.join(project_root, "android-server/CHANGELOG.md")
        if os.path.exists(changelog_path):
            with open(changelog_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            full_block_prompt = f"""
            Task: Generate the full markdown body for version {version}.
            
            Commits:
            {commit_logs}
            
            **CRITICAL FILTER**: 
            Only include changes related to:
            - Go Server (server.go, *.go files)
            - Android Server (android-server/, gomobile, .aar builds)
            - Server Tests (*_test.go)
            - Server Scripts/Workflows
            
            **EXCLUDE completely**:
            - client-nuxt/ changes
            - Vue/TypeScript/CSS changes
            - Frontend UI changes
            
            Output Format (only include sections that have items):
            ### Added
            - ...
            
            ### Fixed
            - ...
            
            If NO server-related changes exist, output:
            ### Note
            - No server-side changes in this release.
            """
            full_block = llm.invoke([HumanMessage(content=full_block_prompt)]).content.strip()
            
            placeholder_pattern = "### Fixed\n*\n\n### Added\n*\n"
            if placeholder_pattern in content:
                new_content = content.replace(placeholder_pattern, full_block + "\n")
                with open(changelog_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"✅ Auto-filled {changelog_path}")
            else:
                print("⚠️ Could not match placeholder pattern. Detailed logs preserved.")

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run bump script: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


# --- PR Helper Functions ---

def generate_branch_suggestions(target_dir: str = DEFAULT_TARGET_DIR):
    """LLM-powered branch name suggestions based on git diff"""
    print(f"📊 Analyzing local changes for suggestions in {target_dir}...")
    
    # Get diff summary
    status_res = subprocess.run(["git", "status", "--short"], cwd=target_dir, capture_output=True, text=True)
    
    try:
        diff_stat = subprocess.check_output(["git", "diff", "--stat"], cwd=target_dir, text=True).strip()
        diff_cached_stat = subprocess.check_output(["git", "diff", "--cached", "--stat"], cwd=target_dir, text=True).strip()
    except:
        diff_stat = ""
        diff_cached_stat = ""

    try:
        diff_content = subprocess.check_output(["git", "diff"], cwd=target_dir, text=True).strip()
        diff_cached_content = subprocess.check_output(["git", "diff", "--cached"], cwd=target_dir, text=True).strip()
    except:
        diff_content = ""
        diff_cached_content = ""

    full_diff = (diff_content + "\n" + diff_cached_content)[:3000]

    log_res = subprocess.run(["git", "log", "-n", "5", "--pretty=format:%s"], cwd=target_dir, capture_output=True, text=True)
    
    changes_context = f"""
    Git Status:
    {status_res.stdout}
    
    Modified Files (Stat):
    {diff_stat}
    {diff_cached_stat}

    Code Changes (Diff - Truncated):
    {full_diff}

    Recent Logs:
    {log_res.stdout}
    """
    
    try:
        llm_suggest = get_llm(temperature=0.7)
        suggest_prompt = f"""
        Based on the Code Changes above, suggest 3 suitable git branch names.
        
        Context:
        {changes_context}
        
        Instructions:
        1. Analyze the *Code Changes* to identify the specific feature or fix.
        2. Format: <type>/<concise-slug>
        3. Types: feat, fix, refactor, chore, docs, test.
        4. Slug: kebab-case, 2-4 words. Avoid generic names like 'update-file'.
        
        Return ONLY the 3 names, one per line. No numbering.
        """
        resp = llm_suggest.invoke([HumanMessage(content=suggest_prompt)])
        return [s.strip() for s in resp.content.strip().split('\n') if s.strip()]
    except Exception as e:
        print(f"⚠️ Failed to generate suggestions: {e}")
        return []


def get_user_branch_choice(target_dir: str = DEFAULT_TARGET_DIR):
    """Interactive branch selection with AI suggestions"""
    suggestions = generate_branch_suggestions(target_dir)
    
    if suggestions:
        print("\n💡 AI Suggestions:")
        for idx, s in enumerate(suggestions):
            print(f"   [{idx+1}] {s}")
        print("   [0] Custom Name")
        
        sel = input("👉 Select [1-3] or Enter custom name: ").strip()
        if sel in ["1", "2", "3"] and int(sel) <= len(suggestions):
            return suggestions[int(sel)-1]
        return sel
    else:
        return input("👉 Enter new branch name: ").strip()


def load_or_generate_pr_content(current_branch: str, repo: str, target_dir: str = DEFAULT_TARGET_DIR):
    """Load draft or generate PR title/body via LLM"""
    draft_file = os.path.join(target_dir, ".pr_draft.json")
    title = ""
    body = ""
    
    # Check for existing DRAFT or PREVIEW
    preview_file = os.path.join(target_dir, "PR_PREVIEW.md")
    
    if os.path.exists(preview_file) or os.path.exists(draft_file):
        print("📄 Found existing PR Draft/Preview!")
        if input("Reuse saved draft? (y/N): ").lower() == 'y':
            try:
                # Prefer Markdown Preview if exists (as user likely edited it)
                if os.path.exists(preview_file):
                    with open(preview_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    # Parse Title from first line if formatted as "# TITLE: ..."
                    lines = content.split('\n')
                    if lines[0].startswith("# TITLE:"):
                        title = lines[0].replace("# TITLE:", "").strip()
                        body = "\n".join(lines[1:]).strip()
                    elif lines[0].startswith("# "):
                         # Fallback if user just wrote a header
                         title = lines[0].replace("# ", "").strip()
                         body = "\n".join(lines[1:]).strip()
                    else:
                        # Fallback
                        title = ""
                        body = content
                    
                    print(f"📖 Loaded from {preview_file}")
                
                # Fallback to JSON if no Markdown or parsing failed/incomplete (though unlikely to fallback if file exists)
                elif os.path.exists(draft_file):
                    with open(draft_file, "r") as f:
                        data = json.load(f)
                        title = data.get("title", "")
                        body = data.get("body", "")
                    print(f"📖 Loaded from {draft_file}")

            except Exception as e:
                print(f"⚠️ Failed to load draft: {e}")

    if not title or not body:
        # Check for Template
        possible_templates = [
            os.path.join(target_dir, ".github", "pull_request_template.md"),
            os.path.join(os.path.dirname(os.path.abspath(target_dir)), ".github", "pull_request_template.md"),
            os.path.join(target_dir, "PR_TEMPLATE.md"),
            os.path.join(target_dir, "docs", "pull_request_template.md") # Added for JarWise structure if needed
        ]
        template_path = next((p for p in possible_templates if os.path.exists(p)), None)
        
        template_content = ""
        if template_path:
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
                
        # Generate Content with Enhanced Context
        print("📊 Analyzing changes by commit for detailed description...")
        
        llm = get_llm(purpose="code")
        
        # 1. Get List of Commits in this PR
        commits_cmd = ["git", "log", "--reverse", "--pretty=format:%H|%s", "origin/main..HEAD"]
        try:
            commits_res = subprocess.run(commits_cmd, cwd=target_dir, capture_output=True, text=True)
            commit_lines = commits_res.stdout.strip().split('\n')
        except Exception as e:
            print(f"⚠️ Failed to get commits: {e}")
            commit_lines = []
            
        # 2. Iterate and get diff stats/summary for EACH commit
        detailed_commit_history = ""
        if commit_lines and commit_lines[0]: # Check if not empty
            for line in commit_lines:
                try:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        commit_hash, commit_msg = parts
                        # Get diff for this specific commit
                        commit_diff_cmd = ["git", "show", "--stat", "--oneline", commit_hash]
                        commit_diff_res = subprocess.run(commit_diff_cmd, cwd=target_dir, capture_output=True, text=True)
                        
                        # Get full diff context (limited)
                        commit_full_diff_cmd = ["git", "show", commit_hash]
                        commit_full_diff_res = subprocess.run(commit_full_diff_cmd, cwd=target_dir, capture_output=True, text=True)
                        
                        detailed_commit_history += f"\n--- Commit: {commit_msg} ({commit_hash[:7]}) ---\n"
                        detailed_commit_history += commit_diff_res.stdout.strip() + "\n"
                        detailed_commit_history += "Diff Snippet:\n" + commit_full_diff_res.stdout[:1500] + "\n" # Limit per commit
                except Exception:
                    continue
        else:
             # Fallback if no commits found (maybe just dirty changes?)
             detailed_commit_history = "No commits found on branch yet."

        # 3. Overall Diff
        diff_res = subprocess.run(["git", "diff", "origin/main...HEAD"], cwd=target_dir, capture_output=True, text=True)

        if template_content:
            gen_prompt = f"""
            You are an expert developer creating a Pull Request.
            
            **CRITICAL INSTRUCTION**: 
            The PR Title MUST derive directly from the branch name: '{current_branch}'.
            
            CONTEXT:
            Target Branch: {current_branch} -> main
            
            **COMMIT-BY-COMMIT ANALYSIS (Detailed)**:
            {detailed_commit_history}
            
            **FULL DIFF SUMMARY (First 6000 chars)**:
            {diff_res.stdout[:6000]}
            
            TEMPLATE:
            {template_content}
            
            INSTRUCTIONS:
            1. **Title**: Generate a conventional commit title based on '{current_branch}'.
            2. **Body**: Fill the template with details.
               - Use the "COMMIT-BY-COMMIT ANALYSIS" to accurately explain *why* and *what* changed at each step.
               - Group related changes logically.
               - Be specific about what files were modified and what the impact is.
            3. Return ONLY the filled markdown.
            4. Start output with "TITLE: <Suggested Title>".
            """
        else:
            gen_prompt = f"""
            Generate a PR Title and Body for branch '{current_branch}'.
            **Title**: Must be based on the branch name.
            **Body**: concise summary of changes.
            
            **Commit History Analysis**:
            {detailed_commit_history}
            
            Files: {diff_res.stdout[:500]}
            """
            
        ai_res = llm.invoke([HumanMessage(content=gen_prompt)])
        content = ai_res.content.strip()
        
        # Parse Title
        title = f"feat: {current_branch}"
        body = content
        
        lines = content.split('\n')
        first_line = lines[0].strip()
        if first_line.startswith("TITLE:"):
            title = first_line.replace("TITLE:", "").strip()
            body = "\n".join(lines[1:]).strip()

        # SAVE DRAFT (JSON for System)
        with open(draft_file, "w") as f:
            json.dump({"title": title, "body": body}, f)
            
        # SAVE PREVIEW (Markdown for User)
        preview_file = os.path.join(target_dir, "PR_PREVIEW.md")
        with open(preview_file, "w", encoding="utf-8") as f:
            f.write(f"# TITLE: {title}\n\n{body}")
            
        print(f"💾 Draft saved to {draft_file}")
        print(f"📝 Preview available at {preview_file} (You can edit this file and I will reload it!)")
        
    return title, body, draft_file


def generate_test_suggestions(target_dir: str = DEFAULT_TARGET_DIR):
    """LLM generates test case suggestions from diff"""
    print("\n🧪 Luma Reviewer: Analyzing for missing tests...")
    try:
        diff_res = subprocess.run(["git", "diff", "origin/main...HEAD"], cwd=target_dir, capture_output=True, text=True)
        
        test_prompt = f"""
        Analyze the following code changes and suggest 3-5 critical test cases that are missing.
        Focus on edge cases, potential bugs, and TDD coverage.
        
        Context:
        {diff_res.stdout[:5000]}
        
        Output format:
        - [ ] Test Case Name: Description
        """
        llm_reviewer = get_llm(purpose="code")
        test_suggestions = llm_reviewer.invoke([HumanMessage(content=test_prompt)]).content
        print("\n⚠️ Suggested Test Cases (Before you publish):")
        print(test_suggestions)
        print("-" * 30)
        return test_suggestions
    except Exception as e:
        print(f"⚠️ Could not generate test suggestions: {e}")
        return ""


def generate_draft_code_review(target_dir: str = DEFAULT_TARGET_DIR, max_diff_lines: int = 500) -> str:
    """
    Generate a draft_code_review.md file with full context for PR/review.
    
    Creates a reusable markdown file containing:
    - Commit history
    - File stats
    - Full diff (truncated to max_diff_lines)
    - Line of code changes summary
    
    This file can be used by:
    - Publisher Agent for PR body
    - Code Review Agent
    - External tools/AI assistants
    
    Args:
        target_dir: Project directory
        max_diff_lines: Maximum lines of diff to include
        
    Returns:
        Path to the generated draft_code_review.md file
    """
    import datetime
    
    output_path = os.path.join(target_dir, "draft_code_review.md")
    
    print("📊 Generating Draft Code Review...")
    
    # 1. Get current branch
    try:
        branch_res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=target_dir, capture_output=True, text=True
        )
        current_branch = branch_res.stdout.strip() or "unknown"
    except:
        current_branch = "unknown"
    
    # 2. Get base branch (main or master)
    base_branch = "main"
    try:
        check_main = subprocess.run(
            ["git", "rev-parse", "--verify", "origin/main"],
            cwd=target_dir, capture_output=True, text=True
        )
        if check_main.returncode != 0:
            base_branch = "master"
    except:
        pass
    
    # 3. Commit log
    try:
        commits_res = subprocess.run(
            ["git", "log", f"origin/{base_branch}..HEAD", "--oneline", "--no-merges"],
            cwd=target_dir, capture_output=True, text=True
        )
        commits = commits_res.stdout.strip() or "No commits yet"
    except:
        commits = "Failed to get commits"
    
    # 4. Diff stats (--stat)
    try:
        stat_res = subprocess.run(
            ["git", "diff", "--stat", f"origin/{base_branch}..HEAD"],
            cwd=target_dir, capture_output=True, text=True
        )
        diff_stat = stat_res.stdout.strip() or "No changes"
    except:
        diff_stat = "Failed to get stats"
    
    # 5. Line changes summary (insertions/deletions)
    try:
        shortstat_res = subprocess.run(
            ["git", "diff", "--shortstat", f"origin/{base_branch}..HEAD"],
            cwd=target_dir, capture_output=True, text=True
        )
        line_changes = shortstat_res.stdout.strip() or "No line changes"
    except:
        line_changes = "Failed to get line counts"
    
    # 6. Full diff (truncated)
    try:
        diff_res = subprocess.run(
            ["git", "diff", f"origin/{base_branch}..HEAD"],
            cwd=target_dir, capture_output=True, text=True
        )
        full_diff = diff_res.stdout
        
        # Truncate by lines
        diff_lines = full_diff.split('\n')
        if len(diff_lines) > max_diff_lines:
            full_diff = '\n'.join(diff_lines[:max_diff_lines])
            full_diff += f"\n\n... (truncated, {len(diff_lines) - max_diff_lines} more lines)"
    except:
        full_diff = "Failed to get diff"
    
    # 7. Generate markdown content
    content = f"""# Draft Code Review

> 📅 Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 🌿 Branch: `{current_branch}` → `{base_branch}`

---

## 📊 Summary

{line_changes}

---

## 📝 Commits

```
{commits}
```

---

## 📁 Changed Files

```
{diff_stat}
```

---

## 🔍 Full Diff

```diff
{full_diff}
```

---

## Notes

<!-- Add your notes here before using this for PR -->

"""
    
    # 8. Write file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Draft saved to: {output_path}")
    print(f"   📋 {line_changes}")
    
    return output_path

def get_git_changed_files(mode: str = "all", target_dir: str = DEFAULT_TARGET_DIR):
    """Get changed files from git based on mode"""
    files = set()
    
    if mode == "all":
        # 1. Commits vs origin/main
        print("   📡 Configuring git scope (origin/main...HEAD)...")
        cmd_commits = ["git", "diff", "--name-only", "--relative", "origin/main...HEAD"]
        res_commits = subprocess.run(cmd_commits, cwd=target_dir, capture_output=True, text=True)
        if res_commits.returncode == 0:
            files.update([f.strip() for f in res_commits.stdout.split('\n') if f.strip()])

        # 2. Local Dirty (Staged + Unstaged)
        cmd_dirty = ["git", "diff", "--name-only", "--relative", "HEAD"]
        res_dirty = subprocess.run(cmd_dirty, cwd=target_dir, capture_output=True, text=True)
        files.update([f.strip() for f in res_dirty.stdout.split('\n') if f.strip()])
        
        # 3. Untracked
        cmd_untracked = ["git", "ls-files", "--others", "--exclude-standard"]
        res_untracked = subprocess.run(cmd_untracked, cwd=target_dir, capture_output=True, text=True)
        files.update([f.strip() for f in res_untracked.stdout.split('\n') if f.strip()])
        
    return list(files)


# --- Multi-Repo PR Functions ---

# GitHub Integration
from .github_client import get_open_pr, create_pull_request, update_pull_request


def check_branch_sync(repo_configs: list) -> tuple:
    """
    Check if all repos are on the same branch.
    
    Args:
        repo_configs: List of dicts with keys: 'name', 'path', 'repo'
    
    Returns:
        Tuple of (is_synced: bool, branches: dict)
    """
    branches = {}
    
    for config in repo_configs:
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=config["path"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                branches[config["name"]] = result.stdout.strip()
            else:
                branches[config["name"]] = "unknown"
        except Exception as e:
            branches[config["name"]] = f"error: {e}"
    
    unique_branches = set(branches.values())
    is_synced = len(unique_branches) == 1 and "unknown" not in unique_branches and not any("error" in b for b in unique_branches)
    
    return is_synced, branches


def create_branch_in_repos(repo_configs: list, branch_name: str) -> tuple:
    """
    Create a new branch in all repos and checkout to it.
    
    Args:
        repo_configs: List of dicts with keys: 'name', 'path', 'repo'
        branch_name: Name of the branch to create
    
    Returns:
        Tuple of (all_success: bool, results: dict)
    """
    results = {}
    all_success = True
    
    for config in repo_configs:
        try:
            # Checkout to main first
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=config["path"],
                capture_output=True,
                text=True
            )
            
            # Pull latest
            subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=config["path"],
                capture_output=True,
                text=True
            )
            
            # Create and checkout new branch
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=config["path"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                results[config["name"]] = f"✅ Created '{branch_name}'"
            else:
                # Maybe branch already exists, try to checkout
                checkout_result = subprocess.run(
                    ["git", "checkout", branch_name],
                    cwd=config["path"],
                    capture_output=True,
                    text=True
                )
                if checkout_result.returncode == 0:
                    results[config["name"]] = f"✅ Switched to existing '{branch_name}'"
                else:
                    results[config["name"]] = f"❌ Failed: {result.stderr.strip()}"
                    all_success = False
                    
        except Exception as e:
            results[config["name"]] = f"❌ Error: {e}"
            all_success = False
    
    return all_success, results
def gather_git_data_for_docs(repo_path: str, base_branch: str = "main") -> dict:
    """
    Gather git data for documentation generation.
    
    Returns dict with:
        - diff_stat: file changes summary
        - commit_log: list of commits
        - feat_commits: feature commits (conventional)
        - fix_commits: fix commits (conventional)
        - changed_files: list of changed files
    """
    data = {
        "diff_stat": "",
        "commit_log": [],
        "feat_commits": [],
        "fix_commits": [],
        "changed_files": [],
        "contributors": []
    }
    
    try:
        # 1. Git diff --stat (file changes summary)
        stat_res = subprocess.run(
            ["git", "diff", "--stat", f"origin/{base_branch}...HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        data["diff_stat"] = stat_res.stdout.strip()
        
        # 2. Git log --oneline (commit history)
        log_res = subprocess.run(
            ["git", "log", f"origin/{base_branch}..HEAD", "--oneline", "--no-merges"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if log_res.stdout.strip():
            data["commit_log"] = log_res.stdout.strip().split('\n')
        
        # 3. Feature commits (grep feat)
        feat_res = subprocess.run(
            ["git", "log", f"origin/{base_branch}..HEAD", "--oneline", "--no-merges", "--grep=feat"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if feat_res.stdout.strip():
            data["feat_commits"] = feat_res.stdout.strip().split('\n')
        
        # 4. Fix commits (grep fix)
        fix_res = subprocess.run(
            ["git", "log", f"origin/{base_branch}..HEAD", "--oneline", "--no-merges", "--grep=fix"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if fix_res.stdout.strip():
            data["fix_commits"] = fix_res.stdout.strip().split('\n')
        
        # 5. Changed files
        files_res = subprocess.run(
            ["git", "diff", "--name-only", f"origin/{base_branch}...HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if files_res.stdout.strip():
            data["changed_files"] = files_res.stdout.strip().split('\n')
        
        # 6. Contributors
        contrib_res = subprocess.run(
            ["git", "shortlog", "-sn", f"origin/{base_branch}..HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if contrib_res.stdout.strip():
            data["contributors"] = contrib_res.stdout.strip().split('\n')
            
    except Exception as e:
        print(f"   ⚠️ Error gathering git data: {e}")
    
    return data


def get_current_version(repo_path: str, version_file: str = None) -> str:
    """
    Get current version from specified version_file or auto-detect.
    Supports: VERSION file, package.json, build.gradle.kts, git tags.
    """
    import re
    
    # If version_file is specified, use it directly
    if version_file:
        full_path = os.path.join(repo_path, version_file)
        if os.path.exists(full_path):
            # Simple VERSION file (just version number)
            if version_file.upper() == "VERSION" or version_file.endswith("/VERSION"):
                try:
                    with open(full_path, 'r') as f:
                        return f.read().strip()
                except:
                    pass
            
            # package.json
            elif version_file.endswith("package.json"):
                try:
                    with open(full_path, 'r') as f:
                        data = json.load(f)
                    return data.get('version', '')
                except:
                    pass
            
            # build.gradle / build.gradle.kts
            elif "build.gradle" in version_file:
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()
                    match = re.search(r'versionName\s*[=]?\s*["\']([^"\']+)["\']', content)
                    if match:
                        return match.group(1)
                except:
                    pass
    
    # Fallback: auto-detect (original behavior)
    # Try package.json
    package_json = os.path.join(repo_path, "package.json")
    if os.path.exists(package_json):
        try:
            with open(package_json, 'r') as f:
                data = json.load(f)
            return data.get('version', '')
        except:
            pass
    
    # Try build.gradle.kts (Android)
    gradle_files = [
        os.path.join(repo_path, "app", "build.gradle.kts"),
        os.path.join(repo_path, "app", "build.gradle"),
    ]
    for gradle_file in gradle_files:
        if os.path.exists(gradle_file):
            try:
                with open(gradle_file, 'r') as f:
                    content = f.read()
                match = re.search(r'versionName\s*[=]?\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
            except:
                pass
    
    # Try VERSION file
    version_path = os.path.join(repo_path, "VERSION")
    if os.path.exists(version_path):
        try:
            with open(version_path, 'r') as f:
                return f.read().strip()
        except:
            pass
    
    # Try latest git tag
    try:
        tag_res = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if tag_res.returncode == 0 and tag_res.stdout.strip():
            return tag_res.stdout.strip().lstrip('v')
    except:
        pass
    
    return ""


def extract_version_from_changelog_entry(changelog_entry: str) -> str:
    """Extract version number from a CHANGELOG entry like '## [0.4.0] - 2026-01-18'."""
    import re
    match = re.search(r'\[(\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?)\]', changelog_entry)
    if match:
        return match.group(1)
    return ""


def _suggest_bumped_version(current_version: str, bump_type: str = "patch") -> str:
    """Suggest a bumped version based on semantic versioning."""
    if not current_version:
        return "1.0.0"
    
    parts = current_version.split('.')
    if len(parts) < 3:
        return current_version
    
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2].split('-')[0])
        if bump_type == "major":
            return f"{major + 1}.0.0"
        elif bump_type == "minor":
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"
    except ValueError:
        return current_version


def _update_changelog_version(changelog_path: str, old_version: str, new_version: str) -> bool:
    """Update version in CHANGELOG.md file."""
    try:
        with open(changelog_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the first occurrence of old version with new version
        updated_content = content.replace(f"[{old_version}]", f"[{new_version}]", 1)
        
        if updated_content != content:
            with open(changelog_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            return True
        return False
    except Exception:
        return False


def update_version_in_file(repo_path: str, new_version: str, version_file: str = None) -> dict:
    """
    Update version in source files.
    If version_file is specified, use it directly. Otherwise auto-detect.
    Supports: VERSION file, package.json, build.gradle.kts.
    Returns dict with 'success', 'file', 'old_version', 'new_version'.
    """
    import re
    
    result = {
        "success": False,
        "file": None,
        "old_version": None,
        "new_version": new_version,
        "error": None
    }
    
    # If version_file is specified, use it directly
    if version_file:
        full_path = os.path.join(repo_path, version_file)
        if os.path.exists(full_path):
            try:
                # Simple VERSION file
                if version_file.upper() == "VERSION" or version_file.endswith("/VERSION"):
                    with open(full_path, 'r') as f:
                        result["old_version"] = f.read().strip()
                    with open(full_path, 'w') as f:
                        f.write(new_version + '\n')
                    result["success"] = True
                    result["file"] = version_file
                    return result
                
                # package.json
                elif version_file.endswith("package.json"):
                    with open(full_path, 'r') as f:
                        data = json.load(f)
                    result["old_version"] = data.get('version', '')
                    data['version'] = new_version
                    with open(full_path, 'w') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                        f.write('\n')
                    result["success"] = True
                    result["file"] = version_file
                    return result
                
                # build.gradle / build.gradle.kts
                elif "build.gradle" in version_file:
                    with open(full_path, 'r') as f:
                        content = f.read()
                    match = re.search(r'versionName\s*[=]?\s*["\']([^"\']+)["\']', content)
                    if match:
                        result["old_version"] = match.group(1)
                        new_content = re.sub(
                            r'(versionName\s*[=]?\s*["\'])([^"\']+)(["\'])',
                            f'\\g<1>{new_version}\\g<3>',
                            content
                        )
                        with open(full_path, 'w') as f:
                            f.write(new_content)
                        result["success"] = True
                        result["file"] = version_file
                        return result
            except Exception as e:
                result["error"] = str(e)
                return result
    
    # Fallback: auto-detect (original behavior)
    # Try package.json
    package_json = os.path.join(repo_path, "package.json")
    if os.path.exists(package_json):
        try:
            with open(package_json, 'r') as f:
                data = json.load(f)
            result["old_version"] = data.get('version', '')
            data['version'] = new_version
            with open(package_json, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write('\n')
            result["success"] = True
            result["file"] = "package.json"
            return result
        except Exception as e:
            result["error"] = str(e)
    
    # Try build.gradle.kts (Android)
    gradle_files = [
        os.path.join(repo_path, "app", "build.gradle.kts"),
        os.path.join(repo_path, "app", "build.gradle"),
    ]
    for gradle_file in gradle_files:
        if os.path.exists(gradle_file):
            try:
                with open(gradle_file, 'r') as f:
                    content = f.read()
                match = re.search(r'versionName\s*[=]?\s*["\']([^"\']+)["\']', content)
                if match:
                    result["old_version"] = match.group(1)
                    new_content = re.sub(
                        r'(versionName\s*[=]?\s*["\'])([^"\']+)(["\'])',
                        f'\\g<1>{new_version}\\g<3>',
                        content
                    )
                    with open(gradle_file, 'w') as f:
                        f.write(new_content)
                    result["success"] = True
                    result["file"] = os.path.basename(gradle_file)
                    return result
            except Exception as e:
                result["error"] = str(e)
    
    # Try VERSION file
    version_path = os.path.join(repo_path, "VERSION")
    if os.path.exists(version_path):
        try:
            with open(version_path, 'r') as f:
                result["old_version"] = f.read().strip()
            with open(version_path, 'w') as f:
                f.write(new_version + '\n')
            result["success"] = True
            result["file"] = "VERSION"
            return result
        except Exception as e:
            result["error"] = str(e)
    
    if not result["error"]:
        result["error"] = "No version file found (VERSION, package.json, or build.gradle)"
    
    return result


def ai_generate_changelog_entry(git_data: dict, repo_name: str, existing_content: str = "", repo_path: str = "", suggested_version: str = "") -> str:
    """Use Gemini to generate CHANGELOG entry based on git data."""
    from datetime import datetime
    
    # Try to detect current version if not provided
    current_version = suggested_version
    if not current_version and repo_path:
        current_version = get_current_version(repo_path)
    
    version_hint = f"Version: {current_version}" if current_version else "Version: (suggest a semantic version based on changes)"
    
    # Try to use Gemini
    try:
        from luma_core.llm import get_llm
        
        prompt = f"""Generate a CHANGELOG.md entry for the following changes in {repo_name}.

## Git Data:
- Commits: {len(git_data.get('commit_log', []))} total
- Feature commits: {git_data.get('feat_commits', [])}
- Fix commits: {git_data.get('fix_commits', [])}
- Changed files: {git_data.get('changed_files', [])}
- Diff stats:
{git_data.get('diff_stat', 'N/A')}
- {version_hint}

## Commit History:
{chr(10).join(git_data.get('commit_log', [])[:20])}

## Existing CHANGELOG (for reference):
{existing_content[:1500] if existing_content else 'Empty'}

## Instructions:
1. Generate a new entry with format: ## [VERSION] - {datetime.now().strftime('%Y-%m-%d')}
2. If version is known, use it. If not, suggest next semantic version based on:
   - MAJOR: breaking changes
   - MINOR: new features (feat commits)
   - PATCH: bug fixes (fix commits)
3. Use categories: ### Added, ### Changed, ### Fixed, ### Removed (only if applicable)
4. Be concise but descriptive
5. Focus on user-facing changes
6. Match the language style of existing changelog (Thai or English)
7. Return ONLY the new entry (not the full changelog)

Generate the new changelog entry:"""

        print(f"   🤖 Generating CHANGELOG with AI...")
        if current_version:
            print(f"   📦 Current version: {current_version}")
        llm = get_llm(temperature=0.3, purpose="general")
        response = llm.invoke(prompt)
        if response:
            content = response.content
            # Handle case where content might be a list (e.g., from some LLM providers)
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            return content.strip() if content else ""
        return ""
        
    except Exception as e:
        print(f"   ⚠️ AI generation failed: {e}")
        # Fallback: manual format
        return _fallback_changelog_entry(git_data, repo_name)


def _fallback_changelog_entry(git_data: dict, repo_name: str) -> str:
    """Fallback changelog generation without AI."""
    from datetime import datetime
    
    lines = [f"## [{datetime.now().strftime('%Y-%m-%d')}] - {repo_name}"]
    
    if git_data.get("feat_commits"):
        lines.append("\n### Added")
        for commit in git_data["feat_commits"][:5]:
            # Extract message after hash
            msg = commit.split(' ', 1)[1] if ' ' in commit else commit
            lines.append(f"- {msg}")
    
    if git_data.get("fix_commits"):
        lines.append("\n### Fixed")
        for commit in git_data["fix_commits"][:5]:
            msg = commit.split(' ', 1)[1] if ' ' in commit else commit
            lines.append(f"- {msg}")
    
    # Other commits
    other_commits = [c for c in git_data.get("commit_log", []) 
                     if c not in git_data.get("feat_commits", []) 
                     and c not in git_data.get("fix_commits", [])]
    if other_commits:
        lines.append("\n### Changed")
        for commit in other_commits[:5]:
            msg = commit.split(' ', 1)[1] if ' ' in commit else commit
            lines.append(f"- {msg}")
    
    return '\n'.join(lines)


def ai_generate_readme_update(git_data: dict, repo_name: str, existing_content: str = "") -> str:
    """Use Gemini to suggest README updates based on git data."""
    try:
        from luma_core.llm import get_llm
        
        prompt = f"""You are updating the README.md for {repo_name}.

## CRITICAL RULES:
1. DO NOT invent, add, or fabricate any new information
2. DO NOT add sections that don't exist in the original
3. DO NOT change tech stack, badges, or role descriptions unless commits explicitly change them
4. ONLY make minimal, targeted updates based on the actual commit changes
5. If unsure about a change, DO NOT make it
6. Preserve ALL existing content structure and formatting

## Recent Commits (ONLY update based on these):
{chr(10).join(git_data.get('commit_log', [])[:10])}

## Changed Files:
{git_data.get('changed_files', [])}

## Current README (preserve structure):
{existing_content if existing_content else 'Empty'}

## What to do:
1. Look at the commits - what was ACTUALLY changed?
2. Find the MINIMAL section in README that relates to these changes
3. Make ONLY the necessary text updates
4. If commits are about scripts/docs/sync → only update relevant sections
5. If no section needs updating → respond with EXACTLY "No updates needed"

Return the FULL README with MINIMAL changes (or "No updates needed"):"""

        print(f"   🤖 Generating README updates with AI...")
        llm = get_llm(temperature=0.2, purpose="general")  # Lower temperature for less creativity
        response = llm.invoke(prompt)
        if response:
            content = response.content
            # Handle case where content might be a list (e.g., from some LLM providers)
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            return content.strip() if content else ""
        return ""
        
    except Exception as e:
        print(f"   ⚠️ AI generation failed: {e}")
        return ""


def _interactive_version_bump(config: dict, suggested_version: str = "", update_changelog: bool = False, changelog_path: str = ""):
    """Prompt user for version bump and update files."""
    try:
        version_file = config.get("version_file")
        current_version = get_current_version(config["path"], version_file)
        
        # Always show version info and ask for confirmation
        print(f"\n   📦 Version detected in CHANGELOG: {suggested_version or 'Not detected'}")
        print(f"   📦 Current version in source: {current_version or 'Not found'}")
        if version_file:
            print(f"   📄 Version file: {version_file}")
        
        current = current_version or "0.0.0"
        patch_ver = _suggest_bumped_version(current, 'patch')
        minor_ver = _suggest_bumped_version(current, 'minor')
        major_ver = _suggest_bumped_version(current, 'major')
        
        print(f"\n   🚀 Select Version Bump:")
        print(f"      [1] PATCH : {patch_ver}")
        print(f"      [2] MINOR : {minor_ver}")
        print(f"      [3] MAJOR : {major_ver}")
        
        if suggested_version and suggested_version != current:
            print(f"      [4] AI Suggested: {suggested_version} (Default)")
        
        print(f"      [0] Skip")

        # Determine prompt
        if suggested_version and suggested_version != current:
            prompt_text = f"\n   👉 Select [1-4] (Default={suggested_version}) or type custom: "
        else:
            prompt_text = f"\n   👉 Select [1-3] or type custom: "

        user_input = input(prompt_text).strip()
        
        version_to_apply = ""
        
        if user_input == '1':
            version_to_apply = patch_ver
        elif user_input == '2':
            version_to_apply = minor_ver
        elif user_input == '3':
            version_to_apply = major_ver
        elif user_input == '4' and suggested_version:
            version_to_apply = suggested_version
        elif user_input == '0':
            print(f"   ⏩ Version update skipped")
            return None
        elif user_input == "" and suggested_version and suggested_version != current:
            version_to_apply = suggested_version
        else:
            version_to_apply = user_input # Custom string or empty

            
        if version_to_apply:
            bump_result = update_version_in_file(config["path"], version_to_apply, version_file)
            if bump_result["success"]:
                print(f"   ✅ {bump_result['file']} updated: {bump_result['old_version']} → {version_to_apply}")
                
                # Also update the CHANGELOG if version differs from detected
                if update_changelog and changelog_path and version_to_apply != suggested_version and suggested_version:
                    _update_changelog_version(changelog_path, suggested_version, version_to_apply)
                    print(f"   ✅ CHANGELOG.md version updated: {suggested_version} → {version_to_apply}")
                
                return user_input # Return something to indicate success
            else:
                print(f"   ⚠️ Failed to update version: {bump_result['error']}")
    except Exception as e:
        print(f"   ⚠️ Error during version bump: {e}")
    
    return None

def update_multi_repo_docs(repo_configs: list, docs_agent_func=None) -> list:
    """
    Update documentation (CHANGELOG.md, README.md) for multiple repos with AI.
    
    Args:
        repo_configs: List of dicts with keys: 'name', 'path', 'repo'
        docs_agent_func: Optional docs agent function (not used in AI mode)
    
    Returns:
        List of results: {name: str, path: str, success: bool, error: str, files_updated: list}
    """
    results = []
    
    for config in repo_configs:
        result = {
            "name": config["name"],
            "path": config["path"],
            "success": False,
            "error": None,
            "files_updated": []
        }
        
        try:
            print(f"\n{'='*50}")
            print(f"📦 [{config['name']}] Checking documentation...")
            
            # Check for CHANGELOG.md and README.md
            changelog_path = os.path.join(config["path"], "CHANGELOG.md")
            readme_path = os.path.join(config["path"], "README.md")
            
            docs_available = []
            if os.path.exists(changelog_path):
                docs_available.append("CHANGELOG.md")
            if os.path.exists(readme_path):
                docs_available.append("README.md")
            
            if not docs_available:
                result["error"] = "No CHANGELOG.md or README.md found"
                print(f"   ⚠️ No documentation files found")
                results.append(result)
                continue
            
            print(f"   📄 Found: {', '.join(docs_available)}")
            
            # Gather git data
            print(f"   📊 Gathering git data...")
            git_data = gather_git_data_for_docs(config["path"])
            
            if not git_data.get("commit_log"):
                result["error"] = "No commits to document"
                print(f"   ⏩ No commits ahead of main")
                results.append(result)
                continue
            
            print(f"   📈 {len(git_data['commit_log'])} commit(s), {len(git_data['changed_files'])} file(s) changed")
            
            # Ask user which docs to update
            print(f"\n   ตัวเลือก:")
            print(f"   [1] 📋 CHANGELOG.md only")
            print(f"   [2] 📖 README.md only")
            print(f"   [3] 📚 Both")
            print(f"   [0] ⏩ Skip")
            
            doc_choice = input(f"   👉 Select: ").strip()
            
            if doc_choice == "0":
                result["error"] = "Skipped by user"
                results.append(result)
                continue
            
            files_to_update = []
            if doc_choice == "1" and "CHANGELOG.md" in docs_available:
                files_to_update = ["CHANGELOG.md"]
            elif doc_choice == "2" and "README.md" in docs_available:
                files_to_update = ["README.md"]
            elif doc_choice == "3":
                files_to_update = docs_available
            else:
                result["error"] = "Invalid choice"
                results.append(result)
                continue
            
            # Variables for version bumping logic later
            detected_version_from_changelog = ""
            changelog_was_updated = False
            
            # Process each doc
            for doc_name in files_to_update:
                doc_path = os.path.join(config["path"], doc_name)
                
                # Read existing content
                existing_content = ""
                if os.path.exists(doc_path):
                    with open(doc_path, 'r', encoding='utf-8') as f:
                        existing_content = f.read()
                
                # Generate new content with AI
                if doc_name == "CHANGELOG.md":
                    new_entry = ai_generate_changelog_entry(
                        git_data, 
                        config["name"], 
                        existing_content,
                        repo_path=config["path"]
                    )
                    if new_entry:
                        # Prepend new entry after header
                        if existing_content.startswith("# Changelog"):
                            header_end = existing_content.find('\n\n')
                            if header_end > 0:
                                new_content = existing_content[:header_end+2] + new_entry + "\n\n" + existing_content[header_end+2:]
                            else:
                                new_content = existing_content + "\n\n" + new_entry
                        else:
                            new_content = "# Changelog\n\n" + new_entry + "\n\n" + existing_content
                        
                        # Save preview
                        preview_path = os.path.join(config["path"], f"{doc_name}.PREVIEW.md")
                        with open(preview_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        # Show new entry preview
                        print(f"\n   📋 NEW CHANGELOG ENTRY:")
                        print(f"   " + "=" * 45)
                        for line in new_entry.split('\n')[:20]:
                            print(f"   {line}")
                        print(f"   " + "=" * 45)
                        
                        # Show diff comparison with existing
                        if existing_content:
                            # Extract first existing entry for comparison
                            existing_lines = existing_content.split('\n')
                            first_entry_lines = []
                            for i, line in enumerate(existing_lines):
                                if i > 0 and line.startswith('## '):
                                    # Found next entry header, stop
                                    break
                                if i > 0:  # Skip the # Changelog header
                                    first_entry_lines.append(line)
                            
                            if first_entry_lines:
                                print(f"\n   📜 PREVIOUS ENTRY (for comparison):")
                                print(f"   " + "-" * 45)
                                for line in first_entry_lines[:10]:
                                    print(f"   {line}")
                                print(f"   " + "-" * 45)
                        
                        # Open VS Code diff view for comparison
                        print(f"\n   📊 Opening VS Code diff...")
                        print(f"      code --diff {doc_path} {preview_path}")
                        subprocess.run(["code", "--diff", doc_path, preview_path], capture_output=True)
                        
                        save_choice = input(f"\n   💾 Save CHANGELOG changes? (y/N): ").lower()
                        if save_choice == 'y':
                            with open(doc_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            result["files_updated"].append(doc_name)
                            print(f"   ✅ CHANGELOG.md updated!")
                            
                            # Capture suggested version for the standalone bump step
                            detected_version_from_changelog = extract_version_from_changelog_entry(new_entry)
                            changelog_was_updated = True
                        
                        # Cleanup preview
                        if os.path.exists(preview_path):
                            os.remove(preview_path)
                
                elif doc_name == "README.md":
                    new_content = ai_generate_readme_update(git_data, config["name"], existing_content)
                    if new_content and new_content != "No updates needed":
                        preview_path = os.path.join(config["path"], f"{doc_name}.PREVIEW.md")
                        with open(preview_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        print(f"\n   📄 README Preview generated")
                        print(f"\n   📊 Opening VS Code diff...")
                        print(f"      code --diff {doc_path} {preview_path}")
                        subprocess.run(["code", "--diff", doc_path, preview_path], capture_output=True)
                        
                        save_choice = input(f"\n   💾 Save README changes? (y/N): ").lower()
                        if save_choice == 'y':
                            with open(doc_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            result["files_updated"].append(doc_name)
                            print(f"   ✅ README.md updated!")
                        
                        if os.path.exists(preview_path):
                            os.remove(preview_path)
                    else:
                        print(f"   ℹ️ No README updates needed")
            
            # === Version Bump Step (Decoupled) ===
            # Run this if any files were updated OR if user explicitly wants to check version
            # Here we run it if at least one doc was attempted/updated, or we can just always run it for flow
            if result["files_updated"]:
                print(f"\n   🔖 Version Bump Check...")
                updated_ver = _interactive_version_bump(
                    config, 
                    suggested_version=detected_version_from_changelog, 
                    update_changelog=changelog_was_updated,
                    changelog_path=changelog_path
                )
                if updated_ver:
                     result["files_updated"].append("VERSION(bump)")
            
            if result["files_updated"]:
                result["success"] = True
                
        except Exception as e:
            result["error"] = str(e)
        
        results.append(result)
    
    return results


def create_multi_repo_prs(repo_configs: list, base_branch: str = "main") -> list:
    """
    Create PRs for multiple repos.
    
    Args:
        repo_configs: List of dicts with keys: 'name', 'path', 'repo'
        base_branch: Target branch (default: main)
    
    Returns:
        List of results: {repo: str, url: str, success: bool, error: str}
    """
    if not create_pull_request:
        print("❌ GitHub fetcher not available.")
        return []
    
    results = []
    
    for config in repo_configs:
        result = {
            "repo": config["repo"],
            "name": config["name"],
            "url": None,
            "success": False,
            "error": None
        }
        
        try:
            # Get current branch
            branch_res = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=config["path"],
                capture_output=True,
                text=True
            )
            current_branch = branch_res.stdout.strip()
            
            if not current_branch or current_branch in ['main', 'master']:
                result["error"] = f"On {current_branch or 'unknown'} branch, skipping"
                results.append(result)
                continue
            
            # Check if there are commits ahead of main
            commits_ahead_res = subprocess.run(
                ["git", "rev-list", "--count", f"origin/{base_branch}..HEAD"],
                cwd=config["path"],
                capture_output=True,
                text=True
            )
            commits_ahead = int(commits_ahead_res.stdout.strip() or "0")
            
            if commits_ahead == 0:
                result["error"] = f"No commits ahead of {base_branch}, skipping"
                print(f"⏩ [{config['name']}] No commits ahead of {base_branch}, skipping")
                results.append(result)
                continue
            
            print(f"\n{'='*50}")
            print(f"� [{config['name']}] {commits_ahead} commit(s) ahead of {base_branch}")
            
            # Step 1: Check if create new or update existing
            existing_pr = get_open_pr(config["repo"], current_branch) if get_open_pr else None
            
            if existing_pr:
                print(f"   🔄 Mode: UPDATE existing PR #{existing_pr['number']}")
                print(f"   🔗 {existing_pr['html_url']}")
            else:
                print(f"   🆕 Mode: CREATE new PR")
            
            # Step 2: Generate new PR draft
            print(f"\n   📊 Generating PR draft...")
            title, body, draft_json_file = load_or_generate_pr_content(
                current_branch, 
                config["repo"], 
                target_dir=config["path"]
            )
            
            # Step 3: Create .md preview file and open it
            preview_file = os.path.join(config["path"], "PR_DRAFT_PREVIEW.md")
            with open(preview_file, "w") as f:
                f.write(f"# {title}\n\n")
                f.write(f"**Repo:** {config['repo']}\n")
                f.write(f"**Branch:** {current_branch}\n")
                if existing_pr:
                    f.write(f"**Action:** Update PR #{existing_pr['number']}\n")
                else:
                    f.write(f"**Action:** Create new PR\n")
                f.write("\n---\n\n")
                f.write(body or '')
            
            print(f"   📄 Opening preview: {preview_file}")
            subprocess.run(["open", preview_file], capture_output=True)
            
            # Step 4: Submit or Cancel
            submit_choice = input(f"   ✅ Submit this PR? (y/N): ").lower()
            if submit_choice != 'y':
                result["error"] = "Cancelled by user"
                print(f"   ❌ Cancelled {config['name']}")
                results.append(result)
                continue
            
            # Push branch
            print(f"   ⬆️ Pushing '{current_branch}'...") 
            push_res = subprocess.run(
                ["git", "push", "origin", current_branch],
                cwd=config["path"],
                capture_output=True,
                text=True
            )
            
            if push_res.returncode != 0:
                result["error"] = f"Push failed: {push_res.stderr}"
                results.append(result)
                continue
            
            # Create or Update PR
            if existing_pr:
                print(f"   🔄 Updating PR #{existing_pr['number']}...")
                url = update_pull_request(config["repo"], existing_pr['number'], title, body)
            else:
                print(f"   🆕 Creating new PR...")
                url = create_pull_request(config["repo"], title, body, current_branch, base_branch)
            
            if url:
                result["url"] = url
                result["success"] = True
                print(f"   ✅ Success: {url}")
                
                # Cleanup draft files
                if os.path.exists(draft_json_file):
                    os.remove(draft_json_file)
                if os.path.exists(preview_file):
                    os.remove(preview_file)
            else:
                result["error"] = "PR creation returned no URL"
                
        except Exception as e:
            result["error"] = str(e)
        
        results.append(result)
    
    return results
