import os
from langchain_core.messages import HumanMessage
from ..state import AgentState
from ..config import TARGET_DIR

def human_approval_agent(state: AgentState):
    """Human Approval Step"""
    if state.get("skip_coder"):
        return {"approved": True} 

    print("\n✋ Human Approval Required")
    print("Review the changes/plan above.")
    
    # In automatic mode (CI), we might auto-approve.
    # Interactive mode:
    # user_input = input("Approve? (y/n): ")
    # return {"approved": user_input.lower() == 'y'}
    
    # For simulation/mock:
    print("   (Auto-Approving for Simulation)")
    return {"approved": True}

def approval_gate(state: AgentState):
    return "yes" if state.get("approved") else "no"

def file_writer(state: AgentState):
    """Writer: Applies changes to the filesystem"""
    changes = state.get("changes", {})
    if not changes:
        print("writer: No changes to write.")
        # If Logic failed, we might still want to proceed?
        return {}
        
    print(f"💾 Writing {len(changes)} files to {TARGET_DIR}...")
    
    for rel_path, content in changes.items():
        full_path = os.path.join(TARGET_DIR, rel_path)
        
        # Security/Sanity Check
        if ".." in rel_path:
            print(f"⚠️ Skipping suspicious path: {rel_path}")
            continue
            
        dir_name = os.path.dirname(full_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"   ✅ Wrote {rel_path}")
        except Exception as e:
            print(f"   ❌ Failed to write {rel_path}: {e}")
            
    return {}
