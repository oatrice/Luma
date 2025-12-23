import os
from dotenv import load_dotenv
from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI 
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

# Load environment variables from .env file
load_dotenv()

# --- Config ---
# Select Provider: "gemini" or "openrouter"
LLM_PROVIDER = "gemini" 

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_CODE_MODEL = "qwen/qwen3-coder:free"
OPENROUTER_GENERAL_MODEL = "mistralai/mistral-7b-instruct:free"


# Gemini Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_CODE_MODEL = "gemini-flash-latest"
GEMINI_GENERAL_MODEL = "gemini-2.5-flash-lite"

TARGET_DIR = "../Tetris-Battle/client-nuxt"

# --- 1. Define State (หน่วยความจำของ Agent) ---
class AgentState(TypedDict):
    task: str           # คำสั่งจากเรา
    code_content: str   # โค้ดที่ AI เขียนเสร็จแล้ว
    filename: str       # ชื่อไฟล์ที่จะบันทึก
    test_errors: str    # (New) Error Log จากการรัน Test
    iterations: int     # (New) จำนวนรอบที่วน Loop แก้ไปแล้ว
    approved: bool      # (New) สถานะการอนุมัติจาก User
    disable_log_truncation: bool # (New) Flag to disable log truncation
    changes: dict[str, str]      # (New) Supports multi-file changes {filename: content}
    source_files: list[str]      # (New) List of files to provide as context
    repo: str                    # (New) Target GitHub Repository
    issue_data: dict             # (New) Issue data used for updating status
    test_suggestions: str        # (New) Recommended test cases from Reviewer
    skip_coder: bool             # (New) Flag to skip Coder Agent (Docs Only Mode)

# --- 1.5 Helper Functions ---
def get_llm(temperature=0.7, purpose="general"):
    """Factory function to get the configured LLM instance"""
    if LLM_PROVIDER == "openrouter":
        model_name = OPENROUTER_GENERAL_MODEL
        if purpose == "code":
            model_name = OPENROUTER_CODE_MODEL
        
        print(f"🔌 Using OpenRouter ({model_name})...")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
            max_tokens=4000
        )
    elif LLM_PROVIDER == "gemini":
        model_name = GEMINI_GENERAL_MODEL
        if purpose == "code":
            model_name = GEMINI_CODE_MODEL

        print(f"🔌 Using Gemini ({model_name})...")
        return ChatGoogleGenerativeAI(
            model=model_name, 
            google_api_key=GOOGLE_API_KEY,
            temperature=temperature,
            request_timeout=120
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")

# --- 2. Define Nodes (ขั้นตอนการทำงาน) ---

import json

def coder_agent(state: AgentState):
    """ทำหน้าที่เป็น Go/C++ Expert เขียนโค้ดตามคำสั่ง (Multi-file Support)"""
    print(f"🤖 Luma is thinking about: {state['task'][:100]}...")
    
    # Check for skip flag
    if state.get("skip_coder"):
        print("⏩ Skipping Coder (Docs Only Mode)...")
        return {"changes": {}}
    
    # 1. Read Source Files for Context
    source_context = ""
    if state.get("source_files"):
        print(f"🧐 Reviewing code for: {state['source_files']}...")
        source_context += "\n\n--- CURRENT SOURCE CODE ---\n"
        for rel_path in state["source_files"]:
            abs_path = os.path.join(TARGET_DIR, rel_path)
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        content_read = f.read()
                        print(f"   📖 Read context: {rel_path} ({len(content_read)} bytes)")
                        source_context += f"\nFile: {rel_path}\n```\n{content_read}\n```\n"
                except Exception as e:
                    source_context += f"\nFile: {rel_path} (Error reading: {e})\n"
            else:
                source_context += f"\nFile: {rel_path} (NOT FOUND)\n"

    # Initialize LLM based on Provider
    llm = get_llm(temperature=0.7, purpose="code")
    
    system_prompt = """You are a Senior Polyglot Developer (Python, Go, C++).
    Your goal is to write high-quality, production-ready code based on the user's task.
    You must follow TDD (Test Driven Development) practices if requested.
    
    IMPORTANT OUTPUT FORMAT:
    You must output the code for each file wrapped in XML tags.
    Example:
    <file path="client/logic.cpp">
    #include "logic.h"
    ...
    </file>
    
    <file path="client/logic.h">
    ...
    </file>
    
    Do NOT output JSON. Do NOT output markdown code blocks around the XML tags.
    """
    
    # Error Handling Logic
    if state.get('test_errors') and state.get('iterations', 0) > 0:
        print(f"🔧 Fixing bugs (Attempt {state.get('iterations', 1)})...")
        task_content = f"""
        Original Task: {state['task']}
        
        The previous code failed the tests.
        
        ERROR LOGS:
        {state['test_errors']}
        
        Please rewrite the code using the XML file format to fix these errors.
        """
    else:
        task_content = state['task']
        
    # Append Source Context
    if source_context:
        task_content += f"\n\nContext for the task:\n{source_context}"
        
    print(f"📨 Sending Prompt to LLM ({len(task_content)} chars)...")
    if "--- CURRENT SOURCE CODE ---" in task_content:
        print("   ✅ Source Code Context verified in prompt payload.")
    else:
        print("   ⚠️ Source Code Context MISSING in prompt payload!")
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=task_content)
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        
        # Parse XML-like tags
        import re
        pattern = r'<file path="([^"]+)">\s*(.*?)\s*</file>'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        changes = {}
        for match in matches:
            path = match.group(1)
            code = match.group(2)
            changes[path] = code
            
        if not changes:
             print(f"⚠️ No code blocks found! Raw Output:\n{content[:500]}...")
             
        return {"changes": changes, "code_content": content} # Return raw content for Reviewer context
        
    except Exception as e:
        print(f"⚠️ Coder Error: {e}")
        return {"changes": {}, "code_content": str(e)}

import subprocess

