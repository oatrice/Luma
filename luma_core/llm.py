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

from luma_core import config
from luma_core import usage_tracker
from luma_core.credential_manager import CredentialManager, AllCredentialsExhaustedError
from luma_core.error_classifier import classify_error, ErrorType

# Import new timeout/retry configuration
LUMA_LLM_TIMEOUT_SCALE = getattr(config, "LUMA_LLM_TIMEOUT_SCALE", 1.0)
LUMA_MAX_LLM_RETRIES = getattr(config, "LUMA_MAX_LLM_RETRIES", None)
LUMA_EXPORT_PROMPTS = getattr(config, "LUMA_EXPORT_PROMPTS", False)

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
CODEX_CLI_TIMEOUT = 300


def _coerce_ai_message(response: Any) -> AIMessage:
    if isinstance(response, BaseMessage):
        return response if isinstance(response, AIMessage) else AIMessage(content=response.content)

    content = getattr(response, "content", None)
    if content is None:
        content = str(response)
    return AIMessage(content=str(content))


def _flatten_messages_to_prompt(messages: List[BaseMessage]) -> str:
    prompt = ""
    for msg in messages:
        if hasattr(msg, "content"):
            prompt += f"{msg.content}\n"
        elif isinstance(msg, dict) and "content" in msg:
            prompt += f"{msg['content']}\n"
    return prompt


def _describe_gemini_credential(credential: Optional[Any]) -> str:
    if credential is None:
        return "environment default account"

    cred_type = getattr(credential, "type", None)
    cred_value = str(getattr(credential, "value", "unknown"))
    if cred_type == CredentialType.API_KEY:
        return f"{cred_value[:8]}..."
    return cred_value


def _get_gemini_retry_target(cred_manager: Optional[Any]) -> str:
    if cred_manager is None:
        return "environment default account"

    peek_next = getattr(cred_manager, "peek_next_credential", None)
    if callable(peek_next):
        try:
            next_credential = peek_next()
            return f"next credential: {_describe_gemini_credential(next_credential)}"
        except AllCredentialsExhaustedError:
            return "next available credential"

    return "next available credential"


def _log_gemini_attempt_failure(
    attempt: int,
    max_retries: int,
    error_type: str,
    detail: str = "",
) -> None:
    print(
        f"⚠️ [GeminiCLIModel] Attempt {attempt}/{max_retries} failed: "
        f"{error_type}{detail}"
    )


def _log_gemini_retry(cred_manager: Optional[Any]) -> None:
    print(f"🔁 [GeminiCLIModel] Retrying with {_get_gemini_retry_target(cred_manager)}")


