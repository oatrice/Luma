import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage
from luma_core.llm import GeminiAPIModel

def test_gemini_api_invoke_no_run_manager():
    """Verify that run_manager is NOT passed as a keyword argument to invoke()."""
    with patch("luma_core.llm.ChatGoogleGenerativeAI") as MockChat:
        mock_instance = MockChat.return_value
        
        model = GeminiAPIModel(model="gemini-1.5-pro")
        messages = [HumanMessage(content="hello")]
        run_manager = MagicMock()
        
        # Call it
        model._generate(messages, run_manager=run_manager)
        
        # Assert that invoke was called
        mock_instance.invoke.assert_called_once()
        
        # Get call arguments
        args, kwargs = mock_instance.invoke.call_args
        
        # Assert that run_manager is NOT in kwargs
        assert "run_manager" not in kwargs, f"run_manager should NOT be passed to invoke, but got: {kwargs}"
        # Assert that run_manager is also NOT in args (it's called with messages as first arg)
        assert len(args) == 1
        assert args[0] == messages

def test_gemini_api_invoke_cleans_other_kwargs():
    """Verify that extra kwargs survive while run_manager is not forwarded to invoke()."""
    with patch("luma_core.llm.ChatGoogleGenerativeAI") as MockChat:
        mock_instance = MockChat.return_value
        
        model = GeminiAPIModel(model="gemini-1.5-pro")
        messages = [HumanMessage(content="hello")]

        # Python rejects duplicate keyword arguments before _generate runs, so
        # we validate the real forwarding contract instead.
        model._generate(messages, run_manager="pos_val", other="val")
        
        # Assert invoke called once
        mock_instance.invoke.assert_called_once()
        args, kwargs = mock_instance.invoke.call_args
        
        assert "run_manager" not in kwargs
        assert kwargs["other"] == "val"
