
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

task = """
Implement Collision Detection and Piece Locking in 'client/logic.cpp' using TDD.

1. Update 'client/tests/logic_test.cpp':
   - Add a test 'CollisionFloor': Spawn piece, move it to bottom (y=19), try Tick() -> Should NOT move down further.
   - Add a test 'LockPiece': When piece hits bottom and Tick() is called, it should Lock into the Board (Board::GetCell > 0) and Spawn a new piece.

2. Modify 'client/logic.h' & 'client/logic.cpp':
   - Implement 'bool IsValidPosition(Piece p)' to check bounds and existing grid blocks.
   - Update 'Tick()' to check IsValidPosition before moving.
   - If move invalid (hit bottom), call 'LockPiece()' to copy piece to board and 'SpawnPiece()' next.

Constraint:
- Output JSON with keys: "client/tests/logic_test.cpp", "client/logic.h", "client/logic.cpp".
- KEEP existing logic! Only ADD/MODIFY relevant parts.
"""

system_prompt = """You are a Senior Polyglot Developer.
IMPORTANT OUTPUT FORMAT:
You must output a VALID JSON object containing the file paths and their contents.
Example:
{
  "changes": {
    "file.cpp": "..."
  }
}
- Do NOT output markdown blocks (```json).
- ensure strict JSON syntax.
"""

messages = [SystemMessage(content=system_prompt), HumanMessage(content=task)]

print(f"📡 Sending Prompt to gemini-2.5-flash...")
try:
    response = llm.invoke(messages)
    print("\n--- RESPONSE ---")
    print(response.content)
    print("----------------")
except Exception as e:
    print(f"❌ Error: {e}")
