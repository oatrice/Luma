import os
from langchain_core.messages import SystemMessage, HumanMessage
from luma_core.llm import get_llm
from luma_core.state import AgentState
from luma_core.project_context import load_project_context, build_context_block

def architect_agent(state: AgentState) -> dict:
    """
    Architect Agent: Generates plan.md from spec.md.
    """
    print("\n📐 Architect Agent: Generating Implementation Plan...")

    feature_dir = state.get('feature_dir')
    target_dir = state.get('target_dir', os.getcwd())
    target_planning_repos = state.get('target_planning_repos', [])
    
    if not feature_dir or not os.path.exists(feature_dir):
        # Try to find recent feature dir
        # (This logic might need robustness in production)
        print("⚠️ Feature directory not specified. Requesting user selection/input in real flow.")
        return {}

    # 1. Load Resources
    spec_path = os.path.join(feature_dir, "spec.md")
    if not os.path.exists(spec_path):
        print("❌ spec.md not found. Cannot generate plan.")
        return {}
        
    with open(spec_path, 'r', encoding='utf-8') as f:
        spec_content = f.read()

    template_path = os.path.join(target_dir, "docs", "templates", "plan_template.md")
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
    else:
        template_content = "# Implementation Plan\n\n[Template not found]"
        
    constitution_path = os.path.join(target_dir, "docs", "constitution.md")
    constitution_content = ""
    if os.path.exists(constitution_path):
        with open(constitution_path, 'r', encoding='utf-8') as f:
            constitution_content = f.read()

    # 2. Load project context (stack + agent rules from AGENTS.md)
    ctx = load_project_context(target_dir)
    context_block = build_context_block(ctx)
    if context_block:
        print("   📦 Loaded project context (AGENTS.md/README.md)")

    # 3. Construct Prompt
    sibling_repos_ctx = ""
    if target_planning_repos:
        repo_names = [r.get('name', 'Unknown') for r in target_planning_repos]
        sibling_repos_ctx = f"\n- **Cross-Repository Scope**: This implementation spans multiple repositories: {', '.join(repo_names)}. Detail how each repository will be modified."

    system_prompt = f"""You are a Senior Software Architect.
Your goal is to write a Technical Implementation Plan (`plan.md`) based on the provided Specification.

---
### 📜 CONSTITUTION (RULES)
{constitution_content}
---

{context_block}

### INSTRUCTIONS
1. Read the **Specification** carefully.
2. Fill out the **Implementation Plan Template**.
3. **Step-by-Step**: Break down the implementation into atomic, testable steps.
4. **Files**: Explicitly mention which files need creation or modification.
5. **Verification**: Define how each step will be verified.{sibling_repos_ctx}
6. Output ONLY the markdown content.
"""

    user_prompt = f"""
    Please generate the Implementation Plan for this Spec:
    
    ---
    SPECIFICATION:
    {spec_content}
    
    ---
    TEMPLATE:
    {template_content}
    """

    # 3. Call LLM
    try:
        print("🤖 Thinking (Architect Agent)...")
        llm = get_llm(temperature=0.3, purpose="code")
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        plan_content = response.content
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return {}

    # 4. Save Output
    output_file = os.path.join(feature_dir, "plan.md")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(plan_content)
        
    print(f"✅ Plan saved to: {output_file}")
    
    return {
        "plan_file": output_file,
        "plan_content": plan_content
    }
