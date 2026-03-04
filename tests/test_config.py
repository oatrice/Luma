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
        # Should default to gemini_cli LLM provider and gemini_cli AGENT_CLI
        assert config.LLM_PROVIDER == "gemini_cli"
        assert config.AGENT_CLI == "gemini_cli"

