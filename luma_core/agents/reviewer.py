import json
from langchain_core.messages import HumanMessage, SystemMessage
from ..state import AgentState
from ..llm import get_llm

def reviewer_agent(state: AgentState):
    """Reviewer Agent: Checks and Modifies Code"""
    # For simplicity, Reviewer currently reviews the main 'code_content'. 
    # Multi-file review logic would iterate 'changes'.
    changes = state.get('changes', {})
    
    # Check for skip flag
    if not changes and state.get("skip_coder"):
        print("⏩ Skipping Reviewer (Docs Only Mode)...")
        return {"test_suggestions": ""}

    target_files = [] 
    if changes:
        target_files = list(changes.keys())
        print(f"🧐 Reviewing code for: {target_files}...")
    else:
        print(f"🧐 Reviewing code for: New Generated Code...")
    
    # Initialize LLM based on Provider
    llm = get_llm(temperature=0, purpose="code")
    
    # Determine primary language from first file
    primary_file = target_files[0] if target_files else "unknown.py"
    
    # Prompt for Reviewer
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
            # This logic might need to be smarter, updating 'changes' dict directly
            # For now, we assume this heuristic was for single-file content.
            # We log it but don't break dict structure.
            print(f"⚠️ Auto-Fixing: Added 'package main' to {primary_file} (Heuristic skipped for multi-file)")
            
    # --- 4. Test Advice (New) ---
    advice = ""
    try:
        print("🧪 Reviewer: Analyzing for missing tests...")
        advice_prompt = f"""
        Analyze the code changes below and list 3 critical test cases that should be added/verified.
        Focus on edge cases.
        
        Code:
        {json.dumps(changes, indent=2)[:3000]}
        
        Output: Bullet points only.
        """
        advice = llm.invoke([HumanMessage(content=advice_prompt)]).content
        print(f"\n⚠️ Recommended Test Cases:\n{advice}\n")
    except Exception as e:
        print(f"⚠️ Reviewer Advice failed: {e}")

    return {"code_content": content, "test_suggestions": advice}
