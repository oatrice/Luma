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

# --- 2. Define Nodes (ขั้นตอนการทำงาน) ---

def coder_agent(state: AgentState):
    """ทำหน้าที่เป็น Go Expert เขียนโค้ดตามคำสั่ง"""
    print(f"🤖 Luma is thinking about: {state['task']}...")
    
    # ใช้ Gemini แทน OpenAI
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    
    messages = [
        SystemMessage(content="You are a Senior Go (Golang) Developer. Write clean, working code. Output ONLY the code, no markdown block."),
        HumanMessage(content=state['task'])
    ]
    
    response = llm.invoke(messages)
    return {"code_content": response.content}

def reviewer_agent(state: AgentState):
    """(New Node) Reviewer Agent: ตรวจสอบและแก้ไขโค้ด"""
    print(f"🧐 Reviewing code for: {state['filename']}...")
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    
    # Prompt สำหรับ Reviewer
    review_prompt = f"""
    Task: {state['task']}
    
    Current Code:
    {state['code_content']}
    
    Role:
    You are a Senior Code Reviewer. Your job is to:
    1. Analyze the code for bugs, race conditions, and style issues.
    2. Fix any issues found.
    3. Ensure it strictly follows Go standards.
    4. Output ONLY the final, corrected code. Do NOT output markdown ticks (```go).
    """
    
    messages = [
        SystemMessage(content="You are a Senior Code Reviewer. Output ONLY the fixed code. No markdown."),
        HumanMessage(content=review_prompt)
    ]
    
    response = llm.invoke(messages)
    return {"code_content": response.content}

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
workflow.add_node("Writer", file_writer)

# เชื่อมเส้น
workflow.set_entry_point("Coder")
workflow.add_edge("Coder", "Reviewer")
workflow.add_edge("Reviewer", "Writer")
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
