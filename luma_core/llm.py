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
# ... rest of code (keeping it for context in the tool call)
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
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"🐛 DEBUG [GeminiCLIModel]: Generating response using model {self.model} (Payload length: {len(prompt)} chars, Attempt {attempt+1}/{max_retries})")
                
                # Always start a new session (no -r flag)
                cmd = ["gemini", "-m", self.model]
                    
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
                         
                    output = f"Error calling Gemini CLI (Return Code {process.returncode}): {stderr}"
                    if attempt < max_retries - 1:
                        print(f"🔄 Retrying... ({attempt+1}/{max_retries})")
                        time.sleep(2)
                        continue
                else:
                    output = stdout.strip()
                
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
        import time
        errors = []
        
        # Determine the start index (use the remembered index if it's within bounds, otherwise 0)
        start_idx = config.FALLBACK_ACTIVE_INDEX if 0 <= config.FALLBACK_ACTIVE_INDEX < len(self.models) else 0
        
        # --- Auto-Recovery Logic ---
        # If we've been using a fallback for more than 1 hour, try the primary model again
        if start_idx > 0:
            current_time = time.time()
            cooldown_period = 3600  # 1 hour in seconds
            elapsed = current_time - config.FALLBACK_LAST_RESET
            
            if elapsed > cooldown_period:
                print(f"🕒 Fallback memory is old ({elapsed/60:.1f}m). Trying to recover and use primary model...")
                start_idx = 0
        # ---------------------------
        
        # Phase 1: Try from the start_idx to the end
        if start_idx > 0:
            current_model_type = getattr(self.models[start_idx], "_llm_type", "unknown")
            print(f"🔄 Using remembered working model {start_idx+1} ({current_model_type})...")

        for i in range(start_idx, len(self.models)):
            model = self.models[i]
            try:
                result = model._generate(messages, stop, run_manager, **kwargs)
                if i != config.FALLBACK_ACTIVE_INDEX:
                    config.save_fallback_index(i) # Remember this success
                return result
            except Exception as e:
                model_type = getattr(model, "_llm_type", "unknown")
                print(f"⚠️ Model {i+1} ({model_type}) failed: {e}")
                errors.append(f"Model {i+1} ({model_type}): {str(e)}")
                if i < len(self.models) - 1:
                    next_model_type = getattr(self.models[i+1], "_llm_type", "unknown")
                    print(f"🔄 Switching to fallback model {i+2} ({next_model_type})...")
                    time.sleep(1)

        # Phase 2: If we started from a fallback (start_idx > 0) and failed, 
        # retry the primary models (0 to start_idx - 1)
        if start_idx > 0:
            print(f"🔄 Last working model (and subsequent fallbacks) failed. Retrying from the primary model...")
            for i in range(0, start_idx):
                model = self.models[i]
                try:
                    result = model._generate(messages, stop, run_manager, **kwargs)
                    config.save_fallback_index(i) # Remember this success
                    return result
                except Exception as e:
                    model_type = getattr(model, "_llm_type", "unknown")
                    print(f"⚠️ Model {i+1} ({model_type}) failed: {e}")
                    errors.append(f"Model {i+1} ({model_type}): {str(e)}")
                    if i < start_idx - 1:
                        next_model_type = getattr(self.models[i+1], "_llm_type", "unknown")
                        print(f"🔄 Switching to next primary fallback model {i+2} ({next_model_type})...")
                        time.sleep(1)

        print("❌ All models in fallback chain failed.")
        config.save_fallback_index(0) # Reset to primary on complete failure
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
            # Add Flash Lite as an even faster, cost-efficient internal fallback
            model_sequence.append(("gemini_cli", "gemini-2.5-flash-lite"))
            # Add auto and specialized gemini-2/3 aliases as last resorts in the CLI chain
            model_sequence.append(("gemini_cli", "auto"))
            model_sequence.append(("gemini_cli", "gemini-2"))
            model_sequence.append(("gemini_cli", "gemini-3"))
            
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
