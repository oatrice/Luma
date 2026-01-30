import os
import datetime
import re
from langchain_core.messages import SystemMessage, HumanMessage
from luma_core.llm import get_llm
from luma_core.state import AgentState

def sanitize_filename(name: str) -> str:
    """Sanitize string for use in filename."""
    name = re.sub(r'[^\w\s-]', '', name).strip().lower()
    return re.sub(r'[-\s]+', '-', name)

def analyst_agent(state: AgentState):
    """
    Analyst Agent: Refines issue and generates analysis document.
    """
    print("\n🔍 Analyst Agent: Refining Issue...")

    task = state.get('task')
    issue_data = state.get('issue_data', {})
    target_dir = state.get('target_dir', os.getcwd())
    
    if not task:
        print("❌ No task/issue provided.")
        return {}
    
    print(f"📄 Analyzing Issue: {task}")
    
    # 1. Load Template
    template_path = os.path.join(target_dir, "docs", "templates", "analysis_template.md")
    if not os.path.exists(template_path):
        print(f"⚠️ Template not found at {template_path}. Using empty template.")
        template_content = "# Analysis (Auto-generated)\n\n[Template not found]"
    else:
        with open(template_path, 'r') as f:
            template_content = f.read()

    # 2. Construct Prompt
    print("🤖 Constructing LLM Prompt...")
    
    # Build Issue URL if we have enough info
    issue_url = issue_data.get('url', '')
    if not issue_url and issue_data.get('number'):
        # Try to construct from repo info if available
        repo = issue_data.get('repository', '')
        if repo:
            issue_url = f"https://github.com/{repo}/issues/{issue_data.get('number')}"
    
    system_prompt = """You are a Senior Technical Analyst. Your goal is to analyze the provided GitHub Issue and fill out the Technical Analysis Document based on the provided template.
    
    Guidelines:
    - Be thorough and detailed.
    - If information is missing in the issue, make reasonable assumptions based on standard software practices, but note them.
    - For 'Impact Analysis', consider a standard web/mobile app structure (React/Next.js frontend, Python/Node backend).
    - Maintain the exact markdown structure of the template.
    - IMPORTANT: In the 'Feature Information' table, you MUST include an 'Issue URL' row with a markdown link to the GitHub issue.
    - Use the current date for the 'Date' field.
    - Output ONLY the filled markdown content.
    """
    
    user_prompt = f"""
    Please fill out the following analysis template for this issue:
    
    Issue Title: {issue_data.get('title', task)}
    Issue Number: {issue_data.get('number', 'N/A')}
    Issue URL: {issue_url or 'N/A'}
    Issue Body:
    {issue_data.get('body', 'No description provided.')}
    
    ---
    TEMPLATE:
    {template_content}
    """

    # 3. Call LLM
    try:
        llm = get_llm(temperature=0.3, purpose="code") # Low temp for structured output
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = llm.invoke(messages)
        analysis_content = response.content
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return {}

    # 4. Save Output
    # Smart path resolution for docs/features
    features_root = os.path.join(target_dir, "docs", "features")
    
    # If not found in target_dir, try parent (common in monorepos like JarWise/Web -> JarWise)
    if not os.path.exists(os.path.join(target_dir, "docs")) and os.path.exists(os.path.join(target_dir, "..", "docs")):
        features_root = os.path.join(target_dir, "..", "docs", "features")
    
    os.makedirs(features_root, exist_ok=True)

    # Calculate Next Index
    next_index = 1
    try:
        existing_dirs = [d for d in os.listdir(features_root) if os.path.isdir(os.path.join(features_root, d))]
        indices = []
        for d in existing_dirs:
            match = re.match(r'^(\d+)_', d)
            if match:
                indices.append(int(match.group(1)))
        
        if indices:
            next_index = max(indices) + 1
    except Exception as e:
        print(f"⚠️ Error calculating next index: {e}")

    # specific format: N_issue-ID_slug
    sanitized_title = sanitize_filename(task)
    # Replace spaces with hyphens for slug style if sanitize didn't
    sanitized_title = sanitized_title.replace(" ", "-")
    
    issue_number = issue_data.get('number', '0')
    output_folder_name = f"{next_index}_issue-{issue_number}_{sanitized_title}"
    
    output_dir = os.path.join(features_root, output_folder_name)
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "analysis.md")
    
    with open(output_file, 'w') as f:
        f.write(analysis_content)
        
    print(f"✅ Analysis saved to: {output_file}")
    
    return {
        "analysis_file": output_file,
        "analysis_content": analysis_content
    }

def generate_branch_names(title: str, body: str, issue_number: int) -> list:
    """Generate 3 suggested branch names using LLM."""
    print("🤖 Generating smart branch names...")
    
    system_prompt = """You are a Git expert. Generate 3 valid git branch names based on the issue title and body.
    
    Rules:
    - Format: feat/ISSUE_NUMBER-short-summary
    - Use kebab-case (lowercase, hyphens).
    - Keep it concise (max 40 chars after prefix).
    - If it's a bug, use 'fix/' prefix instead of 'feat/'.
    - If it's a chore/refactor, use 'chore/' or 'refactor/'.
    - Output ONLY the 3 branch names, one per line. No numbering, no bullets.
    """
    
    user_prompt = f"""
    Issue #{issue_number}: {title}
    
    Body:
    {body[:500]}...
    """
    
    try:
        llm = get_llm(temperature=0.7, purpose="code")
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = llm.invoke(messages)
        
        # Parse lines
        names = [line.strip() for line in response.content.split('\n') if line.strip()]
        
        # Basic cleanup/validation
        cleaned = [n for n in names if '/' in n][:3]
        return cleaned if cleaned else names[:3]
        
    except Exception as e:
        print(f"⚠️ LLM Branch Gen Error: {e}")
        # Fallback
        slug = sanitize_filename(title)[:30]
        return [f"feat/{issue_number}-{slug}"]
