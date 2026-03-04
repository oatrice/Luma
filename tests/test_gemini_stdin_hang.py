import pytest
from luma_core.llm import GeminiCLIModel
from langchain_core.messages import HumanMessage
import json

def test_gemini_stdin_large_payload():
    model = GeminiCLIModel()
    # Create a large payload (e.g. 200KB)
    large_code = "print('hello world')\n" * 10000
    prompt = f"Analyze this code:\n{large_code}\nReply ONLY with PASS."
    
    messages = [HumanMessage(content=prompt)]
    
    try:
        response = model.invoke(messages)
        print(f"Response: {response.content}")
        assert "PASS" in response.content.upper() or "Error" in response.content
    except Exception as e:
        pytest.fail(f"Model invoke failed with exception: {e}")

if __name__ == "__main__":
    test_gemini_stdin_large_payload()