class GeminiCLIModel(BaseChatModel):
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
        # --- FIX: Prevent duplicate run_manager if it's already in kwargs ---
        clean_kwargs = dict(kwargs)
        clean_kwargs.pop("run_manager", None)

        # Convert messages to a single prompt string
        prompt = _flatten_messages_to_prompt(messages)

        # Call gemini cli using STDIN to avoid OS ARG_MAX limits for large code payloads
        start_time = time.time()

        # ── Credential Rotation Setup ────────────────────────────────────────
        _has_credentials = bool(config.GOOGLE_API_KEYS or config.GEMINI_CLI_PROFILES)
        cred_manager = None
        if _has_credentials:
            try:
                if config.GEMINI_CLI_PROFILES:
                    try:
                        cred_manager = CredentialManager.get_instance(
                            oauth_profiles=config.GEMINI_CLI_PROFILES,
                            name="cli"
                        )
                    except Exception:
                        cred_manager = None
            except ValueError:
                cred_manager = None

        current_cred = None
        OAUTH_PROFILES_BASE = os.path.join(
            os.path.expanduser("~"), ".config", "gemini"
        )
        # ──────────────────────────────────────────────────────────────────────

        num_creds = len(cred_manager.pool) if cred_manager else 1
        # Respect LUMA_MAX_LLM_RETRIES if set, otherwise use credential pool size
        if LUMA_MAX_LLM_RETRIES is not None:
            max_retries = max(1, LUMA_MAX_LLM_RETRIES)
        else:
            max_retries = max(2, num_creds)

        process: Optional[subprocess.Popen] = None
        output: str = "Error: No attempts were made."
        for attempt in range(max_retries):
            base_timeout = MODEL_TIMEOUTS.get(self.model, 120)
            # Apply timeout scale with minimum of 10 seconds
            model_timeout = max(10, int(base_timeout * LUMA_LLM_TIMEOUT_SCALE))
            try:
                subprocess_env = dict(os.environ)
                # ── Build env with active credential ────────────────────────
                if cred_manager:
                    try:
                        current_cred = cred_manager.get_next_credential()
                        self.last_account_used = current_cred.value
                    except AllCredentialsExhaustedError:
                        _log_gemini_attempt_failure(
                            attempt + 1,
                            max_retries,
                            ErrorType.RATE_LIMIT.value,
                            " (all credentials exhausted)",
                        )
                        output = "Error: All credentials exhausted due to rate limiting."
                        break

                    if current_cred.type == CredentialType.API_KEY:
                        masked_account = _describe_gemini_credential(current_cred)
                        subprocess_env["GOOGLE_API_KEY"] = current_cred.value
                        subprocess_env.pop("GEMINI_CLI_PROFILE", None)
                    else:  # OAUTH_PROFILE
                        masked_account = _describe_gemini_credential(current_cred)
                        profile_home = os.path.join(OAUTH_PROFILES_BASE, current_cred.value)
                        subprocess_env["HOME"] = profile_home
                        subprocess_env.pop("GOOGLE_API_KEY", None)

                    print(
                        f"🔌 [GeminiCLIModel] Using account: {masked_account} (Model: {self.model}, Attempt: {attempt + 1}/{max_retries})"
                    )
                else:
                    print(
                        f"🔌 [GeminiCLIModel] Using environment default account (Model: {self.model}, Attempt: {attempt + 1}/{max_retries})"
                    )
                # ────────────────────────────────────────────────────────────

                cmd = [os.environ.get("GEMINI_CLI_BIN", "gemini"), "-m", self.model]
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=subprocess_env,
                )

                stdout, stderr = process.communicate(input=prompt, timeout=model_timeout)

                if process.returncode != 0:
                    error_type = classify_error(stderr)
                    error_detail = f" (Return code {process.returncode})"
                    if stderr.strip():
                        error_detail += f": {stderr.strip()}"
                    _log_gemini_attempt_failure(
                        attempt + 1,
                        max_retries,
                        error_type.value,
                        error_detail,
                    )

                    if error_type in (ErrorType.RATE_LIMIT, ErrorType.QUOTA_EXCEEDED):
                        if cred_manager and current_cred is not None:
                            cred_manager.mark_rate_limited(
                                current_cred.value, retry_after=300
                            )
                        output = f"Error calling Gemini CLI: {stderr}"
                        if attempt < max_retries - 1:
                            _log_gemini_retry(cred_manager)
                            time.sleep(1)
                            continue
                        break

                    output = f"Error calling Gemini CLI (Return Code {process.returncode}): {stderr}"
                    if attempt < max_retries - 1:
                        _log_gemini_retry(cred_manager)
                        time.sleep(2)
                        continue
                else:
                    output = stdout.strip()

                break

            except subprocess.TimeoutExpired:
                if process is not None:
                    process.kill()
                _log_gemini_attempt_failure(
                    attempt + 1,
                    max_retries,
                    ErrorType.TIMEOUT.value,
                    f" after {model_timeout}s",
                )
                output = "Error: Gemini CLI timed out."
                if attempt < max_retries - 1:
                    _log_gemini_retry(cred_manager)
                    time.sleep(2)
                    continue
            except Exception as e:
                _log_gemini_attempt_failure(
                    attempt + 1,
                    max_retries,
                    ErrorType.UNKNOWN.value,
                    f": {str(e)}",
                )
                output = f"Error: {str(e)}"
                break

        if "Error:" in output or "Error calling Gemini CLI" in output:
            raise RuntimeError(output)

        end_time = time.time()
        duration = end_time - start_time

        tokens_in = len(prompt) // 4
        tokens_out = len(output) // 4
        total_tokens = tokens_in + tokens_out

        global _session_gemini_cli_time, _session_gemini_cli_tokens
        _session_gemini_cli_time += duration
        _session_gemini_cli_tokens += total_tokens

        message = AIMessage(content=output)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])


