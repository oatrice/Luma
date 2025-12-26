from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage
from ..state import AgentState
from ..llm import get_llm

def docs_agent(state: AgentState):
    """Docs Agent: Generates/Updates Documentation"""
    
    # 1. Option 4: Update Docs Only
    if state.get("skip_coder"):
        print("📝 Generating Documentation Update...")
        llm = get_llm(temperature=0.3)
        
        # We assume 'task' contains the request (e.g., "Update docs for...")
        # or we look at `issue_data`
        
        prompt = f"""
        Task: {state['task']}
        
        Generate a suitable CHANGELOG.md entry for today ({datetime.now().strftime('%Y-%m-%d')}).
        Format: Markdown.
        """
        
        res = llm.invoke([HumanMessage(content=prompt)])
        return {"code_content": res.content} # Store in code_content for Writer?
        
    return {}