def reviewer_agent(state: AgentState):
    """(New Node) Reviewer Agent: ตรวจสอบและแก้ไขโค้ด"""
    # For simplicity, Reviewer currently reviews the main 'code_content'. 
    # Multi-file review logic would iterate 'changes'.
    changes = state.get('changes', {})
    
    # Check for skip flag
    if not changes and state.get("skip_coder"):
        print("⏩ Skipping Reviewer (Docs Only Mode)...")
        return {"test_suggestions": ""}

    target_files = [] 
    if changes:
        target_files = list(changes.keys())
        print(f"🧐 Reviewing code for: {target_files}...")
    else:
        print(f"🧐 Reviewing code for: New Generated Code...")
    
    # Initialize LLM based on Provider
    llm = get_llm(temperature=0, purpose="code")
    
    # Determine primary language from first file
    primary_file = target_files[0] if target_files else "unknown.py"
    
    # Prompt สำหรับ Reviewer
    review_prompt = f"""
    Task: {state['task']}
    
    Current Code input:
    {json.dumps(changes, indent=2)}
    
    Instructions:
    1. Review the code changes in the JSON above.
    2. Check for Logic Errors, Infinite Loops, and Memory Leaks.
    """
    
    if primary_file.endswith(".go"):
        review_prompt += "\n3. Ensure Go concurrency best practices (Channels, Goroutines)."
    elif primary_file.endswith(".cpp") or primary_file.endswith(".h"):
        review_prompt += "\n3. Ensure C++ memory safety (RAII) and Raylib correctness."
    else:
        review_prompt += "\n3. Ensure Python PEP8 and Type Hinting."
        
    review_prompt += "\n\nIf the code looks correct, output ONLY 'PASS'. Otherwise, explain the fix."
    
    messages = [
        SystemMessage(content="You are a Senior Code Reviewer. Your goal is to review the provided code changes. If the code is correct and meets all instructions, output ONLY 'PASS'. If there are issues, explain the fix or the problem clearly."),
        HumanMessage(content=review_prompt)
    ]
    
    response = llm.invoke(messages)
    content = response.content.strip()
    
    # --- Heuristic Check ---
    if primary_file.endswith(".go"):
        if not content.startswith("package "):
            print(f"⚠️ Auto-Fixing: Added 'package main' to {primary_file}")
            content = "package main\n\n" + content
            
    # --- 4. Test Advice (New) ---
    advice = ""
    try:
        print("🧪 Reviewer: Analyzing for missing tests...")
        advice_prompt = f"""
        Analyze the code changes below and list 3 critical test cases that should be added/verified.
        Focus on edge cases.
        
        Code:
        {json.dumps(changes, indent=2)[:3000]}
        
        Output: Bullet points only.
        """
        advice = llm.invoke([HumanMessage(content=advice_prompt)]).content
        print(f"\n⚠️ Recommended Test Cases:\n{advice}\n")
    except Exception as e:
        print(f"⚠️ Reviewer Advice failed: {e}")

    return {"code_content": content, "test_suggestions": advice}

import shutil

