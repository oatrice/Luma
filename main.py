import os
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

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
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0) # ใช้ gpt-4o หรือ gpt-3.5-turbo ก็ได้
    
    messages = [
        SystemMessage(content="You are a Senior Go (Golang) Developer. Write clean, working code. Output ONLY the code, no markdown block."),
        HumanMessage(content=state['task'])
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
workflow.add_node("Writer", file_writer)

# เชื่อมเส้น
workflow.set_entry_point("Coder")
workflow.add_edge("Coder", "Writer")
workflow.add_edge("Writer", END)

# Compile
app = workflow.compile()

# --- 4. Execution (สั่งงาน!) ---
if __name__ == "__main__":
    # โจทย์: สร้าง WebSocket Server ง่ายๆ ด้วย Go
    mission = {
        "task": "Create a simple Golang HTTP server that listens on port 8080 and returns 'Hello from Luma Tetris Server' at root path.",
        "filename": "server.go",
        "code_content": ""
    }
    
    app.invoke(mission)
    print("✅ Mission Complete! Check the Tetris-Battle folder.")
