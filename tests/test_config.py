import os
import json
import pytest
import luma_core.config as config
from unittest.mock import patch, mock_open
import importlib

@pytest.fixture
def mock_luma_global():
    mock_data = {
        "LLM_PROVIDER": "openrouter",
        "AGENT_CLI": "opencode"
    }
    return json.dumps(mock_data)

def test_config_loads_from_global_json(mock_luma_global):
    original_exists = os.path.exists
    def mock_exists(path):
        if "luma_global.json" in path:
            return True
        return original_exists(path)
        
    with patch("builtins.open", mock_open(read_data=mock_luma_global)), \
         patch("os.path.exists", side_effect=mock_exists):
        importlib.reload(config)
        assert config.LLM_PROVIDER == "openrouter"
        assert config.AGENT_CLI == "opencode"

def test_config_defaults():
    original_exists = os.path.exists
    def mock_exists(path):
        if "luma_global.json" in path:
            return False
        return original_exists(path)
        
    with patch("os.path.exists", side_effect=mock_exists):
        importlib.reload(config)
        # Should default to gemini-cli LLM provider and gemini_cli AGENT_CLI
        assert config.LLM_PROVIDER == "gemini-cli"
        assert config.AGENT_CLI == "gemini_cli"
        assert config.GEMINI_CLI_MODEL == "gemini-2.5-flash"


def test_config_normalizes_legacy_llm_provider_name_from_global_json():
    mock_data = json.dumps(
        {
            "LLM_PROVIDER": "gemini_cli",
            "AGENT_CLI": "opencode",
        }
    )

    original_exists = os.path.exists

    def mock_exists(path):
        if "luma_global.json" in path:
            return True
        return original_exists(path)

    with patch("builtins.open", mock_open(read_data=mock_data)), patch(
        "os.path.exists", side_effect=mock_exists
    ):
        importlib.reload(config)
        assert config.LLM_PROVIDER == "gemini-cli"


def test_config_normalizes_known_custom_project_kanban():
    """Test that canonical kanban values are applied when project has None/empty values,
    but user-customized values are preserved."""
    from luma_core.config import normalize_project_entry, CANONICAL_KANBAN_BY_REPO
    
    # Test 1: When project has None/empty values, canonical values are applied
    project_with_none = {
        "name": "Luma",
        "repo": "oatrice/Luma",
        "kanban_number": None,
        "kanban_id": None,
    }
    result = normalize_project_entry(project_with_none)
    assert result["kanban_number"] == 5  # Canonical value applied
    assert result["kanban_id"] == "PVT_kwHOATfKEM4BKOOI"
    
    # Test 2: When project has empty kanban_id, canonical value is applied
    project_with_empty_id = {
        "name": "Luma",
        "repo": "oatrice/Luma",
        "kanban_number": 5,
        "kanban_id": "",
    }
    result = normalize_project_entry(project_with_empty_id)
    assert result["kanban_number"] == 5
    assert result["kanban_id"] == "PVT_kwHOATfKEM4BKOOI"
    
    # Test 3: When project has user-customized values (different from canonical), preserve them
    project_with_custom = {
        "name": "Cerebro",
        "repo": "oatrice/Cerebro",
        "kanban_number": 12,
        "kanban_id": "PVT_custom",
    }
    result = normalize_project_entry(project_with_custom)
    # Cerebro's canonical kanban is None, so user-customized values should be preserved
    assert result["kanban_number"] == 12
    assert result["kanban_id"] == "PVT_custom"


def test_detect_project_key_for_path_prefers_most_specific_match():
    projects = {
        "1": {"path": "/Users/oatrice/Software-projects"},
        "12": {"path": "/Users/oatrice/Software-projects/Luma"},
    }

    detected = config.detect_project_key_for_path(
        "/Users/oatrice/Software-projects/Luma/luma_core",
        projects,
    )

    assert detected == "12"


def test_get_status_workflow_uses_luma_specific_lanes():
    workflow = config.get_status_workflow(
        {
            "name": "Luma",
            "repo": "oatrice/Luma",
        }
    )

    assert workflow["board_order"] == [
        "Backlog",
        "Ready",
        "In Progress",
        "In Review",
        "Done",
    ]
    assert workflow["selectable_statuses"] == ["Ready", "In Progress"]
