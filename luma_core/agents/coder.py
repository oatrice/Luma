import os
import re
from langchain_core.messages import HumanMessage, SystemMessage
from ..state import AgentState
from ..llm import get_llm
from ..config import TARGET_DIR

def coder_agent(state: AgentState):
    """Doing the functionality of a Go/C++ Expert, writing code based on commands (Multi-file Support)"""
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
