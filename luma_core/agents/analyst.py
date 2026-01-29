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
    system_prompt = """You are a Senior Technical Analyst. Your goal is to analyze the provided GitHub Issue and fill out the Technical Analysis Document based on the provided template.
    
    Guidelines:
    - Be thorough and detailed.
    - If information is missing in the issue, make reasonable assumptions based on standard software practices, but note them.
    - For 'Impact Analysis', consider a standard web/mobile app structure (React/Next.js frontend, Python/Node backend).
    - Maintain the exact markdown structure of the template.
    - Output ONLY the filled markdown content.
    """
    
    user_prompt = f"""
    Please fill out the following analysis template for this issue:
    
    Issue Title: {issue_data.get('title', task)}
    Issue Number: {issue_data.get('number', 'N/A')}
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
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    sanitized_title = sanitize_filename(task)
    output_folder_name = f"{timestamp}-{sanitized_title}"
    output_dir = os.path.join(target_dir, "docs", output_folder_name)
    
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "analysis.md")
    
    with open(output_file, 'w') as f:
        f.write(analysis_content)
        
    print(f"✅ Analysis saved to: {output_file}")
    
    return {
        "analysis_file": output_file,
        "analysis_content": analysis_content
    }
