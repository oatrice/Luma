from types import SimpleNamespace

from luma_core.agents import reviewer as reviewer_module


class _FakeLLM:
    def __init__(self):
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        if len(self.calls) == 1:
            return SimpleNamespace(content="PASS")
        return SimpleNamespace(content="- Step 1: Run pytest")


def test_reviewer_agent_embeds_code_changes_in_manual_verification_prompt(monkeypatch):
    fake_llm = _FakeLLM()
    monkeypatch.setattr(reviewer_module, "get_llm", lambda temperature=0, purpose="code": fake_llm)

    result = reviewer_module.reviewer_agent(
        {
            "task": "Review local code changes for bugs.",
            "changes": {
                "main.py": "print('hello headless world')",
            },
        }
    )

    assert result["code_content"] == "PASS"
    assert result["test_suggestions"] == "- Step 1: Run pytest"

    advice_prompt = fake_llm.calls[1][0].content
    assert "print('hello headless world')" in advice_prompt
    assert "{json.dumps(changes, indent=2, ensure_ascii=False)[:3000]}" not in advice_prompt
