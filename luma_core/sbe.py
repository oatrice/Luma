"""
SBE (Specification by Example) Module

Core module for creating and parsing SBE specifications.
Format: Markdown with Given/When/Then structure and Examples tables.
"""
import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Scenario:
    """A single SBE scenario with examples."""
    name: str
    given: str
    when: str
    then: str
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass 
class SBESpec:
    """Complete SBE specification with feature and scenarios."""
    feature: str
    description: str
    scenarios: List[Scenario] = field(default_factory=list)


def parse_sbe_spec(filepath: str) -> SBESpec:
    """
    Parse SBE markdown file into SBESpec object.
    
    Args:
        filepath: Path to the SBE markdown file
        
    Returns:
        SBESpec object with parsed data
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"SBE file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse feature name
    feature_match = re.search(r'^##\s*Feature:\s*(.+)$', content, re.MULTILINE)
    feature_name = feature_match.group(1).strip() if feature_match else "Unknown Feature"
    
    # Parse description (text between Feature and first Scenario)
    desc_match = re.search(r'^##\s*Feature:.+?\n\n(.+?)\n\n###', content, re.MULTILINE | re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else ""
    
    # Parse scenarios
    scenarios = []
    scenario_pattern = r'###\s*Scenario:\s*(.+?)\n(.+?)(?=###\s*Scenario:|$)'
    scenario_matches = re.findall(scenario_pattern, content, re.DOTALL)
    
    for scenario_name, scenario_content in scenario_matches:
        # Parse Given/When/Then
        given_match = re.search(r'\*\*Given\*\*\s*(.+?)(?=\*\*When\*\*|\n\n)', scenario_content, re.DOTALL)
        when_match = re.search(r'\*\*When\*\*\s*(.+?)(?=\*\*Then\*\*|\n\n)', scenario_content, re.DOTALL)
        then_match = re.search(r'\*\*Then\*\*\s*(.+?)(?=\n\n|####|$)', scenario_content, re.DOTALL)
        
        given = given_match.group(1).strip() if given_match else ""
        when = when_match.group(1).strip() if when_match else ""
        then = then_match.group(1).strip() if then_match else ""
        
        # Parse Examples table
        examples = _parse_examples_table(scenario_content)
        
        scenarios.append(Scenario(
            name=scenario_name.strip(),
            given=given,
            when=when,
            then=then,
            examples=examples
        ))
    
    return SBESpec(
        feature=feature_name,
        description=description,
        scenarios=scenarios
    )


def _parse_examples_table(content: str) -> List[Dict[str, Any]]:
    """Parse markdown table into list of dicts."""
    examples = []
    
    # Find table - match rows with or without trailing newline
    table_match = re.search(r'####\s*Examples\s*\n\n\|(.+?)\|\n\|[-\s|]+\|\n((?:\|.+\|(?:\n|$))*)', content, re.DOTALL)
    
    if not table_match:
        return examples
    
    # Parse headers
    headers = [h.strip() for h in table_match.group(1).split('|')]
    
    # Parse rows
    rows = table_match.group(2).strip().split('\n')
    for row in rows:
        if not row.strip():
            continue
        values = [v.strip() for v in row.strip('|').split('|')]
        if len(values) == len(headers):
            example = {}
            for header, value in zip(headers, values):
                # Try to convert to number
                try:
                    example[header] = int(value)
                except ValueError:
                    try:
                        example[header] = float(value)
                    except ValueError:
                        example[header] = value
            examples.append(example)
    
    return examples


def validate_sbe_spec(spec: SBESpec) -> bool:
    """
    Validate SBE specification.
    
    Rules:
    - Feature name must not be empty
    - Must have at least one scenario
    - Each scenario must have at least one example
    
    Args:
        spec: SBESpec object to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Check feature name
    if not spec.feature or spec.feature.strip() == "":
        return False
    
    # Check scenarios
    if not spec.scenarios or len(spec.scenarios) == 0:
        return False
    
    # Check each scenario has examples
    for scenario in spec.scenarios:
        if not scenario.examples or len(scenario.examples) == 0:
            return False
    
    return True


def generate_sbe_from_issue(issue_data: dict, output_dir: str) -> str:
    """
    Generate SBE specification from GitHub issue data.
    
    This is a stub that creates a basic SBE structure.
    The actual AI-powered generation is in sbe_agent.py.
    
    Args:
        issue_data: Dict with 'title', 'number', 'body' keys
        output_dir: Directory to save the SBE file
        
    Returns:
        Path to the generated SBE file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    title = issue_data.get('title', 'Unknown Feature')
    number = issue_data.get('number', 0)
    body = issue_data.get('body', '')
    
    # Generate filename
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:40]
    filename = f"sbe_issue-{number}_{slug}.md"
    filepath = os.path.join(output_dir, filename)
    
    # Generate SBE content
    sbe_content = f"""# SBE: {title}

## Feature: {title}

{body}

### Scenario: Happy path - Basic success case

**Given** the preconditions are met
**When** the user performs the action
**Then** the expected outcome occurs

#### Examples

| input | expected |
|-------|----------|
| valid_input_1 | success |
| valid_input_2 | success |
| valid_input_3 | success |

### Scenario: Edge case - Invalid input handling

**Given** the system is ready
**When** the user provides invalid input
**Then** an appropriate error is shown

#### Examples

| input | expected |
|-------|----------|
| empty | error_message |
| invalid | error_message |
| overflow | error_message |
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(sbe_content)
    
    return filepath
