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
_current_gemini_session_id = None

class GeminiCLIModel(BaseChatModel):
    """LangChain wrapper for the gemini commands using subprocess"""
    
    model: str = Field(default="gemini-2.5-pro")
    temperature: float = Field(default=0.7)
    
    @property
    def _llm_type(self) -> str:
        return f"gemini-cli:{self.model}"

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
        
        global _current_gemini_session_id
        
        # Determine if we should prompt the user for a session on first run
        if _current_gemini_session_id is None:
            try:
                import re
                out = subprocess.run(["gemini", "--list-sessions"], capture_output=True, text=True)
                if out.returncode == 0 and "Available sessions" in out.stdout:
                    lines = out.stdout.strip().split("\n")
                    
                    # Extract sessions looking like: 1. Title... (1 day ago) [uuid]
                    sessions = []
                    for line in lines:
                        match = re.search(r"(\d+)\.\s+(.*?)\s+\[([a-f0-9\-]{36})\]", line)
                        if match:
                            sessions.append({
                                "index": match.group(1),
                                "title": match.group(2)[:60] + "..." if len(match.group(2)) > 60 else match.group(2),
                                "id": match.group(3)
                            })
                            
                    if sessions:
                        # Show most recent sessions first
                        sessions.reverse()
                        display_limit = min(8, len(sessions))
                        display_sessions = sessions[:display_limit]
                        
                        print("\n" + "="*50)
                        print("🤖 [Gemini CLI] Found active sessions for this repo.")
                        print("We should maintain context. Which session should I join?")
                        print("="*50)
                        print("  [0] 🆕 Start a NEW fresh session (Default)")
                        for i, s in enumerate(display_sessions, 1):
                            print(f"  [{i}] 📂 {s['title']}")
                            
                        choice = input(f"\nSelect session [0-{display_limit}]: ").strip()
                        if choice and choice != "0":
                            try:
                                idx = int(choice) - 1
                                if 0 <= idx < display_limit:
                                    _current_gemini_session_id = display_sessions[idx]["id"]
                                    print(f"🔗 Joined session: {_current_gemini_session_id}")
                                else:
                                    print("⚠️ Invalid selection. Starting a new session.")
                            except ValueError:
                                print("⚠️ Invalid input. Starting a new session.")
                        else:
                            print("🆕 Starting a new session.")
                            # We leave _current_gemini_session_id as None, it will get populated after the first request
            except Exception as e:
                print(f"⚠️ Could not list Gemini sessions: {e}")

        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"🐛 DEBUG [GeminiCLIModel]: Generating response using model {self.model} (Payload length: {len(prompt)} chars, Attempt {attempt+1}/{max_retries})")
                
                cmd = ["gemini", "-m", self.model]
                if _current_gemini_session_id:
                    cmd.extend(["-r", _current_gemini_session_id])
                    
                # Use Popen to pipe prompt via stdin
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Send prompt and wait for completion (timeout 5 minutes)
                stdout, stderr = process.communicate(input=prompt, timeout=300)
                
                if process.returncode != 0:
                    print(f"⚠️ Gemini CLI Error Output: {stderr}")
                    # Reset session ID if it was invalid
                    if "No previous sessions found" in stderr and _current_gemini_session_id:
                         _current_gemini_session_id = None
                         
                    output = f"Error calling Gemini CLI (Return Code {process.returncode}): {stderr}"
                    if attempt < max_retries - 1:
                        print(f"🔄 Retrying... ({attempt+1}/{max_retries})")
                        time.sleep(2)
                        continue
                else:
                    output = stdout.strip()
                    
                # If we don't have a session ID yet, fetch the one we just created
                if not _current_gemini_session_id and process.returncode == 0:
                    try:
                        import re
                        out = subprocess.run(["gemini", "--list-sessions"], capture_output=True, text=True)
                        match = re.search(r"1\..*?\[([a-f0-9\-]+)\]", out.stdout)
                        if match:
                            _current_gemini_session_id = match.group(1)
                            print(f"🐛 DEBUG [GeminiCLIModel]: Bound to persistent session {_current_gemini_session_id}")
                    except Exception:
                        pass
                
                break # Exit retry loop on success or non-retryable error
                    
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"⚠️ Gemini CLI Timeout Expired (300s) - Attempt {attempt+1}/{max_retries}")
                output = "Error: Gemini CLI timed out after 5 minutes."
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying due to timeout...")
                    time.sleep(2)
                    continue
            except Exception as e:
                print(f"⚠️ Gemini CLI Exception: {str(e)}")
                output = f"Error: {str(e)}"
                break # Don't retry on random exceptions
        
        # If we exhausted retries and it's an error, export prompt
        if "Error:" in output or "Error calling Gemini CLI" in output:
            timestamp = int(time.time())
            
            # Try to save to docs/features/.../ai_brain within the current project
            export_dir = None
            try:
                from luma_core.state_manager import load_state
                state = load_state(os.getcwd())
                if state and state.active_issue:
                    features_root = os.path.join(os.getcwd(), "docs", "features")
                    if os.path.exists(features_root):
                        for d in os.listdir(features_root):
                            if d.startswith(f"{state.active_issue.number}_") or f"issue-{state.active_issue.number}" in d:
                                export_dir = os.path.join(features_root, d, "ai_brain")
                                break
            except Exception as e:
                print(f"⚠️ Could not resolve feature dir for export: {e}")
                
            if not export_dir:
                export_dir = os.path.abspath(os.path.join(os.getcwd(), "docs", "ai_brain"))
                
            os.makedirs(export_dir, exist_ok=True)
            export_path = os.path.join(export_dir, f"luma_failed_prompt_{timestamp}.md")
            
            print(f"❌ Gemini CLI failed after retries. Exporting prompt to {export_path} for external AI.")
            try:
                with open(export_path, "w") as f:
                    f.write(prompt)
                error_msg = output + f"\n\n[SYSTEM] Gemini CLI failed to process the request. The prompt has been saved to: {export_path}. Please use an external AI to process it."
            except Exception as e:
                print(f"⚠️ Failed to export prompt: {e}")
                error_msg = output
            
            raise RuntimeError(error_msg)
            
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


