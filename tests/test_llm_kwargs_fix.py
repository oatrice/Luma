import unittest
from typing import Any, ClassVar, Optional
from unittest.mock import MagicMock
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import AIMessage, HumanMessage
from luma_core.llm import TrackedModel

class MockChatModel(BaseChatModel):
    last_run_manager: ClassVar[Optional[Any]] = None
    last_kwargs: ClassVar[Optional[dict]] = None

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        type(self).last_run_manager = run_manager
        type(self).last_kwargs = kwargs
        # Result of the fix: forwarded kwargs stay intact without re-inserting
        # run_manager into the child kwargs payload.
        assert "run_manager" not in kwargs
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="mock"))])

    @property
    def _llm_type(self):
        return "mock"

class TestLLMKwargsFix(unittest.TestCase):
    def test_tracked_model_generate_strips_duplicate_run_manager(self):
        mock_model = MockChatModel()
        tracked = TrackedModel(model=mock_model)
        
        messages = [HumanMessage(content="hello")]
        run_manager = MagicMock()
        
        # Python itself rejects duplicate keyword arguments before the function
        # body runs, so the realistic regression test is that the wrapper
        # forwards extra kwargs without adding a duplicate run_manager.
        result = tracked._generate(
            messages,
            stop=None,
            run_manager=run_manager,
            trace_id="abc123",
        )

        self.assertEqual(result.generations[0].text, "mock")
        self.assertIs(mock_model.last_run_manager, run_manager)
        self.assertEqual(mock_model.last_kwargs, {"trace_id": "abc123"})

if __name__ == "__main__":
    unittest.main()