def _format_codex_cli_error(stderr: str, returncode: int) -> str:
    err_text = (stderr or "").strip()
    lower_err = err_text.lower()

    auth_markers = (
        "login",
        "logged out",
        "not logged in",
        "authentication",
        "auth required",
        "expired",
    )
    if any(marker in lower_err for marker in auth_markers):
        return "Error: Codex CLI authentication failed or expired. Run `codex login` and try again."

    if err_text:
        return f"Error calling Codex CLI (Return Code {returncode}): {err_text}"

    return f"Error calling Codex CLI (Return Code {returncode})."


class CodexCLIModel(BaseChatModel):
    """LangChain wrapper for Codex CLI using non-interactive exec mode."""

    model: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.7)

    @property
    def _llm_type(self) -> str:
        return f"codex-cli:{self.model}" if self.model else "codex-cli"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        clean_kwargs = dict(kwargs)
        clean_kwargs.pop("run_manager", None)

        prompt = _flatten_messages_to_prompt(messages)
        cmd = [config.CODEX_CLI_BIN, "exec"]
        if self.model:
            cmd.extend(["-m", self.model])
        cmd.append("-")

        process: Optional[subprocess.Popen] = None
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=dict(os.environ),
            )
            stdout, stderr = process.communicate(input=prompt, timeout=CODEX_CLI_TIMEOUT)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Error: codex-cli is not installed. Install the `codex` CLI or set CODEX_CLI_BIN."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            if process is not None:
                process.kill()
            raise RuntimeError("Error: Codex CLI timed out.") from exc
        except Exception as exc:
            raise RuntimeError(f"Error: {str(exc)}") from exc

        if process.returncode != 0:
            raise RuntimeError(_format_codex_cli_error(stderr, process.returncode))

        message = AIMessage(content=stdout.strip())
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
        # --- FIX: Prevent duplicate run_manager if it's already in kwargs ---
        clean_kwargs = dict(kwargs)
        clean_kwargs.pop("run_manager", None)

        errors = []
        chain_length = len(self.models)
        current_path = os.getcwd()
        active_idx, last_reset = config.get_fallback_info(current_path)
        start_idx = active_idx if 0 <= active_idx < len(self.models) else 0

        ordered_indices = list(range(start_idx, len(self.models)))
        if start_idx > 0:
            ordered_indices.extend(range(0, start_idx))

        for position, i in enumerate(ordered_indices):
            model = self.models[i]
            call_id = uuid.uuid4().hex[:12]
            start_time = time.time()
            try:
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
                errors.append(f"Model {i + 1} ({model_type}): {str(e)}")
                if position < len(ordered_indices) - 1:
                    if is_retryable(error_type_enum):
                        time.sleep(1)

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
        # --- FIX: Prevent duplicate run_manager if it's already in kwargs ---
        clean_kwargs = dict(kwargs)
        clean_kwargs.pop("run_manager", None)

        if config.GOOGLE_API_KEYS:
            try:
                cred_manager = CredentialManager.get_instance(
                    api_keys=config.GOOGLE_API_KEYS,
                    name="api"
                )
            except ValueError:
                cred_manager = None
        else:
            cred_manager = None

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
                    break

            try:
                api_model = ChatGoogleGenerativeAI(
                    model=self.model,
                    google_api_key=current_key,
                    temperature=self.temperature,
                    request_timeout=MODEL_TIMEOUTS.get(self.model, 120),
                )
                response = api_model.invoke(messages, stop=stop, **clean_kwargs)
                return ChatResult(
                    generations=[ChatGeneration(message=_coerce_ai_message(response))]
                )

            except Exception as e:
                last_error = e
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower():
                    if cred_manager:
                        cred_manager.mark_rate_limited(current_key, retry_after=300)
                        continue

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
    provider = config.normalize_llm_provider(provider)

    if provider == "openrouter":
        name = model_name or (config.OPENROUTER_CODE_MODEL if purpose == "code" else config.OPENROUTER_GENERAL_MODEL)
        model = ChatOpenAI(
            model=name,
            openai_api_key=config.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=temperature,
            max_tokens=4000,
        )
        _attach_usage_metadata(model, provider=provider, model_name=name, purpose=purpose)
        return model
    elif provider == "gemini-api" or provider == "gemini":
        name = model_name or (config.GEMINI_CODE_MODEL if purpose == "code" else config.GEMINI_GENERAL_MODEL)
        model = GeminiAPIModel(model=name, temperature=temperature)
        _attach_usage_metadata(model, provider="gemini-api", model_name=name, purpose=purpose)
        return model
    elif provider == "gemini-cli":
        name = model_name or config.GEMINI_CLI_MODEL
        model = GeminiCLIModel(model=name, temperature=temperature)
        _attach_usage_metadata(model, provider=provider, model_name=name, purpose=purpose)
        return model
    elif provider == "codex-cli":
        name = model_name if model_name is not None else config.CODEX_CLI_MODEL
        model = CodexCLIModel(model=name, temperature=temperature)
        _attach_usage_metadata(
            model,
            provider=provider,
            model_name=name or "default",
            purpose=purpose,
        )
        return model
    elif provider == "openai":
        name = model_name or config.OPENAI_MODEL
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
    primary_provider = config.normalize_llm_provider(config.LLM_PROVIDER)
    model_sequence = [(primary_provider, None)]

    if primary_provider == "gemini-cli":
        for cli_model in config.AVAILABLE_GEMINI_CLI_MODELS:
            if cli_model != config.GEMINI_CLI_MODEL:
                model_sequence.append(("gemini-cli", cli_model))
    elif primary_provider == "codex-cli":
        model_sequence.extend(("gemini-cli", cli_model) for cli_model in config.AVAILABLE_GEMINI_CLI_MODELS)

    models = []
    for provider, model_name in model_sequence:
        try:
            models.append(_create_model(provider, model_name=model_name, temperature=temperature, purpose=purpose))
        except Exception:
            pass

    if not models:
        raise ValueError("No valid LLM providers could be initialized.")

    # If export mode is enabled, wrap the primary model with PromptExportModel
    if LUMA_EXPORT_PROMPTS:
        wrapped_model_name = getattr(models[0], "model", None)
        if wrapped_model_name:
            wrapped_model_name = getattr(wrapped_model_name, "model", "unknown")
        else:
            wrapped_model_name = getattr(models[0], "model", "unknown")
        return PromptExportModel(wrapped_model_name=wrapped_model_name or "unknown")

    if len(models) > 1:
        return FallbackModel(models=models)

    return TrackedModel(model=models[0])