class FallbackModel(BaseChatModel):
    """LangChain wrapper that tries multiple models in order if one fails"""
    models: List[BaseChatModel]
    
    @property
    def _llm_type(self) -> str:
        return "fallback"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        errors = []
        for i, model in enumerate(self.models):
            try:
                return model._generate(messages, stop, run_manager, **kwargs)
            except Exception as e:
                model_type = getattr(model, "_llm_type", "unknown")
                print(f"⚠️ Model {i+1} ({model_type}) failed: {e}")
                errors.append(str(e))
                if i < len(self.models) - 1:
                    next_model_type = getattr(self.models[i+1], "_llm_type", "unknown")
                    print(f"🔄 Switching to fallback model {i+2} ({next_model_type})...")
                    time.sleep(1)
                else:
                    print("❌ All models in fallback chain failed.")
        
        raise RuntimeError(f"All models failed. Errors: {'; '.join(errors)}")


def _create_model(provider: str, model_name: Optional[str] = None, temperature: float = 0.7, purpose: str = "general") -> BaseChatModel:
    """Internal helper to create a specific model instance"""
    if provider == "openrouter":
        name = model_name or (config.OPENROUTER_CODE_MODEL if purpose == "code" else config.OPENROUTER_GENERAL_MODEL)
        print(f"🔌 Initializing OpenRouter ({name})...")
        return ChatOpenAI(
            model=name,
            openai_api_key=config.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
            max_tokens=4000
        )
    elif provider == "gemini":
        name = model_name or (config.GEMINI_CODE_MODEL if purpose == "code" else config.GEMINI_GENERAL_MODEL)
        print(f"🔌 Initializing Gemini SDK ({name})...")
        return ChatGoogleGenerativeAI(
            model=name, 
            google_api_key=config.GOOGLE_API_KEY,
            temperature=temperature,
            request_timeout=120
        )
    elif provider == "gemini_cli":
        name = model_name or (config.GEMINI_CODE_MODEL if purpose == "code" else config.GEMINI_GENERAL_MODEL)
        print(f"🔌 Initializing Gemini CLI ({name})...")
        return GeminiCLIModel(model=name, temperature=temperature)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def get_llm(temperature=0.7, purpose="general"):
    """Factory function to get the configured LLM instance with fallback support"""
    print(f"🐛 DEBUG [get_llm]: Reading config.LLM_PROVIDER = {config.LLM_PROVIDER}")
    
    # 1. Start with the primary configuration
    primary_provider = config.LLM_PROVIDER
    
    # 2. Build the model sequence
    model_sequence = []
    
    # --- Add Primary Provider ---
    model_sequence.append((primary_provider, None))
    
    # --- Special Case: gemini_cli internal fallbacks ---
    if primary_provider == "gemini_cli":
        # If using a "Pro" model, try "Flash" as an internal fallback
        primary_model = config.GEMINI_CODE_MODEL if purpose == "code" else config.GEMINI_GENERAL_MODEL
        if "pro" in primary_model.lower():
            # Add Flash as a fast, reliable internal fallback
            model_sequence.append(("gemini_cli", "gemini-2.0-flash"))
            
    # --- Add Cross-Provider Fallbacks ---
    if config.OPENROUTER_API_KEY and primary_provider != "openrouter":
        model_sequence.append(("openrouter", None))
        
    if config.GOOGLE_API_KEY and primary_provider != "gemini":
        model_sequence.append(("gemini", None))
            
    # 3. Initialize all models in the sequence
    models = []
    for provider, model_name in model_sequence:
        try:
            models.append(_create_model(provider, model_name=model_name, temperature=temperature, purpose=purpose))
        except Exception as e:
            print(f"⚠️ Could not initialize provider {provider} ({model_name or 'default'}): {e}")
            
    if not models:
        raise ValueError("No valid LLM providers could be initialized.")
        
    if len(models) > 1:
        chain_names = [getattr(m, "_llm_type", "unknown") for m in models]
        print(f"🔗 Active Fallback Chain: {' -> '.join(chain_names)}")
        return FallbackModel(models=models)
        
    return models[0]
