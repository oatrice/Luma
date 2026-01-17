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
    
    # Check for existing DRAFT
    if os.path.exists(draft_file):
        print("📄 Found saved PR Draft!")
        if input("Reuse saved draft? (y/N): ").lower() == 'y':
            try:
                with open(draft_file, "r") as f:
                    data = json.load(f)
                    title = data.get("title", "")
                    body = data.get("body", "")
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

        # SAVE DRAFT
        with open(draft_file, "w") as f:
            json.dump({"title": title, "body": body}, f)
        print(f"💾 Draft saved to {draft_file}")
        
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