def tester_agent(state: AgentState):
    """(New Node) Tester Agent: รัน Unit Test ตรวจสอบความถูกต้อง (Ephemeral Testing with Multi-File support)"""
    # 1. Prepare Changes
    changes = state.get('changes', {})
    if not changes and state.get('filename'):
        changes = {state['filename']: state['code_content']}
        
    print(f"🧪 Testing code logic for {list(changes.keys())}...")
    
    backups = {} # Map full_path -> backup_path
    created_files = [] # List of full_paths created from scratch
    
    try:
        # 2. Batch Backup & Write
        for filename, content in changes.items():
            full_path = os.path.join(TARGET_DIR, filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Backup
            if os.path.exists(full_path):
                backup_path = full_path + ".bak"
                shutil.copy2(full_path, backup_path)
                backups[full_path] = backup_path
            else:
                created_files.append(full_path)
            
            # Write Draft
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        
        # 3. Detect Language & Run Test
        cmd = []
        is_go = any(f.endswith(".go") for f in changes.keys())
        is_cpp = any(f.endswith(".cpp") or f.endswith(".h") or f.endswith("txt") for f in changes.keys())
        
        if is_go:
            cmd = ["go", "test", "./..."]
            cwd = TARGET_DIR
        elif is_cpp:
            print("⚙️ Detected C++ Project. Attempting to Build...")
            # Find directory containing CMakeLists.txt
            cmake_file = next((f for f in changes.keys() if f.endswith("CMakeLists.txt")), None)
            if cmake_file:
                # e.g. client/CMakeLists.txt -> project_dir = .../client
                project_dir = os.path.dirname(os.path.join(TARGET_DIR, cmake_file))
                # Build command: mkdir build -> cmake -> make
                # Using 'sh -c' to chain commands
                build_cmd = "mkdir -p build && cd build && cmake .. && make"
                cmd = ["sh", "-c", build_cmd]
                cwd = project_dir
                print(f"   Building in: {project_dir}")
            else:
                # Fallback: if only main.cpp changed but no CMakeLists in this batch, 
                # we might need to find where existing CMakeLists is.
                # For this MVP, let's skip test if no build config found, or assume 'client' dir.
                print("⚠️ No CMakeLists.txt in changes. Skip build test for now.")
                cmd = ["echo", "Skipping build test"]
                cwd = TARGET_DIR

        # Run test/build
        if cmd:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
            
            # Helper function to truncate logs
            def get_log(res):
                log = res.stderr + "\n" + res.stdout
                
                # Check flag (New)
                if state.get("disable_log_truncation"):
                    return log
                    
                if len(log) > 2000: # Limit token usage
                    return log[:2000] + "\n...(Truncated)..."
                return log
    
            if result.returncode == 0:
                print("✅ Tester: Build/Test Passed!")
                return {"test_errors": ""} 
            else:
                print("❌ Tester: Build/Test Failed!")
                current_iter = state.get("iterations", 0) + 1
                return {
                    "test_errors": get_log(result),
                    "iterations": current_iter
                }
        else:
             print("⚠️ Unknown language. Skipping test.")
             return {"test_errors": ""}
            
    except Exception as e:
        print(f"⚠️ Tester error: {e}")
        return {"test_errors": str(e)}
        
    finally:
        # 4. RESTORE (Clean up)
        # Restore backups
        for full_path, backup_path in backups.items():
            shutil.move(backup_path, full_path)
        
        # Remove newly created Drafts
        for full_path in created_files:
            if os.path.exists(full_path):
                os.remove(full_path)
        
    return {}

def should_continue(state: AgentState):
    """ตัดสินใจว่าจะไปแก้โค้ดใหม่หรือไปต่อ"""
    errors = state.get('test_errors', "")
    iterations = state.get('iterations', 0)
    
    # ถ้ามี Error และยังวนไม่เกิน 3 รอบ -> กลับไปแก้ (Retry)
    if errors and iterations < 3:
        return "retry"
    
    # ถ้าไม่มี Error หรือครบโควต้าแล้ว -> ไปต่อ Docs Agent (Pass)
    return "pass"

# --- 2.5 Docs Agent (Update Version & Changelog) ---
import datetime

def docs_agent(state: AgentState):
    """(New Node) Docs Agent: อัปเดตเอกสารและ Versioning"""
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
             
             # Filter out docs themselves to avoid infinite loop confusion
             git_files = [f for f in git_files if f not in ["CHANGELOG.md", "package.json"]]
             
             if git_files:
                 print(f"   📂 Detected local changes in: {git_files}")
                 # We don't read content to 'changes' dict (to avoid overwriting user files),
                 # but we list them for the Prompt.
                 # Let's read them for Context only.
                 changes_context = git_files
             else:
                 print("   🔍 No local dirty changes. Checking diff against origin/main...")
                 try:
                     # Check for committed changes (HEAD vs origin/main) - mimicking Reviewer Agent scope
                     # Use triple-dot to find changes on this branch since divergence
                     cmd_diff = ["git", "diff", "--name-only", "origin/main...HEAD"]
                     
                     # Ensure we have the latest remote info? (Optional, skipping fetch for speed/safety)
                     res = subprocess.run(cmd_diff, cwd=TARGET_DIR, capture_output=True, text=True)
                     
                     if res.returncode != 0:
                         print(f"   ⚠️ 'git diff origin/main' failed. Trying local 'main'...")
                         res = subprocess.run(["git", "diff", "--name-only", "main...HEAD"], cwd=TARGET_DIR, capture_output=True, text=True)
                     
                     diff_files = res.stdout.splitlines()
                     
                     # Filter docs
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
    # Heuristic: feat -> minor, fix/refactor -> patch
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
        new_version = current_version # Fallback if parse fails
        
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
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        new_entry = response.content.strip()
        
        # Clean up markdown code blocks if present
        new_entry = new_entry.replace("```markdown", "").replace("```", "").strip()
        
        # 4. Integrate into Files
        
        # Update package.json
        if pkg_path not in changes: # Update only if Coder didn't already touch it
            pkg_json = json.loads(pkg_content)
            pkg_json["version"] = new_version
            changes["package.json"] = json.dumps(pkg_json, indent=2)
            print("   📝 Queueing package.json update...")

        # Update CHANGELOG.md
        if changelog_path not in changes:
            # Insert after the first header (usually # Changelog)
            lines = changelog_content.splitlines()
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("## ["):
                    insert_idx = i
                    break
            if insert_idx == 0 and len(lines) > 2: # Fallback if no version header found yet
                 insert_idx = 2
                 
            lines.insert(insert_idx, new_entry + "\n")
            changes["CHANGELOG.md"] = "\n".join(lines)
            print("   📝 Queueing CHANGELOG.md update...")
            
    except Exception as e:
        print(f"⚠️ Docs Agent Error: {e}")
        
    return {"changes": changes}

# --- 3. Define Human Approval (การตรวจสอบจาก User) ---
import difflib
import webbrowser

def human_approval_agent(state: AgentState):
    """(Mock) ให้ User ตรวจสอบโค้ดก่อนบันทึก"""
    print("\n--- ✋ Approval Request for " + str(list(state['changes'].keys())) + " ---")
    
    # Check for Test Suggestions
    if state.get("test_suggestions"):
        print("\n🧪 Reviewer Agent Suggestions (Test Cases):")
        print("----------------------------------------")
        print(state["test_suggestions"])
        print("----------------------------------------\n")
    
    draft_files = []
    
    for filename, content in state['changes'].items():
        # Create draft file
        draft_filename = f"{TARGET_DIR}/{filename}.draft{os.path.splitext(filename)[1]}" 
        abs_path = os.path.join(TARGET_DIR, filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(draft_filename), exist_ok=True)
        
        with open(draft_filename, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"📝 Review Draft created: {draft_filename}")
        
        # --- Open VS Code Diff ---
        if os.path.exists(abs_path):
            if shutil.which("code"):
                print(f"👀 Opening Diff in Editor: code --diff {filename} ...")
                try:
                    subprocess.run(["code", "--diff", abs_path, draft_filename], check=False)
                except Exception as e:
                    print(f"   ⚠️ Failed to launch VS Code: {e}")
            else:
                # Fallback for Mac: Open the draft file using default editor
                print(f"👀 Opening Draft: open {draft_filename} ...")
                subprocess.run(["open", draft_filename], check=False)

        draft_files.append(draft_filename)

    user_input = input("Approve changes? (y/N): ").strip().lower()
    
    if user_input == 'y':
        return {"approved": True, "filename": str(draft_files)}
    else:
        return {"approved": False, "filename": ""}

def approval_gate(state: AgentState):
    if state.get("approved"):
        return "yes"
    return "no"

def file_writer(state: AgentState):
    """ทำหน้าที่บันทึกไฟล์ลง Disk (Supports Multi-File)"""
    changes = state.get('changes', {})
    if not changes and state.get('filename'):
        changes = {state['filename']: state['code_content']}
        
    for filename, content in changes.items():
        full_path = os.path.join(TARGET_DIR, filename)
        print(f"💾 Saving file to: {full_path}")
        
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # --- Cleanup Drafts & Diffs ---
        draft_path = f"{TARGET_DIR}/{filename}.draft{os.path.splitext(filename)[1]}"
        diff_path = f"{TARGET_DIR}/{filename}.diff.html"
        
        if os.path.exists(draft_path):
            os.remove(draft_path)
            print(f"   🧹 Removed draft: {draft_path}")
            
        if os.path.exists(diff_path):
            os.remove(diff_path)
            print(f"   🧹 Removed diff report: {diff_path}")
        
    return {}

def publisher_agent(state: AgentState):
    """(New Node) Publisher Agent: Push code & Open PR"""
    # Only run if approved
    if not state.get("approved"):
        return {}
        
    print("🚀 Starting Publisher Agent...")
    
    # Check if we have PR capability
    try:
        from github_fetcher import create_pull_request, update_issue_status, get_open_pr, update_pull_request
    except ImportError:
        print("⚠️ GitHub tools not found. Skipping PR.")
        return {}

    # 1. Generate Branch Name
    # 1. Generate Branch Name
    import time
    import re
    timestamp = int(time.time())
    
    # Extract Title
    task_header = state['task'].strip().split('\n')[0].strip()
    repo_name = state.get("repo", "oatrice/Tetris-Battle") # Fallback
    task_title = task_header[:50] # For commit message
    print(f"🔍 Debug Task Header: '{task_header}'")

    # Determine Branch Type
    lower_header = task_header.lower()
    if any(x in lower_header for x in ["bug", "fix"]):
        branch_type = "fix"
    elif any(x in lower_header for x in ["feat", "feature", "add"]):
        branch_type = "feat"
    elif "refactor" in lower_header:
        branch_type = "refactor"
    elif "docs" in lower_header:
        branch_type = "docs"
    elif "test" in lower_header:
        branch_type = "test"
    else:
        branch_type = "chore" # Default

    # Generate Short Slug using LLM
    try:
        print("🤖 Generating short branch name...")
        
        # Gather changes file summary for context
        changes_keys = list(state.get('changes', {}).keys())
        changes_summary = "\n".join(changes_keys[:10]) # Top 10 files
        if len(changes_keys) > 10:
            changes_summary += "\n(and more...)"
            
        llm_slug = get_llm(temperature=0.5, purpose="code")
        slug_prompt = f"""
        Task: {task_header}
        
        Modified Files:
        {changes_summary}
        
        Instruction:
        Generate a concise, consistent git branch slug based on the Task and Modified Files.
        Format: lowercase, kebab-case, 2-4 words max.
        Do NOT include prefixes like 'feat/', 'fix/', 'chore/'. ONLY the slug logic.
        
        Examples:
        - Task: "Add Ghost Piece" -> ghost-piece-toggle
        - Task: "Fix null pointer in Renderer" -> renderer-npe-fix
        - Task: "Refactor Game Loop" -> game-loop-refactor
        
        Return ONLY the slug string.
        """
        response = llm_slug.invoke([HumanMessage(content=slug_prompt)])
        slug = response.content.strip().replace(" ", "-").lower()
        # Clean up
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        # Remove common type prefixes if LLM put them
        for prefix in ["feat-", "fix-", "chore-", "refactor-", "docs-", "test-"]:
            if slug.startswith(prefix):
                slug = slug[len(prefix):]
                
    except Exception as e:
        print(f"⚠️ Slug generation failed: {e}. Using fallback.")
        slug = re.sub(r'[^a-z0-9]+', '-', lower_header).strip('-')
        # Remove common prefixes
        clean_prefixes = ["bug-", "fix-", "feat-", "feature-", "refactor-", "docs-", "test-", "chore-"]
        for prefix in clean_prefixes:
            if slug.startswith(prefix):
                slug = slug[len(prefix):]
                break
        # Fallback limit to 3 words
        slug = "-".join(slug.split("-")[:3])

    branch_name = f"{branch_type}/{slug}-{timestamp}"

    # Allow user override
    print(f"🤖 Proposed Branch Name: {branch_name}")
    custom_branch = input("👉 Press Enter to confirm, or type a custom branch name: ").strip()
    if custom_branch:
        branch_name = custom_branch

    # Construct Commit Message
    type_emoji_map = {
        "fix": "🐛 fix",
        "feat": "✨ feat",
        "refactor": "♻️ refactor",
        "docs": "📚 docs",
        "test": "✅ test",
        "chore": "🔧 chore"
    }
    commit_prefix = type_emoji_map.get(branch_type, "🔧 chore")
    
    scope = ""
    affected_files = list(state.get('changes', {}).keys())
    if any(f.startswith("client") or f.endswith(".cpp") or f.endswith(".h") for f in affected_files):
        scope = "(client)"
    elif any(f.startswith("internal") or f.startswith("cmd") or f.endswith(".go") for f in affected_files):
        scope = "(server)"
    elif any("Luma" in f or f.endswith(".py") for f in affected_files):
        scope = "(luma)"
        
    if not scope:
        if "client" in lower_header: scope = "(client)"
        elif "server" in lower_header: scope = "(server)"
        elif "luma" in lower_header: scope = "(luma)"

    commit_message = f"{commit_prefix}{scope}: {task_title}"
    
    try:
        # 2. Git Operations
        print(f"🌿 Creating/Switching branch: {branch_name}")
        # Check if branch exists locally
        try:
             subprocess.run(["git", "rev-parse", "--verify", branch_name], cwd=TARGET_DIR, check=True, capture_output=True)
             # Branch exists, checkout it
             print(f"   Branch '{branch_name}' exists. Switching...")
             subprocess.run(["git", "checkout", branch_name], cwd=TARGET_DIR, check=True)
        except subprocess.CalledProcessError:
             # Branch does not exist, create it
             print(f"   Branch '{branch_name}' does not exist. Creating...")
             subprocess.run(["git", "checkout", "-b", branch_name], cwd=TARGET_DIR, check=True)
        
        print("📦 Committing changes...")
        subprocess.run(["git", "add", "."], cwd=TARGET_DIR, check=True)
        subprocess.run(["git", "commit", "-m", commit_message], cwd=TARGET_DIR, check=True)
        
        print(f"⬆️ Pushing to origin/{branch_name}...")
        subprocess.run(["git", "push", "origin", branch_name], cwd=TARGET_DIR, check=True)
        
        # 3. Create PR
        print(f"📝 Creating Pull Request for {repo_name}...")
        
        # Prepare Body using Template
        body = f"Auto-generated by Luma.\n\nTask: {state['task']}\n\nTimestamp: {timestamp}"
        # Prepare Body using Template
        body = f"Auto-generated by Luma.\n\nTask: {state['task']}\n\nTimestamp: {timestamp}"
        
        # Search for template in TARGET_DIR and Parent Dir (Repo Root)
        possible_templates = [
            os.path.join(TARGET_DIR, ".github", "pull_request_template.md"),
            os.path.join(os.path.dirname(os.path.abspath(TARGET_DIR)), ".github", "pull_request_template.md")
        ]
        template_path = next((p for p in possible_templates if os.path.exists(p)), None)
        
        if template_path:
            print("   📄 Using PR Template...")
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    template = f.read()
                
                # 1. Fill Summary
                summary = f"Auto-generated by Luma. Implementation for: {task_title}"
                body = template.replace("<!-- Brief description of changes -->", summary)
                
                # 2. Fill Changes
                import textwrap
                description = textwrap.dedent(state['task']).strip()
                body = body.replace("<!-- Describe what changed -->", description)

                # 2.5 Add Test Suggestions
                if state.get("test_suggestions"):
                    test_section = f"\n\n## 🧪 Suggested Test Cases\n{state['test_suggestions']}"
                    body += test_section
                
                # 3. Detect Type
                lower_task = state['task'].lower()
                if "bug" in lower_task or "fix" in lower_task:
                    body = body.replace("- [ ] 🐛 Bug fix", "- [x] 🐛 Bug fix")
                if "feat" in lower_task or "add" in lower_task:
                    body = body.replace("- [ ] ✨ New feature", "- [x] ✨ New feature")
                if "refactor" in lower_task:
                    body = body.replace("- [ ] 🔧 Refactoring", "- [x] 🔧 Refactoring")
                    
                # 4. Link Issues
                import re
                # Pattern to find issue number from "Review Issue Link: .../issues/123"
                issue_match = re.search(r'issues/(\d+)', state['task'])
                if issue_match:
                    issue_num = issue_match.group(1)
                    # Replace the first occurrence (usually "Closes #...")
                    body = body.replace("<!-- issue number -->", issue_num, 1) 
                    
            except Exception as e:
                print(f"   ⚠️ Error reading template: {e}")
        
        # Check for existing PR
        print(f"🔍 Checking for existing PR for {branch_name}...")
        existing_pr = get_open_pr(repo_name, branch_name)
        
        pr_url = None
        if existing_pr:
             print(f"⚠️ Found existing PR #{existing_pr['number']}: {existing_pr['html_url']}")
             print("🔄 Updating existing PR...")
             pr_url = update_pull_request(repo_name, existing_pr['number'], title=commit_message, body=body)
        else:
             pr_url = create_pull_request(
                repo_name=repo_name,
                title=commit_message,
                body=body,
                head_branch=branch_name,
                base_branch="main" 
             )
        
        if pr_url:
            print(f"🎉 Success! PR is ready: {pr_url}")
            
            # --- Update Issue Status to 'In Review' ---
            if state.get('issue_data'):
                print("🔄 Updating Issue Status to 'In Review'...")
                update_issue_status(state['issue_data'], "In Review")
            
    except Exception as e:
        print(f"⚠️ Publisher Error: {e}")
        # Try to return to main?
        # subprocess.run(["git", "checkout", "main"], cwd=TARGET_DIR)
        
    return {}

# --- 3. Build Graph (เชื่อมต่อสายงาน) ---
workflow = StateGraph(AgentState)

# เพิ่ม Node
workflow.add_node("Coder", coder_agent)
workflow.add_node("Reviewer", reviewer_agent)
workflow.add_node("Tester", tester_agent)
workflow.add_node("Docs", docs_agent)
workflow.add_node("Approver", human_approval_agent)
workflow.add_node("Writer", file_writer)
workflow.add_node("Publisher", publisher_agent)

# เชื่อมเส้น
workflow.set_entry_point("Coder")
workflow.add_edge("Coder", "Reviewer")
workflow.add_edge("Reviewer", "Tester")

# Conditional Edge 1: Tester Logic
workflow.add_conditional_edges(
    "Tester",
    should_continue,
    {
        "retry": "Coder",
        "pass": "Docs"
    }
)

workflow.add_edge("Docs", "Approver")

# Conditional Edge 2: Approval Logic
workflow.add_conditional_edges(
    "Approver",
    approval_gate,
    {
        "yes": "Writer",
        "no": END
    }
)

workflow.add_edge("Writer", "Publisher")
workflow.add_edge("Publisher", END)

# Compile
app = workflow.compile()

# --- 4. Execution (สั่งงาน!) ---
if __name__ == "__main__":
    import argparse
    import sys
    
    # Try to import GitHub Fetcher
    try:
        from github_fetcher import fetch_issues, select_issue, convert_to_task, create_pull_request, update_issue_status, get_open_pr, update_pull_request
    except ImportError:
        fetch_issues = None
        print("⚠️ github_fetcher.py not found. GitHub features disabled.")

    parser = argparse.ArgumentParser(description="Luma AI Architect")
    parser.add_argument("--github", action="store_true", help="Fetch task from GitHub Issues")
    parser.add_argument("--repo", type=str, default="oatrice/Tetris-Battle", help="GitHub Repository (user/repo)")
    args = parser.parse_args()

    # Default Mission: Check Project Status (Fallback)
    default_task = """
    Task: Check Project Configuration
    
    1. Read `package.json` to understand the current project dependencies.
    2. Read `vite.config.ts` to check build configuration.
    """
    
    initial_state = {
        "task": default_task,
        "iterations": 0,
        "changes": {},
        "test_errors": "",
        "source_files": [
            "package.json",
            "vite.config.ts"
        ],
        "repo": args.repo,
        "issue_data": {}
    }

    def get_ai_advice(issues):
        if not issues:
            return
            
        summary = "\n".join([f"- Issue #{i['number']}: {i['title']}\n  Body: {(i.get('body') or '')[:200]}..." for i in issues])
        
        prompt = f"""
        You are a Technical Project Manager. 
        Analyze the following GitHub Issues (Priority Tasks) and suggest the execution order.
        
        Criteria:
        1. Dependency (Is there a task that blocks others?)
        2. Difficulty (Easy tasks to get momentum vs Hard tasks)
        3. Impact
        
        Tasks:
        {summary}
        
        Output:
        Provide a short recommendation (2-3 sentences per task) on why it should be done now or later.
        Be concise. Use bullet points.
        """
        
        llm = get_llm(temperature=0.5)
        response = llm.invoke([HumanMessage(content=prompt)])
        print("\n🔎 AI Recommendation:\n" + response.content)

    # --- Interactive Menu System ---
    if args.github and fetch_issues:
        while True:
            print("\n==============================")
            print("🤖 Luma AI Architect - Main Menu")
            print("==============================")
            # Check draft existence for UI hint
            draft_path = os.path.join(TARGET_DIR, ".pr_draft.json")
            draft_hint = " 📄 (Resume Draft)" if os.path.exists(draft_path) else ""

            print("1. 📥 Select Next Issue (Start Coding)")
            print("2. 🚀 Create Pull Request (Deploy)")
            print("3. 🧐 Code Review (Local)")
            print("4. 📝 Update Docs (Standalone)")
            print("0. ❌ Exit")
            
            choice = input("\nSelect Option: ").strip()
            
            if choice == "1":
                # --- Flow 1: Issue Selection ---
                print(f"📡 Fetching issues from {args.repo}...")
                issues = fetch_issues(args.repo)
                
                selected_issue = select_issue(issues, ai_advisor=get_ai_advice)
                
                if selected_issue:
                    print(f"🚀 Starting Task: {selected_issue['title']}")
                    
                    print("🔄 Updating Issue Status to 'In Progress'...")
                    update_issue_status(selected_issue, "In Progress")
                    
                    initial_state["task"] = convert_to_task(selected_issue)
                    initial_state["issue_data"] = selected_issue
                    
                    # Run Workflow
                    final_state = app.invoke(initial_state)
                    print("✅ Simulation Complete.")
                    
                    # Ask to loop back?
                    # break # for now break to return to menu or exit? 
                    # Let's loop back to menu
                else:
                    print("❌ No issue selected.")

            elif choice == "2":
                # --- Flow 2: Create PR ---
                print(f"\n🚀 Preparing to Create PR for {TARGET_DIR}...")
                
                # 1. Get Current Branch
                try:
                    res = subprocess.run(["git", "branch", "--show-current"], cwd=TARGET_DIR, capture_output=True, text=True)
                    current_branch = res.stdout.strip()
                    if not current_branch:
                        print("❌ Error: Not in a git repository or detached head.")
                        continue
                        
                    def generate_suggestions():
                        print("📊 Analyzing local changes for suggestions...")
                        # Get diff summary (staged + unstaged)
                        status_cmd = ["git", "status", "--short"] 
                        status_res = subprocess.run(status_cmd, cwd=TARGET_DIR, capture_output=True, text=True)
                        
                        # Get diff stat
                        try:
                            diff_stat = subprocess.check_output(["git", "diff", "--stat"], cwd=TARGET_DIR, text=True).strip()
                            diff_cached_stat = subprocess.check_output(["git", "diff", "--cached", "--stat"], cwd=TARGET_DIR, text=True).strip()
                        except:
                            diff_stat = ""
                            diff_cached_stat = ""

                        # Get actual diff content (Truncated)
                        try:
                            diff_content = subprocess.check_output(["git", "diff"], cwd=TARGET_DIR, text=True).strip()
                            diff_cached_content = subprocess.check_output(["git", "diff", "--cached"], cwd=TARGET_DIR, text=True).strip()
                        except:
                            diff_content = ""
                            diff_cached_content = ""

                        # Combine and truncate
                        full_diff = (diff_content + "\n" + diff_cached_content)[:3000]

                        # Get recent log (last 5 commits)
                        log_cmd_quick = ["git", "log", "-n", "5", "--pretty=format:%s"]
                        log_res_quick = subprocess.run(log_cmd_quick, cwd=TARGET_DIR, capture_output=True, text=True)
                        
                        changes_context = f"""
                        Git Status:
                        {status_res.stdout}
                        
                        Modified Files (Stat):
                        {diff_stat}
                        {diff_cached_stat}

                        Code Changes (Diff - Truncated):
                        {full_diff}

                        Recent Logs:
                        {log_res_quick.stdout}
                        """
                        
                        try:
                            llm_suggest = get_llm(temperature=0.7)
                            suggest_prompt = f"""
                            Based on the Code Changes above, suggest 3 suitable git branch names.
                            
                            Context:
                            {changes_context}
                            
                            Instructions:
                            1. Analyze the *Code Changes* to identify the specific feature or fix (e.g., 'renderer-fix', 'ghost-piece-logic').
                            2. Format: <type>/<concise-slug>
                            3. Types: feat, fix, refactor, chore, docs, test.
                            4. Slug: kebab-case, 2-4 words. Avoid generic names like 'update-file'.
                            
                            Examples:
                            - Diff shows added tests -> test/offline-mode-cases
                            - Diff shows UI color change -> feat/ui-dark-theme-colors
                            
                            Return ONLY the 3 names, one per line. No numbering.
                            """
                            resp = llm_suggest.invoke([HumanMessage(content=suggest_prompt)])
                            return [s.strip() for s in resp.content.strip().split('\n') if s.strip()]
                        except Exception as e:
                            print(f"⚠️ Failed to generate suggestions: {e}")
                            return []

                    def get_user_branch_choice():
                        # Call LLM only here
                        suggestions = generate_suggestions()
                        
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

                    # If on main, offer to create feature branch
                    if current_branch in ['main', 'master']:
                        print(f"⚠️ You are currently on '{current_branch}'.")
                        create_new = input("🌿 Do you want to create a new branch? (y/N): ").lower()
                        if create_new == 'y':
                            new_branch = get_user_branch_choice()
                            if new_branch:
                                try:
                                    subprocess.run(["git", "checkout", "-b", new_branch], cwd=TARGET_DIR, check=True)
                                    current_branch = new_branch
                                    print(f"✅ Switched to new branch: {current_branch}")
                                except subprocess.CalledProcessError as e:
                                    print(f"❌ Failed to create branch: {e}")
                                    continue
                        
                    print(f"🌿 Current Branch: {current_branch}")

                    # If NOT on main, offer to rename (e.g. to match changes)
                    if current_branch not in ['main', 'master']:
                        rename_opt = input(f"✏️  Do you want to rename '{current_branch}'? (y/N): ").lower()
                        if rename_opt == 'y':
                             new_name = get_user_branch_choice()
                             if new_name:
                                 try:
                                     subprocess.run(["git", "branch", "-m", new_name], cwd=TARGET_DIR, check=True)
                                     current_branch = new_name
                                     print(f"✅ Renamed to: {current_branch}")
                                 except subprocess.CalledProcessError as e:
                                     print(f"❌ Failed to rename: {e}")
                    
                    # Confirm
                    confirm = input(f"Create PR for '{current_branch}' -> 'main'? (y/N): ").lower()
                    if confirm != 'y':
                        continue
                        
                    
                    # --- OPTIONAL: Run Docs Agent before PR ---
                    run_docs = input("\n📚 Do you want to update docs & versioning before PR? (y/N): ").lower()
                    if run_docs == 'y':
                        print("📚 Running Docs Agent (Pre-PR Check)...")
                        try:
                             # 1. Reuse existing docs_agent logic via a focused state
                             doc_state = initial_state.copy()
                             doc_state["task"] = f"Update documentation for PR: {current_branch}"
                             doc_state["skip_coder"] = True # We only want docs
                             
                             # Run Docs Node
                             doc_result = docs_agent(doc_state)
                             
                             if doc_result and doc_result.get('changes'):
                                 changes = doc_result['changes']
                                 print(f"   📝 Docs Agent proposes updates to: {list(changes.keys())}")
                                 
                                 # Auto-commit these changes if user agrees
                                 if input("   💾 Commit documentation updates now? (Y/n): ").lower() not in ['n', 'no']:
                                     for filename, content in changes.items():
                                         full_path = os.path.join(TARGET_DIR, filename)
                                         with open(full_path, "w", encoding="utf-8") as f:
                                             f.write(content)
                                     
                                     subprocess.run(["git", "add", "."], cwd=TARGET_DIR, check=True)
                                     subprocess.run(["git", "commit", "-m", "docs: update CHANGELOG and version from Luma"], cwd=TARGET_DIR, check=True)
                                     print("   ✅ Docs committed.")
                                 else:
                                     print("   ⏩ Skipping docs commit.")
                        except Exception as e:
                            print(f"   ⚠️ Docs Agent failed in PR flow: {e}")
                    else:
                        print("   ⏩ Skipping Docs Agent.")

                    # 2. Get Diff for Description
                    # 2.3 Check for existing DRAFT
                    draft_file = os.path.join(TARGET_DIR, ".pr_draft.json")
                    title = ""
                    body = ""
                    
                    if os.path.exists(draft_file):
                        print("📄 Found saved PR Draft!")
                        if input("reuse saved draft? (y/N): ").lower() == 'y':
                             try:
                                 with open(draft_file, "r") as f:
                                     data = json.load(f)
                                     title = data.get("title", "")
                                     body = data.get("body", "")
                             except Exception as e:
                                 print(f"⚠️ Failed to load draft: {e}")

                    if not title or not body:
                        # 2.4 Check for Template
                        possible_templates = [
                            os.path.join(TARGET_DIR, ".github", "pull_request_template.md"),
                            os.path.join(os.path.dirname(os.path.abspath(TARGET_DIR)), ".github", "pull_request_template.md")
                        ]
                        template_path = next((p for p in possible_templates if os.path.exists(p)), None)
                        
                        template_content = ""
                        if template_path:
                            with open(template_path, "r", encoding="utf-8") as f:
                                template_content = f.read()
                                
                        # 3. Generate Content with Enhanced Context
                        print("📊 Analyzing changes for description...")
                        
                        llm = get_llm(purpose="code")
                        
                        # Get Commit Logs & Diff
                        log_cmd = ["git", "log", "origin/main..HEAD", "--pretty=format:%s%n%b"]
                        log_res = subprocess.run(log_cmd, cwd=TARGET_DIR, capture_output=True, text=True)
                        commit_logs = log_res.stdout.strip()
                        
                        # Use full diff to get content changes, not just names
                        diff_cmd = ["git", "diff", "origin/main...HEAD"] 
                        diff_res = subprocess.run(diff_cmd, cwd=TARGET_DIR, capture_output=True, text=True)

                        if template_content:
                            gen_prompt = f"""
                            You are an expert developer creating a Pull Request.
                            
                            **CRITICAL INSTRUCTION**: 
                            The PR Title MUST derive directly from the branch name: '{current_branch}'.
                            Example: if branch is 'feat/add-login', Title should be 'feat: Add Login Functionality'.
                            
                            FOCUS: Describe ONLY the changes related to '{current_branch}'. 
                            Ignore unrelated history or large file additions if they are not central to this specific feature/fix.
                            
                            CONTEXT:
                            Target Branch: {current_branch} -> main
                            
                            COMMITS (User Intent):
                            {commit_logs}
                            
                            **CODE DIFF (First 6000 chars)**:
                            {diff_res.stdout[:6000]}
                            
                            TEMPLATE:
                            {template_content}
                            
                            INSTRUCTIONS:
                            1. **Title**: Generate a conventional commit title based on '{current_branch}'.
                            2. **Body**: Fill the template with details from the commits and file changes. Focus on WHAT changed and WHY.
                            3. Return ONLY the filled markdown.
                            4. Start output with "TITLE: <Suggested Title>".
                            """
                            print("\n[DEBUG] Sending to LLM:")
                            print(f"[DEBUG] Commits:\n{commit_logs}\n")
                            print(f"[DEBUG] Diff (First 500 chars):\n{diff_res.stdout[:500]}\n...")
                            
                            # Save Full Context to Log File
                            log_path = os.path.join(TARGET_DIR, "luma_pr_context.log")
                            try:
                                with open(log_path, "w", encoding="utf-8") as f:
                                    f.write("=== Luma PR Generation Context ===\n")
                                    f.write(f"Updated: {os.getcwd()}\n\n")
                                    f.write("--- COMMITS ---\n")
                                    f.write(commit_logs)
                                    f.write("\n\n--- GIT DIFF ---\n")
                                    f.write(diff_res.stdout)
                                print(f"💾 Full PR Context log saved to: {log_path}")
                            except Exception as e:
                                print(f"⚠️ Failed to save log file: {e}")
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
                        title = f"feat: {current_branch}" # fallback
                        body = content
                        
                        lines = content.split('\n')
                        first_line = lines[0].strip()
                        if first_line.startswith("TITLE:"):
                             title = first_line.replace("TITLE:", "").strip()
                             # Remove title from body
                             body = "\n".join(lines[1:]).strip()

                        # SAVE DRAFT
                        with open(draft_file, "w") as f:
                            json.dump({"title": title, "body": body}, f)
                        print(f"💾 Draft saved to {draft_file}")
                    
                    print(f"\n📝 Proposed PR:\nTitle: {title}\nBody:\n{body[:200]}...\n")

                    # --- Luma Reviewer: Test Suggestions ---
                    print("\n🧪 Luma Reviewer: Analyzing for missing tests...")
                    try:
                        test_prompt = f"""
                        Analyze the following code changes and suggest 3-5 critical test cases that are missing or should be added.
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
                    except Exception as e:
                        print(f"⚠️ Could not generate test suggestions: {e}")

                    # 4. Create PR
                    if input("Proceed to Open PR? (y/N): ").lower() == 'y':
                         try:
                             print(f"⬆️ Pushing branch '{current_branch}' to origin...")
                             subprocess.run(["git", "push", "origin", current_branch], cwd=TARGET_DIR, check=True)
                         except subprocess.CalledProcessError as e:
                             print(f"❌ Failed to push branch: {e}")
                             continue

                         # Check for existing PR
                         existing_pr = get_open_pr(args.repo, current_branch)
                         url = None
                         
                         if existing_pr:
                             print(f"⚠️ Found existing PR #{existing_pr['number']}: {existing_pr['html_url']}")
                             if input("🔄 Update existing PR description? (y/N): ").lower() == 'y':
                                 url = update_pull_request(args.repo, existing_pr['number'], title, body)
                             else:
                                 print("⏩ Skipping PR update.")
                                 continue
                         else:
                             url = create_pull_request(args.repo, title, body, current_branch, "main")
                             
                         if url: 
                             print(f"✅ PR Created: {url}")
                             # CLEANUP
                             if os.path.exists(draft_file):
                                 os.remove(draft_file)
                         else:
                             print(f"⚠️ PR Creation failed. Draft preserved at {draft_file}")
                         
                except Exception as e:
                    print(f"❌ Error in PR Flow: {e}")

            elif choice == "3":
                 print("\n🧐 Local Code Reviewer")
                 
                 # 1. Select Files
                 changes = {}
                 
                 print("1. Review Changes (origin/main -> HEAD + Dirty)")
                 print("2. Review Specific File")
                 review_mode = input("Select Mode [1]: ").strip() or "1"
                 
                 if review_mode == "1":
                     # Get modified files from git
                     try:
                         files = set()
                         
                         # 1. Commits vs origin/main
                         print("   📡 Configuring git scope (origin/main...HEAD)...")
                         cmd_commits = ["git", "diff", "--name-only", "--relative", "origin/main...HEAD"]
                         res_commits = subprocess.run(cmd_commits, cwd=TARGET_DIR, capture_output=True, text=True)
                         if res_commits.returncode == 0:
                             files.update([f.strip() for f in res_commits.stdout.split('\n') if f.strip()])
                         else:
                             print(f"   ⚠️ Could not diff against origin/main (using local only).")

                         # 2. Local Dirty (Staged + Unstaged)
                         cmd_dirty = ["git", "diff", "--name-only", "--relative", "HEAD"]
                         res_dirty = subprocess.run(cmd_dirty, cwd=TARGET_DIR, capture_output=True, text=True)
                         files.update([f.strip() for f in res_dirty.stdout.split('\n') if f.strip()])
                         
                         # 3. Untracked
                         cmd_untracked = ["git", "ls-files", "--others", "--exclude-standard"]
                         res_untracked = subprocess.run(cmd_untracked, cwd=TARGET_DIR, capture_output=True, text=True)
                         files.update([f.strip() for f in res_untracked.stdout.split('\n') if f.strip()])
                         
                         file_list = list(files)
                         if not file_list:
                             print("✅ No changes found (Clean vs origin/main).")
                             continue
                             
                         print(f"   🔎 Found {len(file_list)} changed files.")
                         
                         # Limit files (Review limit)
                         if len(file_list) > 30:
                              print(f"⚠️ Too many files ({len(file_list)}). Reviewing top 10.")
                              file_list = file_list[:10]
                              
                         for rel_path in file_list:
                             full_path = os.path.join(TARGET_DIR, rel_path)
                             # Only review text files that exist
                             if os.path.exists(full_path) and os.path.isfile(full_path):
                                 # Basic binary check extension
                                 if rel_path.endswith(('.png', '.bg', '.jpg', '.ico', '.pdf')):
                                     continue
                                     
                                 with open(full_path, 'r', encoding='utf-8') as f:
                                     changes[rel_path] = f.read()
                                     
                     except Exception as e:
                         print(f"❌ Error reading git status: {e}")
                         continue
                         
                 elif review_mode == "2":
                     target_file = input("Enter relative file path: ").strip()
                     full_path = os.path.join(TARGET_DIR, target_file)
                     if os.path.exists(full_path):
                         with open(full_path, 'r', encoding='utf-8') as f:
                             changes[target_file] = f.read()
                     else:
                         print(f"❌ File not found: {target_file}")
                         continue
                 
                 if not changes:
                     print("❌ No content to review.")
                     continue
                     
                 # 2. Run Reviewer Agent
                 print(f"🚀 Running Reviewer on {list(changes.keys())}...")
                 
                 # Mock a state
                 review_state = {
                     "task": "Review local code changes for bugs, security issues, and best practices.",
                     "changes": changes,
                     "iterations": 0,
                     "test_errors": ""
                 }
                 
                 result = reviewer_agent(review_state)
                 
                 if result.get("code_content"):
                     print("\n📝 Reviewer Feedback:")
                     print("--------------------------------------------------")
                     print(result["code_content"])
                     print("--------------------------------------------------")
                 
                 print("\n✅ Review Complete.")

            elif choice == "4":
                # --- Flow 4: Update Docs Only ---
                print("📝 Starting Documentation Update...")
                print("   This will check for local Git changes and update CHANGELOG.md + package.json")
                
                confirm = input("   Continue? (Y/n): ").strip().lower()
                if confirm not in ['n', 'no']:
                    doc_state = initial_state.copy()
                    doc_state["task"] = "Update all documentation based on local file changes. Especially .md or markdown files"
                    doc_state["skip_coder"] = True
                    
                    final_state = app.invoke(doc_state)
                    print("✅ Documentation Update Complete.")

            elif choice == "0":
                print("👋 Exiting.")
                break
            else:
                print("❌ Invalid option.")
    else:
        # Fallback for non-github mode (CLI args only)
        # Run Simulation
        final_state = app.invoke(initial_state)
        print("✅ Simulation Complete.")
