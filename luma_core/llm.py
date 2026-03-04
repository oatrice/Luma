import os
import subprocess
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI 
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from pydantic import Field
from typing import Any, List, Optional
from typing import Any, List, Optional
import time

from . import config

# Store session metrics for Gemini CLI
_session_gemini_cli_time = 0.0
_session_gemini_cli_tokens = 0
class GeminiCLIModel(BaseChatModel):
    """LangChain wrapper for the gemini commands using subprocess"""
    
    model: str = Field(default="gemini-2.5-pro")
    temperature: float = Field(default=0.7)
    
    @property
    def _llm_type(self) -> str:
        return "gemini-cli"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Convert messages to a single prompt string
        prompt = ""
        for msg in messages:
            if hasattr(msg, "content"):
                prompt += f"{msg.content}\n"
            elif isinstance(msg, dict) and "content" in msg:
                prompt += f"{msg['content']}\n"
                
        # Call gemini cli using STDIN to avoid OS ARG_MAX limits for large code payloads
        start_time = time.time()
        
        try:
            print(f"🐛 DEBUG [GeminiCLIModel]: Generating response using model {self.model} (Payload length: {len(prompt)} chars)")
            
            # Use Popen to pipe prompt via stdin
            process = subprocess.Popen(
                ["gemini", "-m", self.model],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send prompt and wait for completion (timeout 3 minutes)
            stdout, stderr = process.communicate(input=prompt, timeout=180)
            
            if process.returncode != 0:
                print(f"⚠️ Gemini CLI Error Output: {stderr}")
                output = f"Error calling Gemini CLI (Return Code {process.returncode}): {stderr}"
            else:
                output = stdout.strip()
                
        except subprocess.TimeoutExpired:
            process.kill()
            print("⚠️ Gemini CLI Timeout Expired (180s)")
            output = "Error: Gemini CLI timed out after 3 minutes."
        except Exception as e:
            print(f"⚠️ Gemini CLI Exception: {str(e)}")
            output = f"Error: {str(e)}"
            
        end_time = time.time()
        duration = end_time - start_time
        
        # Approximate Token Usage (4 chars ~= 1 token)
        tokens_in = len(prompt) // 4
        tokens_out = len(output) // 4
        total_tokens = tokens_in + tokens_out
        
        # Accumulate to global
        global _session_gemini_cli_time, _session_gemini_cli_tokens
        _session_gemini_cli_time += duration
        _session_gemini_cli_tokens += total_tokens
        
        print(f"⏱️ Gemini CLI Response Time: {duration:.2f}s | 🪙 Tokens Used (Approx): {total_tokens} (In: {tokens_in}, Out: {tokens_out})")

        message = AIMessage(content=output)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])


def get_llm(temperature=0.7, purpose="general"):
    """Factory function to get the configured LLM instance"""
    print(f"🐛 DEBUG [get_llm]: Reading config.LLM_PROVIDER = {config.LLM_PROVIDER}")
    
    if config.LLM_PROVIDER == "openrouter":
        model_name = config.OPENROUTER_GENERAL_MODEL
        if purpose == "code":
            model_name = config.OPENROUTER_CODE_MODEL
        
        print(f"🔌 Using OpenRouter ({model_name})...")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=config.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
            max_tokens=4000
        )
    elif config.LLM_PROVIDER == "gemini":
        model_name = config.GEMINI_GENERAL_MODEL
        if purpose == "code":
            model_name = config.GEMINI_CODE_MODEL

        print(f"🔌 Using Gemini ({model_name})...")
        return ChatGoogleGenerativeAI(
            model=model_name, 
            google_api_key=config.GOOGLE_API_KEY,
            temperature=temperature,
            request_timeout=120
        )
    elif config.LLM_PROVIDER == "gemini_cli":
        model_name = config.GEMINI_CODE_MODEL if purpose == "code" else config.GEMINI_GENERAL_MODEL
        print(f"🔌 Using Gemini CLI ({model_name})...")
        return GeminiCLIModel(model=model_name, temperature=temperature)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {config.LLM_PROVIDER}")
