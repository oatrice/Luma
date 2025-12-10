
import pytest
from unittest.mock import patch, MagicMock
import main

# สร้าง Mock return ค่าที่ยาวมากๆ (3000 ตัวอักษร)
def mock_long_output(*args, **kwargs):
    long_str = "a" * 3000
    return MagicMock(returncode=1, stdout=long_str, stderr="")

def test_log_truncation_default():
    """Test that logs are truncated by default"""
    if not hasattr(main, 'tester_agent'):
         pytest.fail("tester_agent not implemented")
         
    state = {
        "task": "test",
        "filename": "server.go",
        "code_content": "package main",
        "iterations": 0
    }
    
    # Mock IO และ Subprocess
    with patch('subprocess.run', side_effect=mock_long_output):
        # We assume file exists logic for simplicity in mocking
        with patch('os.makedirs'), \
             patch('builtins.open', MagicMock()), \
             patch('shutil.copy2'), \
             patch('shutil.move'), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove'):
            result = main.tester_agent(state)
            
    error_log = result.get("test_errors", "")
    assert "Truncated" in error_log
    assert len(error_log) < 3000

def test_log_truncation_disabled():
    """Test that logs are NOT truncated when disable_log_truncation is True"""
    if not hasattr(main, 'tester_agent'):
         pytest.fail("tester_agent not implemented")

    state = {
        "task": "test",
        "filename": "server.go",
        "code_content": "package main",
        "iterations": 0,
        "disable_log_truncation": True # Flag ใหม่
    }
    
    with patch('subprocess.run', side_effect=mock_long_output):
        with patch('os.makedirs'), \
             patch('builtins.open', MagicMock()), \
             patch('shutil.copy2'), \
             patch('shutil.move'), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove'):
            result = main.tester_agent(state)
            
    error_log = result.get("test_errors", "")
    # คาดหวังว่าต้องไม่เจอคำว่า Truncated และความยาวต้องครบ (เพราะปัจจุบัน Logic ตัดเสมอ Test นี้จึงควร Fail)
    assert "Truncated" not in error_log
    assert len(error_log) >= 3000