def _attach_usage_metadata(model, provider, model_name, purpose):
    setattr(model, "_luma_provider", provider)
    setattr(model, "_luma_model_name", model_name)
    setattr(model, "_luma_purpose", purpose)


def _resolve_model_info(model):
    provider = getattr(model, "_luma_provider", None)
    model_name = getattr(model, "_luma_model_name", None)
    model_type = getattr(model, "_llm_type", None)
    purpose = getattr(model, "_luma_purpose", None)
    if not model_name:
        model_name = getattr(model, "model", None) or getattr(model, "model_name", None)

    if not provider and model_type:
        if "gemini-api" in model_type:
            provider = "gemini-api"
        elif "gemini-cli" in model_type:
            provider = "gemini-cli"
        elif "codex-cli" in model_type:
            provider = "codex-cli"
        elif "openrouter" in model_type:
            provider = "openrouter"
        elif "openai" in model_type:
            provider = "openai"

    return provider, model_name, model_type, purpose


def _mask_account(account):
    if not account:
        return None
    if account.startswith("AIza") or account.startswith("sk-") or len(account) > 24:
        return f"****{account[-4:]}"
    return account


class TrackedModel(BaseChatModel):
    model: BaseChatModel

    class Config:
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        return getattr(self.model, "_llm_type", "tracked")

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # --- FIX: Prevent duplicate run_manager if it's already in kwargs ---
        clean_kwargs = dict(kwargs)
        clean_kwargs.pop("run_manager", None)

        call_id = uuid.uuid4().hex[:12]
        start_time = time.time()
        start_dt = datetime.now(timezone.utc).isoformat()
        try:
            result = self.model._generate(messages, stop, run_manager, **clean_kwargs)
            duration_ms = (time.time() - start_time) * 1000
            provider, model_name, model_type, purpose = _resolve_model_info(self.model)
            account = getattr(self.model, "last_account_used", None)
            usage_tracker.record_llm_event(
                provider=provider, model=model_name, model_type=model_type, purpose=purpose,
                status="success", duration_ms=duration_ms, start_datetime=start_dt,
                end_datetime=datetime.now(timezone.utc).isoformat(), account=_mask_account(account),
                call_id=call_id, chain_index=0, chain_length=1,
            )
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            provider, model_name, model_type, purpose = _resolve_model_info(self.model)
            account = getattr(self.model, "last_account_used", None)
            usage_tracker.record_llm_event(
                provider=provider, model=model_name, model_type=model_type, purpose=purpose,
                status="error", duration_ms=duration_ms, start_datetime=start_dt,
                end_datetime=datetime.now(timezone.utc).isoformat(), account=_mask_account(account),
                error=str(e), error_type=classify_error(str(e)).value,
                call_id=call_id, chain_index=0, chain_length=1,
            )
            raise


