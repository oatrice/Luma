
import pytest
from unittest.mock import patch, MagicMock
import main

def test_coder_uses_test_feedback():
    """
    Test that Coder agent incorporates test errors into the prompt 
    when revisiting the code (Red -> Green attempt).
    """
    # จำลอง State ที่มี Error จากรอบที่แล้ว
    state = {
        "task": "Create struct",
        "filename": "server.go",
        "code_content": "package main...",
        "test_errors": "server.go:10: undefined: GameSession", # Error จาก Tester
        "iterations": 1
    }
    
    with patch('main.ChatGoogleGenerativeAI') as MockLLM:
        mock_instance = MockLLM.return_value
        # Mock การตอบกลับ
        mock_instance.invoke.return_value.content = "package main\n// Fixed"
        
        # Run Coder Agent
        main.coder_agent(state)
        
        # Capture Prompt ที่ส่งไปหา LLM
        call_args = mock_instance.invoke.call_args
        messages = call_args[0][0] # messages list
        # Debug print
        print(f"Sent prompt: {messages[1].content}")
        
        # Assert: Prompt ต้องมี Error Message ส่งไปด้วย
        # Custom Coder logic uses 'ERROR LOGS:'
        assert "undefined: GameSession" in messages[1].content
        assert "ERROR LOGS:" in messages[1].content
        assert "FAILED CODE:" in messages[1].content
