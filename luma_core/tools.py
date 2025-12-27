import os
import subprocess
import json
import re
from langchain_core.messages import HumanMessage
from .llm import get_llm
from .config import TARGET_DIR

def update_android_version_logic(version: str):
    """Orchestrates the Android Version Bump and Changelog Generation"""
    project_root = os.path.dirname(TARGET_DIR) 
    cmd = ["./scripts/bump_version.sh", version]
    
    try:
        print(f"🚀 Running: {' '.join(cmd)} in {project_root}")
        subprocess.run(cmd, cwd=project_root, check=True)
        print("✅ Version Update Complete.")
        
        # --- Auto-Fill Changelog Logic ---
        print("📝 Generating Auto-Changelog from Git History...")
        
        log_cmd = ["git", "log", "-n", "20", "--pretty=format:%s"]
        log_res = subprocess.run(log_cmd, cwd=project_root, capture_output=True, text=True)
        commit_logs = log_res.stdout
        
        llm = get_llm(temperature=0.5)
        changelog_prompt = f"""
        Task: Summarize these git commits for a Changelog.
        Target Audience: Android Server Users.
        
        Commits:
        {commit_logs}
        
        **CRITICAL FILTER**: 
        Only include changes related to:
        - Go Server (server.go, *.go files, Makefile, go.mod)
        - Android Server (android-server/, gomobile, .aar)
        - Server Tests (*_test.go, TestServerParity, server test files)
        - Server Workflows (bump_version.sh, scripts/)
        
        **EXCLUDE completely**:
        - Client changes (client-nuxt/, Vue components, TypeScript, package.json)
        - UI/Frontend changes (CSS, Canvas, mobile layout, touch controls)
        - Game logic in TypeScript (Game.ts, OnlineGame.ts, etc.)
        
        Instructions:
        1. Group into 'Fixed' (bug fixes) and 'Added' (new features).
        2. Return ONLY the bullet points (markdown format). 
        3. Do not include headers like '### Fixed', just the bullet points.
        4. If NO server-related items exist, return "No server changes in this release."
        
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

def generate_branch_suggestions():
    """LLM-powered branch name suggestions based on git diff"""
    print("📊 Analyzing local changes for suggestions...")
    
    # Get diff summary
    status_res = subprocess.run(["git", "status", "--short"], cwd=TARGET_DIR, capture_output=True, text=True)
    
    try:
        diff_stat = subprocess.check_output(["git", "diff", "--stat"], cwd=TARGET_DIR, text=True).strip()
        diff_cached_stat = subprocess.check_output(["git", "diff", "--cached", "--stat"], cwd=TARGET_DIR, text=True).strip()
    except:
        diff_stat = ""
        diff_cached_stat = ""

    try:
        diff_content = subprocess.check_output(["git", "diff"], cwd=TARGET_DIR, text=True).strip()
        diff_cached_content = subprocess.check_output(["git", "diff", "--cached"], cwd=TARGET_DIR, text=True).strip()
    except:
        diff_content = ""
        diff_cached_content = ""

    full_diff = (diff_content + "\n" + diff_cached_content)[:3000]

    log_res = subprocess.run(["git", "log", "-n", "5", "--pretty=format:%s"], cwd=TARGET_DIR, capture_output=True, text=True)
    
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


def get_user_branch_choice():
    """Interactive branch selection with AI suggestions"""
    suggestions = generate_branch_suggestions()
    
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


def load_or_generate_pr_content(current_branch: str, repo: str):
    """Load draft or generate PR title/body via LLM"""
    draft_file = os.path.join(TARGET_DIR, ".pr_draft.json")
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
            os.path.join(TARGET_DIR, ".github", "pull_request_template.md"),
            os.path.join(os.path.dirname(os.path.abspath(TARGET_DIR)), ".github", "pull_request_template.md")
        ]
        template_path = next((p for p in possible_templates if os.path.exists(p)), None)
        
        template_content = ""
        if template_path:
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
                
        # Generate Content with Enhanced Context
        print("📊 Analyzing changes for description...")
        
        llm = get_llm(purpose="code")
        
        # Get Commit Logs & Diff
        log_res = subprocess.run(["git", "log", "origin/main..HEAD", "--pretty=format:%s%n%b"], cwd=TARGET_DIR, capture_output=True, text=True)
        commit_logs = log_res.stdout.strip()
        
        diff_res = subprocess.run(["git", "diff", "origin/main...HEAD"], cwd=TARGET_DIR, capture_output=True, text=True)

        if template_content:
            gen_prompt = f"""
            You are an expert developer creating a Pull Request.
            
            **CRITICAL INSTRUCTION**: 
            The PR Title MUST derive directly from the branch name: '{current_branch}'.
            
            CONTEXT:
            Target Branch: {current_branch} -> main
            
            COMMITS:
            {commit_logs}
            
            **CODE DIFF (First 6000 chars)**:
            {diff_res.stdout[:6000]}
            
            TEMPLATE:
            {template_content}
            
            INSTRUCTIONS:
            1. **Title**: Generate a conventional commit title based on '{current_branch}'.
            2. **Body**: Fill the template with details from the commits and file changes.
            3. Return ONLY the filled markdown.
            4. Start output with "TITLE: <Suggested Title>".
            """
        else:
            gen_prompt = f"""
            Generate a PR Title and Body for branch '{current_branch}'.
            **Title**: Must be based on the branch name.
            **Body**: concise summary of changes.
            
            Commits: {commit_logs}
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


def generate_test_suggestions():
    """LLM generates test case suggestions from diff"""
    print("\n🧪 Luma Reviewer: Analyzing for missing tests...")
    try:
        diff_res = subprocess.run(["git", "diff", "origin/main...HEAD"], cwd=TARGET_DIR, capture_output=True, text=True)
        
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


def get_git_changed_files(mode: str = "all"):
    """Get changed files from git based on mode"""
    files = set()
    
    if mode == "all":
        # 1. Commits vs origin/main
        print("   📡 Configuring git scope (origin/main...HEAD)...")
        cmd_commits = ["git", "diff", "--name-only", "--relative", "origin/main...HEAD"]
        res_commits = subprocess.run(cmd_commits, cwd=TARGET_DIR, capture_output=True, text=True)
        if res_commits.returncode == 0:
            files.update([f.strip() for f in res_commits.stdout.split('\n') if f.strip()])

        # 2. Local Dirty (Staged + Unstaged)
        cmd_dirty = ["git", "diff", "--name-only", "--relative", "HEAD"]
        res_dirty = subprocess.run(cmd_dirty, cwd=TARGET_DIR, capture_output=True, text=True)
        files.update([f.strip() for f in res_dirty.stdout.split('\n') if f.strip()])
        
        # 3. Untracked
        cmd_untracked = ["git", "ls-files", "--others", "--exclude-standard"]
        res_untracked = subprocess.run(cmd_untracked, cwd=TARGET_DIR, capture_output=True, text=True)
        files.update([f.strip() for f in res_untracked.stdout.split('\n') if f.strip()])
        
    return list(files)
