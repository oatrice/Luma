import unittest
from unittest.mock import MagicMock
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import AIMessage, HumanMessage
from luma_core.llm import TrackedModel

class MockChatModel(BaseChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # Result of the fix: this should NOT fail when TrackedModel calls it.
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
        
        # This simulates when LangChain's generate() gives both explicit and keyword
        # BUT we call the wrapper normally. The wrapper internal should be safe.
        kwargs = {"run_manager": "some_extra_context"}
        
        # This call to TrackedModel._generate should succeed because it will 
        # clean clean_kwargs before calling the underlying mock_model._generate
        try:
            result = tracked._generate(messages, stop=None, run_manager=run_manager, **kwargs)
            self.assertEqual(result.generations[0].text, "mock")
            print("Verified: TrackedModel safely handles 'run_manager' in kwargs.")
        except TypeError as e:
            self.fail(f"TrackedModel failed with TypeError: {e}")

if __name__ == "__main__":
    unittest.main()
