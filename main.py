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
OPENROUTER_MODEL = "qwen/qwen3-coder:free"

# Gemini Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

TARGET_DIR = "../Tetris-Battle"

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

# --- 1.5 Helper Functions ---
def get_llm(temperature=0.7):
    """Factory function to get the configured LLM instance"""
    if LLM_PROVIDER == "openrouter":
        print(f"🔌 Using OpenRouter ({OPENROUTER_MODEL})...")
        return ChatOpenAI(
            model=OPENROUTER_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
            max_tokens=4000
        )
    elif LLM_PROVIDER == "gemini":
        print(f"🔌 Using Gemini ({GEMINI_MODEL})...")
        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL, 
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
    llm = get_llm(temperature=0.7)
    
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
    target_files = [] 
    if changes:
        target_files = list(changes.keys())
        print(f"🧐 Reviewing code for: {target_files}...")
    else:
        print(f"🧐 Reviewing code for: New Generated Code...")
    
    # Initialize LLM based on Provider
    llm = get_llm(temperature=0)
    
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
            
    return {"code_content": content}

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
    
    # ถ้าไม่มี Error หรือครบโควต้าแล้ว -> ไปต่อ Approver (Pass)
    return "pass"

# --- 3. Define Human Approval (การตรวจสอบจาก User) ---
import difflib
import webbrowser

def human_approval_agent(state: AgentState):
    """(Mock) ให้ User ตรวจสอบโค้ดก่อนบันทึก"""
    print("\n--- ✋ Approval Request for " + str(list(state['changes'].keys())) + " ---")
    
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

    user_input = input("Approve changes? (y/n): ").strip().lower()
    
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
        from github_fetcher import create_pull_request, update_issue_status
    except ImportError:
        print("⚠️ GitHub tools not found. Skipping PR.")
        return {}

    # 1. Generate Branch Name
    import time
    timestamp = int(time.time())
    branch_name = f"luma-fix-{timestamp}"
    
    repo_name = state.get("repo", "oatrice/Tetris-Battle") # Fallback
    task_title = state['task'].split('\n')[0][:50].strip()
    
    try:
        # 2. Git Operations
        print(f"🌿 Creating branch: {branch_name}")
        # Note: We assume we are on main/master and clean. 
        # In prod, we should git checkout main && git pull first.
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=TARGET_DIR, check=True)
        
        print("📦 Committing changes...")
        subprocess.run(["git", "add", "."], cwd=TARGET_DIR, check=True)
        subprocess.run(["git", "commit", "-m", f"Luma Auto-Fix: {task_title}"], cwd=TARGET_DIR, check=True)
        
        print(f"⬆️ Pushing to origin/{branch_name}...")
        subprocess.run(["git", "push", "origin", branch_name], cwd=TARGET_DIR, check=True)
        
        # 3. Create PR
        print(f"📝 Creating Pull Request for {repo_name}...")
        
        # Prepare Body using Template
        body = f"Auto-generated by Luma.\n\nTask: {state['task']}\n\nTimestamp: {timestamp}"
        template_path = os.path.join(TARGET_DIR, ".github", "pull_request_template.md")
        
        if os.path.exists(template_path):
            print("   📄 Using PR Template...")
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    template = f.read()
                
                # 1. Fill Summary
                summary = f"Auto-generated by Luma. Implementation for: {task_title}"
                body = template.replace("<!-- Brief description of changes -->", summary)
                
                # 2. Fill Changes
                description = state['task']
                body = body.replace("<!-- Describe what changed -->", description)
                
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
        
        pr_url = create_pull_request(
            repo_name=repo_name,
            title=f"Luma Fix: {task_title}",
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
        "pass": "Approver"
    }
)

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
        from github_fetcher import fetch_issues, select_issue, convert_to_task, create_pull_request, update_issue_status
    except ImportError:
        fetch_issues = None
        print("⚠️ github_fetcher.py not found. GitHub features disabled.")

    parser = argparse.ArgumentParser(description="Luma AI Architect")
    parser.add_argument("--github", action="store_true", help="Fetch task from GitHub Issues")
    parser.add_argument("--repo", type=str, default="oatrice/Tetris-Battle", help="GitHub Repository (user/repo)")
    args = parser.parse_args()

    # Default Mission: High Contrast Preview Color (Fallback)
    default_task = """
    Feature: Add Pause and Persistent Restart Buttons

    1. Update `client/game.h`:
       - Add `bool isPaused` member variable to `Game` class (initialize to false).
       - Add `Button btnPause` to `Game` class.

    2. Update `client/game.cpp`:
       - In `Game::Game()` (Constructor):
         - Initialize `isPaused` to false.
         - Update `btnRestart` position to be on the right side of the board (UI Area), e.g., below Next Piece preview. Size: 100x40.
         - Initialize `btnPause` position to be below `btnRestart`. Size: 100x40. Text: "Pause". Color: GOLD.
       
       - In `Game::ResetGame()`:
         - Set `isPaused` to false.
         - Set `logic.isGameOver` to false (already done in logic.Reset, but ensure Game state is clean).

       - In `Game::HandleInput()`:
         - Add logic for `btnPause`: If clicked, toggle `isPaused` state.
         - Add logic for `btnRestart`: If clicked, call `ResetGame()`.
         - IMPORTANT: If `isPaused` is true, ignore other game inputs (movement, rotation), BUT allow `btnPause` and `btnRestart` to work.

       - In `Game::Update()`:
         - If `isPaused` is true, do NOT update `gravityTimer` or call `logic.Tick()`. Return early.

       - In `Game::Draw()`:
         - Draw `btnRestart` and `btnPause` always (not just on Game Over).
         - If `isPaused` is true:
           - Draw a semi-transparent overlay over the board.
           - Draw "PAUSED" text in the center.
    """
    
    initial_state = {
        "task": default_task,
        "iterations": 0,
        "changes": {},
        "test_errors": "",
        "source_files": [
            "client/game.h",
            "client/game.cpp"
        ],
        "repo": args.repo,
        "issue_data": {}
    }

    def get_ai_advice(issues):
        if not issues:
            return
            
        summary = "\n".join([f"- Issue #{i['number']}: {i['title']}\n  Body: {i['body'][:200]}..." for i in issues])
        
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

    if args.github and fetch_issues:
        print(f"📡 Fetching issues from {args.repo}...")
        issues = fetch_issues(args.repo)
        
        # Pass the advisor function
        selected_issue = select_issue(issues, ai_advisor=get_ai_advice)
        
        if selected_issue:
            print(f"🚀 Starting Task: {selected_issue['title']}")
            
            # --- Update Issue Status to 'In Progress' ---
            print("🔄 Updating Issue Status to 'In Progress'...")
            # Note: We need to import update_issue_status or define it locally if we want to use it here.
            # We already imported it.
            if fetch_issues:
                 update_issue_status(selected_issue, "In Progress")
            
            initial_state["task"] = convert_to_task(selected_issue)
            initial_state["issue_data"] = selected_issue
            # Todo: dynamic source file detection could go here
        else:
            print("❌ No issue selected. Using default task.")
            
    # Run Simulation
    final_state = app.invoke(initial_state)
    print("✅ Simulation Complete.")
