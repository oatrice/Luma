import os
from dotenv import load_dotenv
from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

# Load environment variables from .env file
load_dotenv()

# --- Config ---

# --- Config ---
# ระบุ Path ปลายทางของโปรเจ็ค Tetris
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

# --- 2. Define Nodes (ขั้นตอนการทำงาน) ---

def coder_agent(state: AgentState):
    """ทำหน้าที่เป็น Go Expert เขียนโค้ดตามคำสั่ง"""
    print(f"🤖 Luma is thinking about: {state['task']}...")
    
    # (Note: For now, Coder still outputs single file logic. 
    #  To fully utilize multi-file, we need to update Coder prompt to return JSON/Multiple files.
    #  But for this step, we just prepare the infrastructure.)
    
    # ใช้ Gemini แทน OpenAI
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    
    # Construct Prompt
    prompt_content = state['task']
    
    # ถ้ามี Errors จาก Tester ให้เปลี่ยนโหมดเป็น Repair
    if state.get('test_errors') and state.get('test_errors') != "":
        print(f"🔧 Fixing bugs (Attempt {state.get('iterations', 1)})...")
        prompt_content = f"""
        Original Task: {state['task']}
        
        The previous code you wrote failed the tests.
        
        FAILED CODE:
        {state['code_content']}
        
        ERROR LOGS:
        {state['test_errors']}
        
        Please rewrite the code to fix these errors. Ensure all imports are correct.
        Output ONLY the full corrected code, no markdown block.
        """
    
    messages = [
        SystemMessage(content="You are a Senior Go (Golang) Developer. Write clean, working code. Output ONLY the code, no markdown block."),
        HumanMessage(content=prompt_content)
    ]
    
    response = llm.invoke(messages)
    # Forward compatibility: If Coder produced single file, wrap in changes check later
    return {"code_content": response.content}

import subprocess

def reviewer_agent(state: AgentState):
    """(New Node) Reviewer Agent: ตรวจสอบและแก้ไขโค้ด"""
    # For simplicity, Reviewer currently reviews the main 'code_content'. 
    # Multi-file review logic would iterate 'changes'.
    filename = state.get('filename', 'unknown')
    print(f"🧐 Reviewing code for: {filename}...")
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    
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
        
        # 3. Run Go Test
        cmd = ["go", "test", "./..."]
        # Run test in the target directory
        result = subprocess.run(cmd, cwd=TARGET_DIR, capture_output=True, text=True)
        
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
            print("✅ Tester: Tests Passed!")
            return {"test_errors": ""} 
        else:
            print("❌ Tester: Tests Failed!")
            current_iter = state.get("iterations", 0) + 1
            return {
                "test_errors": get_log(result),
                "iterations": current_iter
            }
            
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
    """(New Node) ขออนุมัติจากมนุษย์ (Supports Multi-File Preview)"""
    changes = state.get('changes', {})
    if not changes and state.get('filename'):
        changes = {state['filename']: state['code_content']}
        
    print(f"\n--- ✋ Approval Request for {list(changes.keys())} ---")
    
    for filename, content in changes.items():
        print(f"\n📄 File: {filename}")
        print("-" * 40)
        print("\n".join(content.splitlines()[:15]))
        print("... (Preview truncated) ...")
        print("-" * 40)
    
    try:
        user_input = input(f"Approve save? (y/n): ").strip().lower()
    except EOFError:
        user_input = 'n'

    if user_input == 'y':
        print("✅ User Approved.")
        return {"approved": True}
    else:
        print("⛔ User Rejected/Aborted.")
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
    # โจทย์ 3: Simulation - Add Game Start Logic
    mission = {
        "task": """
        Update 'server.go' to include a 'StartGame' method in GameSession.
        1. Add a boolean field `isStarted` to GameSession struct.
        2. Implement `StartGame()` which sets `isStarted` to true (thread-safe).
        3. IMPORTANT: You must also create/update 'server_test.go' to test this method.
           (Wait... I can only write one file per turn? 
            Okay, for this simulation, just update 'server.go' first. 
            We will assume 'server_test.go' needs to be updated in a separate task or combined if possible.
            Actually, let's ask Coder to put BOTH implementation and test in 'server.go' 
            (using a package test trick) OR just write 'server.go' and I will manually run test that fails).
            
            BETTER: Just update 'server.go'. The existing 'server_test.go' might fail if struct changes?
            No, adding field is non-breaking usually.
            
            Let's force a failure: "Change the ServeHello message to 'Welcome to Tetris'". 
            (Assuming existing test checks for 'Hello from Go server').
        """,
        "filename": "server.go",
        "code_content": "",
        "test_errors": "",
        "iterations": 0
    }
    
    app.invoke(mission)
    print("✅ Simulation Complete.")
