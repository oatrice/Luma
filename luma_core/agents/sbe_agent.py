"""
SBE Agent - AI-powered Specification by Example Generator

Uses LLM to generate SBE specifications from GitHub issue data.
Output: Markdown file with Given/When/Then scenarios and Examples tables.
"""
import os
import re
import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from luma_core.llm import get_llm
from luma_core.state import AgentState


def sanitize_filename(name: str) -> str:
    """Sanitize string for use in filename."""
    name = re.sub(r'[^\w\s-]', '', name).strip().lower()
    return re.sub(r'[-\s]+', '-', name)


def sbe_agent(state: AgentState) -> dict:
    """
    SBE Agent: Generates Specification by Example from issue data.
    
    Creates markdown file with:
    - Feature description
    - Multiple scenarios (happy path + edge cases)
    - Examples tables with concrete data
    
    Args:
        state: AgentState with 'task', 'issue_data', 'target_dir'
        
    Returns:
        dict with 'sbe_file' and 'sbe_content' keys
    """
    print("\n📋 SBE Agent: Generating Specification by Example...")
    
    task = state.get('task')
    issue_data = state.get('issue_data', {})
    target_dir = state.get('target_dir', os.getcwd())
    
    if not task:
        print("❌ No task/issue provided.")
        return {}
    
    print(f"📄 Generating SBE for: {task}")
    
    # 1. Load Template
    template_path = os.path.join(target_dir, "docs", "templates", "sbe_template.md")
    if not os.path.exists(template_path):
        print(f"⚠️ Template not found at {template_path}. Using default template.")
        template_content = _get_default_template()
    else:
        with open(template_path, 'r') as f:
            template_content = f.read()
    
    # 2. Build Issue URL
    issue_url = issue_data.get('url', '')
    if not issue_url and issue_data.get('number'):
        repo = issue_data.get('repository', '')
        if repo:
            issue_url = f"https://github.com/{repo}/issues/{issue_data.get('number')}"
    
    # 3. Construct Prompt
    print("🤖 Constructing LLM Prompt...")
    
    system_prompt = """You are a Senior QA Architect specialized in Specification by Example (SBE) and Behavior-Driven Development (BDD).

Your goal is to analyze the GitHub Issue and generate a comprehensive SBE specification.

Guidelines:
1. **Feature Section**: Clear description of what the feature does
2. **Scenarios**: Generate AT LEAST 3 scenarios:
   - Happy Path (normal successful flow)
   - Edge Cases (boundary conditions, limits)
   - Error Handling (invalid inputs, failures)
3. **Given/When/Then**: Use precise, testable statements
4. **Examples Tables**: Include 3-5 concrete examples per scenario with real values
5. **Be Specific**: Use actual values, not placeholders like "value1", "value2"
6. **Maintain Format**: Follow the exact markdown template structure
7. **Today's Date**: Use the current date provided

Output ONLY the filled markdown content, no explanations.
"""
    
    user_prompt = f"""
Generate an SBE specification for this issue:

Issue Title: {issue_data.get('title', task)}
Issue Number: #{issue_data.get('number', 'N/A')}
Issue URL: {issue_url or 'N/A'}
Today's Date: {datetime.datetime.now().strftime('%Y-%m-%d')}

Issue Description:
{issue_data.get('body', 'No description provided.')}

---
TEMPLATE TO FOLLOW:
{template_content}
"""
    
    # 4. Call LLM
    try:
        llm = get_llm(temperature=0.4, purpose="code")  # Slightly creative but structured
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = llm.invoke(messages)
        sbe_content = response.content
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return {}
    
    # 5. Save Output
    output_path = _save_sbe_file(sbe_content, issue_data, target_dir)
    
    print(f"✅ SBE saved to: {output_path}")
    
    return {
        "sbe_file": output_path,
        "sbe_content": sbe_content
    }


def _save_sbe_file(content: str, issue_data: dict, target_dir: str) -> str:
    """Save SBE content to specs directory."""
    
    # Find feature directory (same as analyst output)
    features_root = os.path.join(target_dir, "docs", "features")
    
    # Check parent for monorepo structure
    if not os.path.exists(os.path.join(target_dir, "docs")) and \
       os.path.exists(os.path.join(target_dir, "..", "docs")):
        features_root = os.path.join(target_dir, "..", "docs", "features")
    
    # Find existing feature folder or create new one
    issue_number = issue_data.get('number', 0)
    feature_dir = None
    
    if os.path.exists(features_root):
        for dirname in os.listdir(features_root):
            if f"issue-{issue_number}" in dirname:
                feature_dir = os.path.join(features_root, dirname)
                break
    
    if not feature_dir:
        # Create new feature directory
        title = issue_data.get('title', 'unknown')
        slug = sanitize_filename(title)[:30]
        next_index = 1
        
        if os.path.exists(features_root):
            existing = [d for d in os.listdir(features_root) if os.path.isdir(os.path.join(features_root, d))]
            indices = []
            for d in existing:
                match = re.match(r'^(\d+)_', d)
                if match:
                    indices.append(int(match.group(1)))
            if indices:
                next_index = max(indices) + 1
        
        feature_dir = os.path.join(features_root, f"{next_index}_issue-{issue_number}_{slug}")
    
    # Create feature directory if needed
    os.makedirs(feature_dir, exist_ok=True)
    
    # Generate filename
    filename = "sbe.md"
    filepath = os.path.join(feature_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath


def _get_default_template() -> str:
    """Return default SBE template if file not found."""
    return """# SBE: [FEATURE_NAME]

> 📅 Created: [DATE]
> 🔗 Issue: [ISSUE_URL]

---

## Feature: [FEATURE_NAME]

[FEATURE_DESCRIPTION]

### Scenario: Happy Path

**Given** [PRECONDITION]
**When** [ACTION]
**Then** [EXPECTED_OUTCOME]

#### Examples

| input | expected |
|-------|----------|
| value1 | result1 |
| value2 | result2 |

### Scenario: Error Handling

**Given** [PRECONDITION]
**When** [INVALID_ACTION]
**Then** [ERROR_OUTCOME]

#### Examples

| input | error |
|-------|-------|
| invalid | error_msg |
"""