class PromptExportModel(BaseChatModel):
    """Exports prompts to .md files instead of calling LLM.

    Useful when LLM calls are timing out - export prompts, use external AI,
    then paste responses back.
    """

    wrapped_model_name: str = Field(default="unknown")
    export_dir: str = Field(default=".luma/prompts")

    @property
    def _llm_type(self) -> str:
        return f"prompt-export:{self.wrapped_model_name}"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Export prompt to file and return placeholder response."""
        # Flatten messages to prompt text
        prompt_text = _flatten_messages_to_prompt(messages)

        # Create export directory
        export_path = os.path.join(os.getcwd(), self.export_dir)
        os.makedirs(export_path, exist_ok=True)

        # Generate unique filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        short_id = uuid.uuid4().hex[:8]
        filename = f"prompt_{timestamp}_{short_id}.md"
        filepath = os.path.join(export_path, filename)

        # Write prompt to markdown file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Prompt Export\n\n")
            f.write(f"**Model**: {self.wrapped_model_name}\n\n")
            f.write(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()}\n\n")
            f.write(f"---\n\n")
            f.write(prompt_text)
            f.write(f"\n\n---\n\n")
            f.write(f"# Instructions\n\n")
            f.write(f"1. Copy the prompt above and use it with your external AI\n")
            f.write(f"2. Paste the AI's response into a new file: `{filepath}.response.md`\n")
            f.write(f"3. Re-run Luma to load the response automatically\n")

        # Check if response file exists
        response_filepath = f"{filepath}.response.md"
        if os.path.exists(response_filepath):
            with open(response_filepath, "r", encoding="utf-8") as f:
                response_content = f.read().strip()
            print(f"📥 Loaded response from {response_filepath}")
            # Clean up response file after reading
            try:
                os.remove(response_filepath)
            except OSError:
                pass
            message = AIMessage(content=response_content)
        else:
            print(f"💾 [PROMPT EXPORTED] Prompt saved to: {filepath}")
            print(f"   Use external AI with this prompt, then paste response to: {response_filepath}")
            placeholder = (
                f"[PROMPT EXPORTED] Your prompt was saved to: {filepath}\n\n"
                f"Paste the AI response into: {response_filepath}\n"
                f"Then re-run to load the response."
            )
            message = AIMessage(content=placeholder)

        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
