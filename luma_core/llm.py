import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import Field

from . import config
from . import usage_tracker
from .error_classifier import classify_error, ErrorType, is_retryable
from .credential_manager import (
    CredentialManager,
    CredentialType,
    AllCredentialsExhaustedError,
)

# Store session metrics for Gemini CLI
_session_gemini_cli_time = 0.0
_session_gemini_cli_tokens = 0
_current_gemini_session_id = None

MODEL_TIMEOUTS = {
    "gemini-2.0-flash-lite-preview-02-05": 30,
    "gemini-2.5-flash": 60,
    "gemini-3-flash-preview": 90,
    "gemini-2.5-pro": 120,
    "gemini-3-pro-preview": 300,
}


class GeminiCLIModel(BaseChatModel):
    # ... rest of code (keeping it for context in the tool call)
    """LangChain wrapper for the gemini commands using subprocess"""

    model: str = Field(default="gemini-2.5-pro")
    temperature: float = Field(default=0.7)
    last_account_used: Optional[str] = None

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

        # ── Credential Rotation Setup ────────────────────────────────────────
        _has_credentials = bool(config.GOOGLE_API_KEYS or config.GEMINI_CLI_PROFILES)
        if _has_credentials:
            try:
                # Reset instance to pick up latest config (e.g. if .env changed)
                if config.GEMINI_CLI_PROFILES:
                    try:
                        cred_manager = CredentialManager.get_instance(
                            oauth_profiles=config.GEMINI_CLI_PROFILES,
                            name="cli"
                        )
                    except Exception:
                        cred_manager = None  # empty pool — fall through to bare env
                else:
                    cred_manager = None
            except ValueError:
                cred_manager = None  # empty pool — fall through to bare env
        else:
            cred_manager = None

        current_cred = None
        OAUTH_PROFILES_BASE = os.path.join(
            os.path.expanduser("~"), ".config", "gemini"
        )
        # ──────────────────────────────────────────────────────────────────────

        # Dynamic max_retries based on available credentials
        num_creds = len(cred_manager.pool) if cred_manager else 1
        max_retries = max(2, num_creds)

        process: Optional[subprocess.Popen] = None
        output: str = "Error: No attempts were made."
        for attempt in range(max_retries):
            try:
                print(
                    f"🐛 DEBUG [GeminiCLIModel]: Generating response using model {self.model} (Payload length: {len(prompt)} chars, Attempt {attempt + 1}/{max_retries})"
                )

                # Always start a new session (no -r flag)
                cmd = ["/opt/homebrew/bin/gemini", "-m", self.model]

                # ── Build env with active credential ────────────────────────
                if cred_manager:
                    try:
                        current_cred = cred_manager.get_next_credential()
                        self.last_account_used = current_cred.value
                    except AllCredentialsExhaustedError:
                        print(
                            "⚠️ All credentials are rate-limited. "
                            "Please add a new API key from a DIFFERENT Google Account, "
                            "or wait for the cooldown to expire."
                        )
                        output = "Error: All credentials exhausted due to rate limiting."
                        break

                    subprocess_env = dict(os.environ)
                    if current_cred.type == CredentialType.API_KEY:
                        masked_account = f"{current_cred.value[:8]}..."
                        subprocess_env["GOOGLE_API_KEY"] = current_cred.value
                        subprocess_env.pop("GEMINI_CLI_PROFILE", None)
                    else:  # OAUTH_PROFILE
                        masked_account = current_cred.value
                        profile_home = os.path.join(OAUTH_PROFILES_BASE, current_cred.value)
                        subprocess_env["HOME"] = profile_home
                        subprocess_env.pop("GOOGLE_API_KEY", None)  # force OAuth fallback

                    print(
                        f"🔌 [GeminiCLIModel] Using account: {masked_account} (Model: {self.model}, Attempt: {attempt + 1}/{max_retries})"
                    )
                else:
                    subprocess_env = dict(os.environ)  # bare env — original behavior
                    print(
                        f"🔌 [GeminiCLIModel] Using environment default account (Model: {self.model}, Attempt: {attempt + 1}/{max_retries})"
                    )
                # ────────────────────────────────────────────────────────────

                # Use Popen to pipe prompt via stdin
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=subprocess_env,
                )

                # Send prompt and wait for completion
                model_timeout = MODEL_TIMEOUTS.get(self.model, 120)
                stdout, stderr = process.communicate(input=prompt, timeout=model_timeout)

                if process.returncode != 0:
                    print(f"⚠️ Gemini CLI Error Output: {stderr}")

                    error_type = classify_error(stderr)
                    if error_type in (ErrorType.RATE_LIMIT, ErrorType.QUOTA_EXCEEDED):
                        # Mark credential and retry immediately with the next one
                        if cred_manager and current_cred is not None:
                            cred_manager.mark_rate_limited(
                                current_cred.value, retry_after=300
                            )
                            print(
                                f"🔄 Credential '{current_cred.value}' rate-limited. "
                                "Switching to next available credential..."
                            )
                            if attempt < max_retries - 1:
                                time.sleep(1)
                                continue  # Try with next credential

                        output = f"Error calling Gemini CLI: {stderr}"
                        break  # Non-retryable or no more attempts allowed

                    output = f"Error calling Gemini CLI (Return Code {process.returncode}): {stderr}"
                    if attempt < max_retries - 1:
                        print(f"🔄 Retrying... ({attempt + 1}/{max_retries})")
                        time.sleep(2)
                        continue
                else:
                    output = stdout.strip()

                break  # Exit retry loop on success or non-retryable error

            except subprocess.TimeoutExpired:
                if process is not None:
                    process.kill()
                model_timeout = MODEL_TIMEOUTS.get(self.model, 300)
                print(
                    f"⚠️ Gemini CLI Timeout Expired ({model_timeout}s) - Attempt {attempt + 1}/{max_retries}"
                )
                output = f"Error: Gemini CLI timed out after {model_timeout} seconds."
                if attempt < max_retries - 1:
                    print("🔄 Retrying due to timeout...")
                    time.sleep(2)
                    continue
            except Exception as e:
                print(f"⚠️ Gemini CLI Exception: {str(e)}")
                output = f"Error: {str(e)}"
                break  # Don't retry on random exceptions

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
                            if (
                                d.startswith(f"{state.active_issue.number}_")
                                or f"issue-{state.active_issue.number}" in d
                            ):
                                export_dir = os.path.join(features_root, d, "ai_brain")
                                break
            except Exception as e:
                print(f"⚠️ Could not resolve feature dir for export: {e}")

            if not export_dir:
                export_dir = os.path.abspath(
                    os.path.join(os.getcwd(), "docs", "ai_brain")
                )

            os.makedirs(export_dir, exist_ok=True)
            export_path = os.path.join(export_dir, f"luma_failed_prompt_{timestamp}.md")

            print(
                f"❌ Gemini CLI failed after retries. Exporting prompt to {export_path} for external AI."
            )
            try:
                with open(export_path, "w") as f:
                    f.write(prompt)
                error_msg = (
                    output
                    + f"\n\n[SYSTEM] Gemini CLI failed to process the request. The prompt has been saved to: {export_path}. Please use an external AI to process it."
                )
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

        print(
            f"⏱️ Gemini CLI Response Time: {duration:.2f}s | 🪙 Tokens Used (Approx): {total_tokens} (In: {tokens_in}, Out: {tokens_out})"
        )

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
        chain_length = len(self.models)

        # Determine the start index using project-specific info
        current_path = os.getcwd()
        active_idx, last_reset = config.get_fallback_info(current_path)
        start_idx = active_idx if 0 <= active_idx < len(self.models) else 0

        # --- Auto-Recovery Logic ---
        # If we've been using a fallback for more than 1 hour, try the primary model again
        if start_idx > 0:
            current_time = time.time()
            cooldown_period = 3600  # 1 hour in seconds
            elapsed = current_time - last_reset

            if elapsed > cooldown_period:
                print(
                    f"🕒 Fallback memory is old ({elapsed / 60:.1f}m). Trying to recover and use primary model for this project..."
                )
                start_idx = 0
        # ---------------------------

        # Phase 1: Try from the start_idx to the end
        if start_idx > 0:
            current_model_type = getattr(self.models[start_idx], "_llm_type", "unknown")
            print(
                f"🔄 Using remembered working model {start_idx + 1} ({current_model_type}) for this project..."
            )

        for i in range(start_idx, len(self.models)):
            model = self.models[i]
            call_id = uuid.uuid4().hex[:12]
            start_time = time.time()
            try:
                # --- FIX: Prevent duplicate run_manager if it's already in kwargs ---
                clean_kwargs = dict(kwargs)
                clean_kwargs.pop("run_manager", None)
                # ------------------------------------------------------------------
                result = model._generate(messages, stop, run_manager, **clean_kwargs)
                duration_ms = (time.time() - start_time) * 1000
                provider, model_name, model_type, purpose = _resolve_model_info(model)
                account = getattr(model, "last_account_used", None)
                usage_tracker.record_llm_event(
                    provider=provider,
                    model=model_name,
                    model_type=model_type,
                    purpose=purpose,
                    status="success",
                    duration_ms=duration_ms,
                    call_id=call_id,
                    chain_index=i,
                    chain_length=chain_length,
                    account=_mask_account(account),
                )
                # Success! Remember this index for THIS project
                config.save_fallback_index(i, current_path)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                provider, model_name, model_type, purpose = _resolve_model_info(model)
                account = getattr(model, "last_account_used", None)
                error_type_enum = classify_error(str(e))
                usage_tracker.record_llm_event(
                    provider=provider,
                    model=model_name,
                    model_type=model_type,
                    purpose=purpose,
                    status="error",
                    duration_ms=duration_ms,
                    error=str(e),
                    error_type=error_type_enum.value,
                    call_id=call_id,
                    chain_index=i,
                    chain_length=chain_length,
                    account=_mask_account(account),
                )
                model_type = getattr(model, "_llm_type", "unknown")
                print(f"⚠️ Model {i + 1} ({model_type}) failed [{error_type_enum.value}]: {e}")
                errors.append(f"Model {i + 1} ({model_type}): {str(e)}")
                if i < len(self.models) - 1:
                    next_model_type = getattr(
                        self.models[i + 1], "_llm_type", "unknown"
                    )
                    print(
                        f"🔄 Switching to fallback model {i + 2} ({next_model_type})..."
                    )
                    if is_retryable(error_type_enum):
                        time.sleep(1)

        # Phase 2: If we started from a fallback (start_idx > 0) and failed,
        # retry the primary models (0 to start_idx - 1)
        if start_idx > 0:
            print(
                "🔄 Last working model (and subsequent fallbacks) failed. Retrying from the primary model..."
            )
            for i in range(0, start_idx):
                model = self.models[i]
                call_id = uuid.uuid4().hex[:12]
                try:
                    # --- FIX: Prevent duplicate run_manager if it's already in kwargs ---
                    clean_kwargs = dict(kwargs)
                    clean_kwargs.pop("run_manager", None)
                    # ------------------------------------------------------------------
                    result = model._generate(messages, stop, run_manager, **clean_kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    provider, model_name, model_type, purpose = _resolve_model_info(
                        model
                    )
                    account = getattr(model, "last_account_used", None)
                    usage_tracker.record_llm_event(
                        provider=provider,
                        model=model_name,
                        model_type=model_type,
                        purpose=purpose,
                        status="success",
                        duration_ms=duration_ms,
                        call_id=call_id,
                        chain_index=i,
                        chain_length=chain_length,
                        account=_mask_account(account),
                    )
                    config.save_fallback_index(i, current_path)  # Remember this success
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    provider, model_name, model_type, purpose = _resolve_model_info(
                        model
                    )
                    account = getattr(model, "last_account_used", None)
                    error_type_enum = classify_error(str(e))
                    usage_tracker.record_llm_event(
                        provider=provider,
                        model=model_name,
                        model_type=model_type,
                        purpose=purpose,
                        status="error",
                        duration_ms=duration_ms,
                        error=str(e),
                        error_type=error_type_enum.value,
                        call_id=call_id,
                        chain_index=i,
                        chain_length=chain_length,
                        account=_mask_account(account),
                    )
                    model_type = getattr(model, "_llm_type", "unknown")
                    print(f"⚠️ Model {i + 1} ({model_type}) failed [{error_type_enum.value}]: {e}")
                    errors.append(f"Model {i + 1} ({model_type}): {str(e)}")
                    if i < start_idx - 1:
                        next_model_type = getattr(
                            self.models[i + 1], "_llm_type", "unknown"
                        )
                        print(
                            f"🔄 Switching to next primary fallback model {i + 2} ({next_model_type})..."
                        )
                        if is_retryable(error_type_enum):
                            time.sleep(1)

        print("❌ All models in fallback chain failed.")
        config.save_fallback_index(
            0, current_path
        )  # Reset to primary on complete failure
        raise RuntimeError(f"All models failed. Errors: {'; '.join(errors)}")


class GeminiAPIModel(BaseChatModel):
    """Wrapper for ChatGoogleGenerativeAI that supports credential rotation"""

    model: str = Field(default="gemini-1.5-pro")
    temperature: float = Field(default=0.7)
    last_account_used: Optional[str] = None

    @property
    def _llm_type(self) -> str:
        return f"gemini-api:{self.model}"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # ── Credential Rotation Setup ────────────────────────────────────────
        if config.GOOGLE_API_KEYS:
            try:
                # Use a separate named pool for API keys to avoid mixing with CLI profiles
                cred_manager: Optional[CredentialManager] = CredentialManager.get_instance(
                    api_keys=config.GOOGLE_API_KEYS,
                    name="api"
                )
            except ValueError:
                cred_manager = None
        else:
            cred_manager = None
        # ──────────────────────────────────────────────────────────────────────

        num_creds = len(cred_manager.pool) if cred_manager else 1
        max_retries = max(2, num_creds)

        last_error = None
        for attempt in range(max_retries):
            current_key = config.GOOGLE_API_KEY
            if cred_manager:
                try:
                    current_cred = cred_manager.get_next_credential()
                    current_key = current_cred.value
                    self.last_account_used = current_key
                except AllCredentialsExhaustedError:
                    print("⚠️ All Gemini API keys are rate-limited.")
                    break

            try:
                masked_account = f"{current_key[:8]}..." if current_key else "default"
                print(
                    f"🔌 [GeminiAPIModel] Using account: {masked_account} (Model: {self.model}, Attempt: {attempt + 1}/{max_retries})"
                )
                api_model = ChatGoogleGenerativeAI(
                    model=self.model,
                    google_api_key=current_key,
                    temperature=self.temperature,
                    request_timeout=MODEL_TIMEOUTS.get(self.model, 120),
                )
                # --- FIX: Prevent duplicate run_manager if it's already in kwargs ---
                clean_kwargs = dict(kwargs)
                clean_kwargs.pop("run_manager", None)
                # ------------------------------------------------------------------
                response = api_model.invoke(
                    messages, stop=stop, **clean_kwargs
                )
                return ChatResult(generations=[ChatGeneration(message=response)])

            except Exception as e:
                last_error = e
                err_str = str(e)
                print(f"⚠️ Gemini API Error (Attempt {attempt + 1}): {err_str}")

                # Check if it's a rate limit error (429)
                if "429" in err_str or "quota" in err_str.lower():
                    if cred_manager:
                        cred_manager.mark_rate_limited(current_key, retry_after=300)
                        print(
                            f"🔄 Key '{current_key[:8]}...' rate-limited. "
                            "Switching to next available credential..."
                        )
                        continue

                # For other errors, maybe retry once or just fail
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                break

        raise last_error or RuntimeError("Gemini API failed after retries")


def _create_model(
    provider: str,
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    purpose: str = "general",
) -> BaseChatModel:
    """Internal helper to create a specific model instance"""
    if provider == "openrouter":
        name = model_name or (
            config.OPENROUTER_CODE_MODEL
            if purpose == "code"
            else config.OPENROUTER_GENERAL_MODEL
        )
        print(f"🔌 Initializing OpenRouter ({name})...")
        model = ChatOpenAI(
            model=name,
            openai_api_key=config.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
            max_tokens=4000,
        )
        _attach_usage_metadata(model, provider=provider, model_name=name, purpose=purpose)
        return model
    elif provider == "gemini-api":
        name = model_name or (
            config.GEMINI_CODE_MODEL
            if purpose == "code"
            else config.GEMINI_GENERAL_MODEL
        )
        print(f"🔌 Initializing Gemini API Rotation Wrapper ({name})...")
        model = GeminiAPIModel(model=name, temperature=temperature)
        _attach_usage_metadata(model, provider="gemini-api", model_name=name, purpose=purpose)
        return model
    elif provider == "gemini_cli":
        name = model_name or config.GEMINI_CLI_MODEL
        print(f"🔌 Initializing Gemini CLI ({name})...")
        model = GeminiCLIModel(model=name, temperature=temperature)
        _attach_usage_metadata(model, provider=provider, model_name=name, purpose=purpose)
        return model
    elif provider == "openai":
        name = model_name or config.OPENAI_MODEL
        print(f"🔌 Initializing OpenAI ({name})...")
        model = ChatOpenAI(
            model=name,
            openai_api_key=config.OPENAI_API_KEY,
            temperature=temperature,
            max_tokens=4000,
        )
        _attach_usage_metadata(model, provider=provider, model_name=name, purpose=purpose)
        return model
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

    # --- Tier 1: gemini_cli — cycle through all remaining CLI models ---
    if primary_provider == "gemini_cli":
        primary_model = config.GEMINI_CLI_MODEL
        for cli_model in config.AVAILABLE_GEMINI_CLI_MODELS:
            if cli_model != primary_model:
                model_sequence.append(("gemini_cli", cli_model))

    # --- Tier 2: OpenRouter (if configured) ---
    if config.OPENROUTER_API_KEY and primary_provider != "openrouter":
        model_sequence.append(("openrouter", None))

    # --- Tier 3: OpenAI (if configured) ---
    if config.OPENAI_API_KEY and primary_provider != "openai":
        model_sequence.append(("openai", None))

    # --- Tier 4: Gemini API direct — pro → flash → lite ---
    if config.GOOGLE_API_KEY and primary_provider != "gemini-api":
        if config.GEMINI_GENERAL_MODEL:
            model_sequence.append(("gemini-api", config.GEMINI_GENERAL_MODEL))

    # 3. Initialize all models in the sequence
    models = []
    for provider, model_name in model_sequence:
        try:
            models.append(
                _create_model(
                    provider,
                    model_name=model_name,
                    temperature=temperature,
                    purpose=purpose,
                )
            )
        except Exception as e:
            print(
                f"⚠️ Could not initialize provider {provider} ({model_name or 'default'}): {e}"
            )

    if not models:
        raise ValueError("No valid LLM providers could be initialized.")

    if len(models) > 1:
        chain_names = [getattr(m, "_llm_type", "unknown") for m in models]
        print(f"🔗 Active Fallback Chain: {' -> '.join(chain_names)}")
        return FallbackModel(models=models)

    return TrackedModel(model=models[0])


def _attach_usage_metadata(
    model: BaseChatModel,
    *,
    provider: Optional[str],
    model_name: Optional[str],
    purpose: Optional[str],
) -> None:
    try:
        setattr(model, "_luma_provider", provider)
        setattr(model, "_luma_model_name", model_name)
        setattr(model, "_luma_purpose", purpose)
    except Exception:
        pass


def _resolve_model_info(
    model: BaseChatModel,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    provider = getattr(model, "_luma_provider", None)
    model_name = getattr(model, "_luma_model_name", None)
    model_type = getattr(model, "_llm_type", None)
    purpose = getattr(model, "_luma_purpose", None)
    if not model_name:
        model_name = getattr(model, "model", None) or getattr(model, "model_name", None)
    if not provider and model_type:
        if "openrouter" in str(model_type):
            provider = "openrouter"
        elif "openai" in str(model_type):
            provider = "openai"
        elif "gemini-api" in str(model_type):
            provider = "gemini-api"
        elif "gemini" in str(model_type):
            # Fallback for older Log types or other Gemini wrappers
            provider = "gemini-api"
        elif "gemini-cli" in str(model_type):
            provider = "gemini-cli"
    return provider, model_name, model_type, purpose


def _mask_account(account: Optional[str]) -> Optional[str]:
    """
    Returns a masked version of the account string.
    - If it's an API key (starts with 'AIza' or length > 24), show last 4 chars.
    - Otherwise (OAuth profile name), keep as is.
    """
    if not account:
        return None
    # Google API keys usually start with AIza and are long.
    # OpenAI keys start with sk- and are also long.
    if account.startswith("AIza") or account.startswith("sk-") or len(account) > 24:
        # Show only last 4 chars for security
        return f"****{account[-4:]}"
    return account


class TrackedModel(BaseChatModel):
    """Wrap a single model to record success/failure usage stats."""

    model: BaseChatModel

    class Config:
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        return getattr(self.model, "_llm_type", "tracked")

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        try:
            return self.model._identifying_params  # type: ignore[attr-defined]
        except Exception:
            return {"model": getattr(self.model, "model", None)}

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:

        call_id = uuid.uuid4().hex[:12]
        start_time = time.time()
        start_dt = datetime.now(timezone.utc).isoformat()
        try:
            # --- FIX: Prevent duplicate run_manager if it's already in kwargs ---
            clean_kwargs = dict(kwargs)
            clean_kwargs.pop("run_manager", None)
            # ------------------------------------------------------------------
            result = self.model._generate(messages, stop, run_manager, **clean_kwargs)
            duration_ms = (time.time() - start_time) * 1000
            end_dt = datetime.now(timezone.utc).isoformat()
            provider, model_name, model_type, purpose = _resolve_model_info(self.model)
            account = getattr(self.model, "last_account_used", None)
            usage_tracker.record_llm_event(
                provider=provider,
                model=model_name,
                model_type=model_type,
                purpose=purpose,
                status="success",
                duration_ms=duration_ms,
                start_datetime=start_dt,
                end_datetime=end_dt,
                account=_mask_account(account),
                call_id=call_id,
                chain_index=0,
                chain_length=1,
            )
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            end_dt = datetime.now(timezone.utc).isoformat()
            provider, model_name, model_type, purpose = _resolve_model_info(self.model)
            account = getattr(self.model, "last_account_used", None)
            error_type_enum = classify_error(str(e))
            usage_tracker.record_llm_event(
                provider=provider,
                model=model_name,
                model_type=model_type,
                purpose=purpose,
                status="error",
                duration_ms=duration_ms,
                start_datetime=start_dt,
                end_datetime=end_dt,
                account=_mask_account(account),
                error=str(e),
                error_type=error_type_enum.value,
                call_id=call_id,
                chain_index=0,
                chain_length=1,
            )
            raise
