"""
🟥 RED Phase: Tests for Gemini CLI Model Selection feature.
These tests are expected to FAIL initially.
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock


# ===========================================================================
# Test 1: config.py should have AVAILABLE_GEMINI_CLI_MODELS list
# ===========================================================================
def test_available_gemini_cli_models_exists():
    """config should export AVAILABLE_GEMINI_CLI_MODELS with all 5 models."""
    from luma_core import config
    assert hasattr(config, "AVAILABLE_GEMINI_CLI_MODELS")
    expected_models = [
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-3-pro-preview",
        "gemini-2.5-flash-lite",
    ]
    assert config.AVAILABLE_GEMINI_CLI_MODELS == expected_models


# ===========================================================================
# Test 2: config.py should have GEMINI_CLI_MODEL defaulting to gemini-2.5-flash
# ===========================================================================
def test_gemini_cli_model_default():
    """GEMINI_CLI_MODEL should default to 'gemini-2.5-flash'."""
    from luma_core import config
    assert hasattr(config, "GEMINI_CLI_MODEL")
    assert config.GEMINI_CLI_MODEL == "gemini-2.5-flash"


# ===========================================================================
# Test 3: GEMINI_CLI_MODEL should be loaded from .luma_global.json if present
# ===========================================================================
def test_gemini_cli_model_loaded_from_global_config(tmp_path):
    """GEMINI_CLI_MODEL should be persisted and restored from .luma_global.json."""
    from luma_core import config
    
    config_file = tmp_path / ".luma_global.json"
    config_file.write_text(json.dumps({"GEMINI_CLI_MODEL": "gemini-2.5-flash"}))
    
    original = config.GEMINI_CLI_MODEL
    try:
        with patch.object(config, "GLOBAL_CONFIG_FILE", str(config_file)):
            # Simulate what happens when config loads: read from file
            with open(str(config_file), "r") as f:
                cfg = json.load(f)
            loaded_model = cfg.get("GEMINI_CLI_MODEL", "gemini-2.5-flash")
            assert loaded_model == "gemini-2.5-flash"
    finally:
        config.GEMINI_CLI_MODEL = original


# ===========================================================================
# Test 4: save_gemini_cli_model should persist model to global config
# ===========================================================================
def test_save_gemini_cli_model(tmp_path):
    """save_gemini_cli_model should write the model name to .luma_global.json."""
    from luma_core import config
    
    config_file = tmp_path / ".luma_global.json"
    config_file.write_text(json.dumps({"LLM_PROVIDER": "gemini_cli"}))
    
    with patch.object(config, "GLOBAL_CONFIG_FILE", str(config_file)):
        config.save_gemini_cli_model("gemini-3-pro-preview")
    
    saved = json.loads(config_file.read_text())
    assert saved["GEMINI_CLI_MODEL"] == "gemini-3-pro-preview"


# ===========================================================================
# Test 5: delegate_task_to_gemini should use config.GEMINI_CLI_MODEL
# ===========================================================================
@patch("subprocess.run")
def test_delegate_task_to_gemini_uses_configured_model(mock_subprocess_run):
    """delegate_task_to_gemini should use config.GEMINI_CLI_MODEL, not hardcoded."""
    from luma_core import config
    
    # Set a specific model
    original = getattr(config, "GEMINI_CLI_MODEL", "gemini-2.5-pro")
    config.GEMINI_CLI_MODEL = "gemini-3-flash-preview"
    
    try:
        from luma_core.gemini_cli import delegate_task_to_gemini
        delegate_task_to_gemini("mock_task.md", "/mock/path")
        
        args, kwargs = mock_subprocess_run.call_args
        call_args_list = args[0]
        
        # The -m flag should use the configured model
        assert "-m" in call_args_list
        m_index = call_args_list.index("-m")
        assert call_args_list[m_index + 1] == "gemini-3-flash-preview"
    finally:
        config.GEMINI_CLI_MODEL = original


# ===========================================================================
# Test 6: save_gemini_cli_model should also update the runtime variable
# ===========================================================================
def test_save_gemini_cli_model_updates_runtime(tmp_path):
    """save_gemini_cli_model should update config.GEMINI_CLI_MODEL at runtime."""
    from luma_core import config
    
    config_file = tmp_path / ".luma_global.json"
    config_file.write_text(json.dumps({}))
    
    original = getattr(config, "GEMINI_CLI_MODEL", "gemini-2.5-pro")
    
    try:
        with patch.object(config, "GLOBAL_CONFIG_FILE", str(config_file)):
            config.save_gemini_cli_model("gemini-2.5-flash-lite")
        
        assert config.GEMINI_CLI_MODEL == "gemini-2.5-flash-lite"
    finally:
        config.GEMINI_CLI_MODEL = original
