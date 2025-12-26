import os
import subprocess
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
        
        Instructions:
        1. Group into 'Fixed' (bug fixes) and 'Added' (new features).
        2. Return ONLY the bullet points (markdown format). 
        3. Do not include headers like '### Fixed', just the bullet points.
        4. If a category has no items, output nothing for it.
        
        Format Example:
        - Fixed crash on startup
        - Added new icon
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
            
            Output Format:
            ### Added
            - ...
            
            ### Fixed
            - ...
            
            (Only output applicable sections)
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
