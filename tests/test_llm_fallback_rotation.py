from unittest.mock import patch

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from luma_core.llm import FallbackModel


class FailingStubModel(BaseChatModel):
    name: str

    @property
    def _llm_type(self) -> str:
        return f"stub:{self.name}"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError(f"{self.name} failed")


class SuccessStubModel(BaseChatModel):
    name: str
    response_text: str

    @property
    def _llm_type(self) -> str:
        return f"stub:{self.name}"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(
            generations=[
                ChatGeneration(message=AIMessage(content=self.response_text))
            ]
        )


def test_fallback_model_wraps_around_after_saved_active_index():
    models = [
        SuccessStubModel(name="model-1", response_text="first"),
        FailingStubModel(name="model-2"),
        FailingStubModel(name="model-3"),
    ]
    fallback = FallbackModel(models=models)

    with patch("luma_core.config.get_fallback_info", return_value=(2, 0.0)):
        with patch("luma_core.config.save_fallback_index") as mock_save:
            with patch("luma_core.usage_tracker.record_llm_event"):
                response = fallback.invoke([HumanMessage(content="hello")])

    assert response.content == "first"
    assert mock_save.call_count == 1
    assert mock_save.call_args.args[0] == 0
