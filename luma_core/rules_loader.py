import json
import os
import jsonschema
from typing import Dict, Any

def load_project_rules(rules_path: str) -> Dict[str, Any]:
    """
    Load project rules from a JSON file.
    Returns empty dict if file not found or invalid JSON.
    """
    if not os.path.exists(rules_path):
        return {}
        
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading rules from {rules_path}: {e}")
        return {}

def validate_rules(rules: Dict[str, Any], schema_path: str = "schemas/luma_rules.schema.json") -> bool:
    """
    Validate rules against the JSON schema.
    """
    if not os.path.exists(schema_path):
        print(f"Schema not found at {schema_path}")
        return False
        
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
            
        jsonschema.validate(instance=rules, schema=schema)
        return True
    except jsonschema.exceptions.ValidationError as e:
        print(f"Rules validation error: {e.message}")
        return False
    except Exception as e:
        print(f"Schema validation error: {e}")
        return False
