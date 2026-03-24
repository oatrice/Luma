import os
import re
import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from luma_core.llm import get_llm
from luma_core.state import AgentState
from luma_core.project_context import load_project_context, build_context_block

def spec_agent(state: AgentState) -> dict:
    """
    Spec Agent: Generates spec.md from issue data.
    """
    print("\n🔍 Spec Agent: Generating Specification...")

    task = state.get('task')
    issue_data = state.get('issue_data', {})
    target_dir = state.get('target_dir', os.getcwd())
    target_planning_repos = state.get('target_planning_repos', [])
    
    if not task:
        print("❌ No task/issue provided.")
        return {}
    
    # 1. Load Resources
    # Spec Template
    template_path = os.path.join(target_dir, "docs", "templates", "spec_template.md")
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
    else:
        template_content = "# Specification\n\n[Template not found]"

    # Constitution
    constitution_path = os.path.join(target_dir, "docs", "constitution.md")
    constitution_content = ""
    if os.path.exists(constitution_path):
        with open(constitution_path, 'r', encoding='utf-8') as f:
            constitution_content = f.read()
    else:
        print("⚠️ Constitution not found.")

    # 2a. Load project context (tech stack + agent routing rules)
    ctx = load_project_context(target_dir)
    context_block = build_context_block(ctx)
    if context_block:
        print("   📦 Loaded project context (README/AGENTS.md)")

    # 2b. Construct Prompt
    issue_url = issue_data.get('url', '')
    if not issue_url and issue_data.get('number'):
        repo = issue_data.get('repository', '')
        if repo:
            issue_url = f"https://github.com/{repo}/issues/{issue_data.get('number')}"
            
    sibling_repos_ctx = ""
    if target_planning_repos:
        repo_names = [r.get('name', 'Unknown') for r in target_planning_repos]
        sibling_repos_ctx = f"\n- **Cross-Repository Scope**: This specification spans multiple repositories: {', '.join(repo_names)}. Ensure your spec is comprehensive across all these domains."
            
    system_prompt = f"""You are an Expert Product Manager and Systems Analyst.
Your goal is to write a detailed Specification Document (`spec.md`) for the user's request.

---
### 📜 CONSTITUTION (RULES)
{constitution_content}
---

{context_block}

### INSTRUCTIONS
1. Analyze the Issue Request below.
2. Fill out the **Specification Template** accurately.
3. **SBE (Specification by Example)**: You MUST generate at least 2 Scenarios with concrete Examples tables.
4. **User-Centric**: Focus on the "Goal" and "User Journey".
5. **No Implementation Details**: Do NOT write code or technical steps here (that's for the Plan). Focus on *behavior*.{sibling_repos_ctx}
6. Output ONLY the markdown content.
"""

    user_prompt = f"""
    Please generate the Specification for:
    
    Title: {issue_data.get('title', task)}
    Issue URL: {issue_url}
    Body:
    {issue_data.get('body', 'No description.')}
    
    ---
    TEMPLATE:
    {template_content}
    """

    # 3. Call LLM
    try:
        print("🤖 Thinking (Spec Agent)...")
        llm = get_llm(temperature=0.3)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        spec_content = response.content
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return {}

    # 4. Save Output
    features_root = os.path.join(target_dir, "docs", "features")
    if not os.path.exists(os.path.join(target_dir, "docs")) and os.path.exists(os.path.join(target_dir, "..", "docs")):
        features_root = os.path.join(target_dir, "..", "docs", "features")
    
    os.makedirs(features_root, exist_ok=True)
    
    # Calculate Next Index (Reuse logic or simplify)
    # Simple logic finding next available or existing folder for this issue
    issue_number = str(issue_data.get('number', '0'))
    
    # Check if folder already exists for this issue
    existing_folder = None
    for d in os.listdir(features_root):
        if f"issue-{issue_number}" in d:
            existing_folder = d
            break
            
    if existing_folder:
        output_dir = os.path.join(features_root, existing_folder)
    else:
        # Create new
        next_index = 1
        # ... folder creation logic ...
        # (Simplified for brevity, assuming standard Luma folder structure logic reused or copied)
        # Use simple timestamp-based or just count dirs
        count = len([d for d in os.listdir(features_root) if os.path.isdir(os.path.join(features_root, d))])
        next_index = count + 1
        
        safe_title = re.sub(r'[^\w\s-]', '', task).strip().lower().replace(" ", "-")
        output_dir = os.path.join(features_root, f"{next_index}_issue-{issue_number}_{safe_title}")
        os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, "spec.md")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
        
    print(f"✅ Spec saved to: {output_file}")
    
    return {
        "spec_file": output_file,
        "spec_content": spec_content,
        "feature_dir": output_dir
    }
