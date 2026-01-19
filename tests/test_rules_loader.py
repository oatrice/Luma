import os
import json
import pytest
from luma_core.rules_loader import load_project_rules, validate_rules

# Dummy rules for testing
VALID_RULES = {
    "project_name": "TestProject",
    "kanban": {
        "project_number": 123,
        "owner": "testuser"
    },
    "preflight_checks": [
        {
            "id": "test_check",
            "type": "file_exists",
            "path": "README.md",
            "required": True
        }
    ]
}

INVALID_RULES = {
    "project_name": "TestProject"
    # Missing kanban details if they were required, but check schema
}

def test_load_project_rules(tmp_path):
    # Create a temporary rules file
    rules_file = tmp_path / ".luma_rules.json"
    rules_file.write_text(json.dumps(VALID_RULES), encoding="utf-8")
    
    rules = load_project_rules(str(rules_file))
    assert rules is not None
    assert rules["project_name"] == "TestProject"
    assert len(rules["preflight_checks"]) == 1

def test_load_non_existent_file():
    rules = load_project_rules("non_existent_file.json")
    assert rules == {}

def test_validate_rules_valid():
    # Assuming schema file exists in known location or passed explicitly
    # validation might rely on relative path to schema
    assert validate_rules(VALID_RULES, schema_path="schemas/luma_rules.schema.json") is True

def test_validate_rules_invalid():
    # Construct invalid data based on schema (e.g. wrong type)
    invalid_data = {
        "project_name": "TestProject",
        "preflight_checks": "should_be_list_not_string" 
    }
    assert validate_rules(invalid_data, schema_path="schemas/luma_rules.schema.json") is False
