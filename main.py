import os
from dotenv import load_dotenv
from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

# Load environment variables from .env file
load_dotenv()

# --- Config ---

# --- 0. Configuration ---
MODEL_NAME = "gemini-2.0-flash"
TARGET_DIR = "../Tetris-Battle" # Directory เป้าหมายที่ Agent จะเข้าไปเขียนโค้ด

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

# --- 2. Define Nodes (ขั้นตอนการทำงาน) ---

import json

def coder_agent(state: AgentState):
    """ทำหน้าที่เป็น Go/C++ Expert เขียนโค้ดตามคำสั่ง (Multi-file Support)"""
    print(f"🤖 Luma is thinking about: {state['task']}...")
    
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0)
    
    # Construct Prompt
    prompt_content = state['task']
    
    # Error Handling Logic
    if state.get('test_errors'):
        print(f"🔧 Fixing bugs (Attempt {state.get('iterations', 1)})...")
        prompt_content = f"""
        Original Task: {state['task']}
        
        The previous code you wrote failed the tests.
        
        FAILED CODE (See previously gen files):
        {json.dumps(state.get('changes', {}), indent=2)}
        
        ERROR LOGS:
        {state['test_errors']}
        
        Please rewrite the code to fix these errors.
        """
    
    system_prompt = """You are a Senior Polyglot Developer (Go, C++, Python).
    Your goal is to write clean, production-ready code.
    
    IMPORTANT OUTPUT FORMAT:
    You must output a VALID JSON object containing the file paths and their contents.
    Example:
    {
      "changes": {
        "main.go": "package main\\nfunc main() { ... }",
        "main_test.go": "package main\\nfunc TestMain(t *testing.T) { ... }"
      }
    }
    
    - Keys must be relative file paths (e.g., "client/main.cpp").
    - Do NOT output markdown blocks (```json).
    - ensure strict JSON syntax.
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt_content)
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        # Remove markdown if LLM accidentally adds it
        if content.startswith("```json"): content = content[7:]
        if content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]
        
        data = json.loads(content.strip())
        return {"changes": data.get("changes", {}), "code_content": "See changes"}
        
    except json.JSONDecodeError:
        print("⚠️ Error parsing Coder JSON output. Fallback to single file raw string.")
        # Fallback for Backward Compatibility (if inputs were single file)
        # But for 'Initialize Client', we really need JSON.
        return {"code_content": response.content, "changes": {}}
    except Exception as e:
        print(f"⚠️ Coder Error: {e}")
        return {"changes": {}}

import subprocess

def reviewer_agent(state: AgentState):
    """(New Node) Reviewer Agent: ตรวจสอบและแก้ไขโค้ด"""
    # For simplicity, Reviewer currently reviews the main 'code_content'. 
    # Multi-file review logic would iterate 'changes'.
    filename = state.get('filename', 'unknown')
    print(f"🧐 Reviewing code for: {filename}...")
    
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0)
    
    # Prompt สำหรับ Reviewer
    review_prompt = f"""
    Task: {state['task']}
    
    Current Code input:
    {state['code_content']}
    
    Role:
    You are a Senior Code Reviewer for Go (Golang). Your job is to:
    1. Analyze the code for bugs, race conditions, and style issues.
    2. Fix any issues found.
    3. Ensure it strictly follows Go standards.
    4. CRITICAL: The code MUST start with 'package <name>'. If unsure, use 'package main'.
    5. Output ONLY the final, corrected code. Do NOT output markdown ticks (```go).
    """
    
    messages = [
        SystemMessage(content="You are a Senior Code Reviewer. Output ONLY the fixed code. No markdown. Always start with 'package'."),
        HumanMessage(content=review_prompt)
    ]
    
    response = llm.invoke(messages)
    content = response.content.strip()
    
    # --- Heuristic Check ---
    if filename.endswith(".go"):
        if not content.startswith("package "):
            print(f"⚠️ Auto-Fixing: Added 'package main' to {filename}")
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

def human_approval_agent(state: AgentState):
    """(New Node) ขออนุมัติจากมนุษย์ (Supports Multi-File Preview & Drafts)"""
    changes = state.get('changes', {})
    if not changes and state.get('filename'):
        changes = {state['filename']: state['code_content']}
        
    print(f"\n--- ✋ Approval Request for {list(changes.keys())} ---")
    draft_files = []
    
    for filename, content in changes.items():
        # 1. Write Drafts for Review
        full_path = os.path.join(TARGET_DIR, filename)
        draft_path = full_path + ".draft"
        
        try:
            os.makedirs(os.path.dirname(draft_path), exist_ok=True)
            with open(draft_path, "w", encoding="utf-8") as f:
                f.write(content)
            draft_files.append(draft_path)
            
            print(f"📝 Review Draft created: {draft_path}")
            print("-" * 40)
            print("\n".join(content.splitlines()[:10]))
            print(f"... (Open {filename}.draft to see full content) ...")
            print("-" * 40)
        except Exception as e:
            print(f"⚠️ Failed to create draft for {filename}: {e}")
    
    try:
        user_input = input(f"Approve changes? (y/n): ").strip().lower()
    except EOFError:
        user_input = 'n'

    # Cleanup Drafts Logic
    def cleanup_drafts():
        for d in draft_files:
            if os.path.exists(d): 
                os.remove(d)
                
    if user_input == 'y':
        print("✅ User Approved. Applying changes...")
        cleanup_drafts() # Clean up drafts before real writing (or after? doesn't matter much)
        return {"approved": True}
    else:
        print("⛔ User Rejected. Discarding drafts...")
        cleanup_drafts()
        return {"approved": False}

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
        
    return {}

# --- 3. Build Graph (เชื่อมต่อสายงาน) ---
workflow = StateGraph(AgentState)

# เพิ่ม Node
workflow.add_node("Coder", coder_agent)
workflow.add_node("Reviewer", reviewer_agent)
workflow.add_node("Tester", tester_agent)
workflow.add_node("Approver", human_approval_agent)
workflow.add_node("Writer", file_writer)

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

workflow.add_edge("Writer", END)

# Compile
app = workflow.compile()

# --- 4. Execution (สั่งงาน!) ---
if __name__ == "__main__":
    # โจทย์ 5: Basic Gameplay Implementation
    mission = {
        "task": """
        Implement basic Tetris Gameplay in C++.
        
        1. Create 'client/game.h':
           - Class 'Game'
           - Method 'Update()' (handle input later).
           - Method 'Draw()' (render grid and pieces).
           - Member 'int grid[20][10]' (initialize to 0).
           - Define cellSize = 30;
           
        2. Create 'client/game.cpp':
           - Implement 'Draw()': 
             - Draw a background rectangle for the board (DarkGray).
             - Loop 20x10. If grid[row][col] is 0, draw empty cell (Line). If >0, draw filled rectangle (Color).
             - Align board to center of screen.
           
        3. Update 'client/main.cpp':
           - Include "game.h".
           - Create 'Game game;' before loop.
           - Inside loop: game.Update(); game.Draw();
           
        4. Update 'client/CMakeLists.txt':
           - Add 'game.cpp' to add_executable sources.
           - Keep the Policy Fix we added earlier! (Or Luma might revert it if not careful. 
             Actually Luma reads files? No, Coder overwrites if not careful. 
             Tell Coder to KEEP existing policy lines).
             
        Output JSON: { "changes": { "client/game.h": "...", "client/game.cpp": "...", "client/main.cpp": "...", "client/CMakeLists.txt": "..." } }
        """,
        "filename": "client/main.cpp", # Hint
        "changes": {},
        "test_errors": "",
        "iterations": 0
    }
    
    app.invoke(mission)
    print("✅ Simulation Complete.")
