import os
import json
import datetime
import subprocess
from langchain_core.messages import HumanMessage
from ..state import AgentState
from ..llm import get_llm
from ..config import TARGET_DIR

def docs_agent(state: AgentState):
    """Docs Agent: อัปเดตเอกสารและ Versioning"""
    print("📚 Docs Agent: Checking for documentation updates...")
    
    changes = state.get('changes', {})
    task = state.get('task', "")
    
    # Support for "Docs Only" mode (Manual Git Changes)
    if not changes and state.get("skip_coder"):
        print("   🔍 No internal changes. Checking for local Git changes...")
        try:
            # Get list of changed files (Unstaged + Staged)
            cmd_unstaged = ["git", "diff", "--name-only"]
            cmd_staged = ["git", "diff", "--name-only", "--cached"]
            
            files_unstaged = subprocess.run(cmd_unstaged, cwd=TARGET_DIR, capture_output=True, text=True).stdout.splitlines()
            files_staged = subprocess.run(cmd_staged, cwd=TARGET_DIR, capture_output=True, text=True).stdout.splitlines()
            
            git_files = list(set(files_unstaged + files_staged))
            
            # Filter out docs themselves to avoid infinite loop
            git_files = [f for f in git_files if f not in ["CHANGELOG.md", "package.json"]]
            
            if git_files:
                print(f"   📂 Detected local changes in: {git_files}")
                changes_context = git_files
            else:
                print("   🔍 No local dirty changes. Checking diff against origin/main...")
                try:
                    cmd_diff = ["git", "diff", "--name-only", "origin/main...HEAD"]
                    res = subprocess.run(cmd_diff, cwd=TARGET_DIR, capture_output=True, text=True)
                    
                    if res.returncode != 0:
                        print(f"   ⚠️ 'git diff origin/main' failed. Trying local 'main'...")
                        res = subprocess.run(["git", "diff", "--name-only", "main...HEAD"], cwd=TARGET_DIR, capture_output=True, text=True)
                    
                    diff_files = res.stdout.splitlines()
                    diff_files = [f for f in diff_files if f not in ["CHANGELOG.md", "package.json"]]
                    
                    if diff_files:
                        print(f"   📂 Detected committed changes: {diff_files}")
                        changes_context = diff_files
                    else:
                        print("   ⚠️ No changes found (Local or Committed via Git).")
                        return {}
                        
                except Exception as e:
                    print(f"   ⚠️ Git check failed: {e}")
                    return {}
        except Exception as e:
            print(f"   ⚠️ Git check failed: {e}")
            return {}
    else:
        # Normal mode
        if not changes:
            print("   No changes detected. Skipping Docs.")
            return {}
        changes_context = list(changes.keys())

    # 1. Read package.json & CHANGELOG.md from Target Dir
    pkg_path = os.path.join(TARGET_DIR, "package.json")
    changelog_path = os.path.join(TARGET_DIR, "CHANGELOG.md")
    
    current_version = "0.0.0"
    pkg_content = "{}"
    changelog_content = ""
    
    # Read package.json
    if os.path.exists(pkg_path):
        with open(pkg_path, "r", encoding="utf-8") as f:
            pkg_content = f.read()
            try:
                pkg_json = json.loads(pkg_content)
                current_version = pkg_json.get("version", "0.0.0")
            except:
                pass
    
    # Read CHANGELOG.md
    if os.path.exists(changelog_path):
        with open(changelog_path, "r", encoding="utf-8") as f:
            changelog_content = f.read()
            
    # 2. Determine Version Bump (SemVer)
    lower_task = task.lower()
    bump_type = "patch"
    if "feat" in lower_task or "new" in lower_task or "add" in lower_task:
        bump_type = "minor"
    
    # Parse Version
    try:
        major, minor, patch = map(int, current_version.split("."))
        if bump_type == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1
        new_version = f"{major}.{minor}.{patch}"
    except:
        new_version = current_version
        
    print(f"   🆙 Bump Version: {current_version} -> {new_version} ({bump_type})")
    
    # 3. Generate Changelog Entry via LLM
    llm = get_llm(temperature=0.7, purpose="general")
    prompt = f"""
    Task: {task}
    
    Files Changed:
    {changes_context}
    
    Existing Changelog (Top 20 lines):
    {changelog_content[:1000]}
    
    Instruction:
    Generate a changelog entry for this update in "Keep a Changelog" format.
    - Version: [{new_version}]
    - Date: {datetime.date.today().isoformat()}
    - Section: Added, Changed, Fixed, or Removed
    - Bullet points summarizing the change.
    
    Output ONLY the new markdown section. Do not output the whole file.
    """
    
    result_changes = {}
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        new_entry = response.content.strip()
        
        # Clean up markdown code blocks if present
        new_entry = new_entry.replace("```markdown", "").replace("```", "").strip()
        
        # 4. Integrate into Files
        
        # Update package.json
        if "package.json" not in changes:
            pkg_json = json.loads(pkg_content)
            pkg_json["version"] = new_version
            result_changes["package.json"] = json.dumps(pkg_json, indent=2)
            print("   📝 Queueing package.json update...")

        # Update CHANGELOG.md
        if "CHANGELOG.md" not in changes:
            # Insert after the first header (usually # Changelog)
            lines = changelog_content.splitlines()
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("## ["):
                    insert_idx = i
                    break
            if insert_idx == 0 and len(lines) > 2:
                insert_idx = 2
                 
            lines.insert(insert_idx, new_entry + "\n")
            result_changes["CHANGELOG.md"] = "\n".join(lines)
            print("   📝 Queueing CHANGELOG.md update...")
            
    except Exception as e:
        print(f"⚠️ Docs Agent Error: {e}")
        
    return {"changes": result_changes}
