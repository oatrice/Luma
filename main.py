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

# --- 2. Define Nodes (ขั้นตอนการทำงาน) ---

def coder_agent(state: AgentState):
    """ทำหน้าที่เป็น Go Expert เขียนโค้ดตามคำสั่ง"""
    print(f"🤖 Luma is thinking about: {state['task']}...")
    
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
    return {"code_content": response.content}

import subprocess

def reviewer_agent(state: AgentState):
    """(New Node) Reviewer Agent: ตรวจสอบและแก้ไขโค้ด"""
    print(f"🧐 Reviewing code for: {state['filename']}...")
    
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
    # ถ้าเป็นไฟล์ Go แล้วไม่มี package declaration ให้เติมให้
    if state['filename'].endswith(".go"):
        if not content.startswith("package "):
            print(f"⚠️ Auto-Fixing: Added 'package main' to {state['filename']}")
            content = "package main\n\n" + content
            
    return {"code_content": content}

def tester_agent(state: AgentState):
    """(New Node) Tester Agent: รัน Unit Test ตรวจสอบความถูกต้อง"""
    print(f"🧪 Testing code logic for {state['filename']}...")
    
    # เขียนไฟล์ชั่วคราวเพื่อรัน Test
    full_path = os.path.join(TARGET_DIR, state['filename'])
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # Write 'Draft' for testing
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(state['code_content'])
    
    # Run Go Test
    cmd = ["go", "test", "./..."]
    try:
        # Run test in the target directory
        result = subprocess.run(cmd, cwd=TARGET_DIR, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Tester: Tests Passed!")
            return {"test_errors": ""} # Clear previous errors
        else:
            print("❌ Tester: Tests Failed!")
            # Increment iterations
            current_iter = state.get("iterations", 0) + 1
            return {
                "test_errors": result.stderr + "\n" + result.stdout,
                "iterations": current_iter
            }
            # Todo: In future, loop back to Coder with error message
    except Exception as e:
        print(f"⚠️ Tester error: {e}")
        return {"test_errors": str(e)}
        
    return {}

def should_continue(state: AgentState):
    """ตัดสินใจว่าจะไปแก้โค้ดใหม่หรือไปต่อ"""
    errors = state.get('test_errors', "")
    iterations = state.get('iterations', 0)
    
    # ถ้ามี Error และยังวนไม่เกิน 3 รอบ -> กลับไปแก้ (Retry)
    if errors and iterations < 3:
        return "retry"
    
    # ถ้าไม่มี Error หรือครบโควต้าแล้ว -> ไปต่อ (Pass)
    return "pass"

def file_writer(state: AgentState):
    """ทำหน้าที่บันทึกไฟล์ลง Disk"""
    full_path = os.path.join(TARGET_DIR, state['filename'])
    
    print(f"💾 Saving file to: {full_path}")
    
    # ตรวจสอบว่ามีโฟลเดอร์ไหม ถ้าไม่มีให้สร้าง
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(state['code_content'])
        
    return {}

# --- 3. Build Graph (เชื่อมต่อสายงาน) ---
workflow = StateGraph(AgentState)

# เพิ่ม Node
workflow.add_node("Coder", coder_agent)
workflow.add_node("Reviewer", reviewer_agent)
workflow.add_node("Tester", tester_agent)
workflow.add_node("Writer", file_writer)

# เชื่อมเส้น
workflow.set_entry_point("Coder")
workflow.add_edge("Coder", "Reviewer")
workflow.add_edge("Reviewer", "Tester")

# Conditional Edge
workflow.add_conditional_edges(
    "Tester",
    should_continue,
    {
        "retry": "Coder",
        "pass": "Writer"
    }
)

workflow.add_edge("Writer", END)

# Compile
app = workflow.compile()

# --- 4. Execution (สั่งงาน!) ---
if __name__ == "__main__":
    # โจทย์ 2: อัปเกรดเป็น WebSocket Server
    mission = {
        "task": """
        Upgrade the existing Go server to handle WebSocket connections.
        1. Use 'github.com/gorilla/websocket'.
        2. Create a struct `GameSession` (thread-safe with Mutex) to hold state.
        3. Implement a `/ws` endpoint that upgrades HTTP to WebSocket.
        4. When a client connects, print "New Player Connected".
        5. Keep the root `/` handler for "Hello" message (Regression).
        6. In the main function, register both handlers.
        """,
        "filename": "server.go",
        "code_content": ""
    }
    
    app.invoke(mission)
    print("✅ Mission 2 Complete! WebSocket Server upgrade deployed.")
