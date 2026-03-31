# Implementation Plan: Rotate Google Account Auth Keys for Luma CLI

## Goal Description
Implement a **Hybrid Credential Rotation** system in Luma CLI. To maximize throughput and avoid Rate Limiting (429), Luma will cycle through a mixed pool of credentials: both `GOOGLE_API_KEYS` (from `.env`) and local **Gemini CLI OAuth Profiles** (Sign in with Google).

> [!NOTE]
> **Factcheck Conclusion**: You are entirely correct! Gemini API rate limits (Free tier RPM/RPD limits) are enforced **per Google Cloud Project** / Account. Multiple API keys created under the *same* account/project **share the same quota limit**. Therefore, using a combination of API Keys (from different accounts) and OAuth Profiles allows maximum flexibility and quota scale.

## Proposed Changes

### Configuration
#### [MODIFY] [config.py](file:///Users/oatrice/Software-projects/Luma/luma_core/config.py)
- Update configuration to read both:
  - `GOOGLE_API_KEYS` (comma-separated string mapping to API Keys).
  - `GEMINI_CLI_PROFILES` (comma-separated string mapping to `HOME` directory overrides for OAuth accounts).
- Provide safe defaults (e.g., parsing single `GOOGLE_API_KEY` if plural is missing, and defaulting profile to `['default']`).

---
### Core Logic (Credential Manager)
#### [NEW] [credential_manager.py](file:///Users/oatrice/Software-projects/Luma/luma_core/credential_manager.py)
- Create `CredentialStatus` dataclass:
  - `type`: Enum(`API_KEY`, `OAUTH_PROFILE`)
  - `value`: The key itself OR the profile folder name.
  - `is_active`, `cooldown_until`, `fail_count`.
- Create `CredentialManager` class initialized with both keys and profiles.
- Implement `get_next_credential()` with Round-robin logic across the mixed pool, skipping rate-limited credentials.
- Implement `mark_rate_limited(credential_value: str, retry_after: int)`.
- If all credentials in the pool are rate-limited, prompt the user: "All accounts and API keys are rate-limited. Would you like to add a new account API key? (Note: Keys from the same Google Account share the same quota)".

---
### LLM Client Rotation
#### [MODIFY] [llm.py](file:///Users/oatrice/Software-projects/Luma/luma_core/llm.py)
- Instantiate `CredentialManager` using data from `config`.
- **GeminiCLIModel**:
  - Fetch the next active credential from `CredentialManager`.
  - **If `API_KEY`**: Inject `env={"GOOGLE_API_KEY": cred.value, **os.environ}`. (Ensure `HOME` uses standard location).
  - **If `OAUTH_PROFILE`**: Inject `env={"HOME": f"/Users/name/.luma/profiles/{cred.value}", ...}`. (Ensure `GOOGLE_API_KEY` is completely unset so the CLI falls back to OAuth).
  - Monitor `stderr` or `output` for Rate Limit indicators (Error 429).
  - When rate limited, set the credential to cooldown and retry immediately with the next item in the pool.

## Verification Plan

### Automated Tests
- **`tests/test_key_manager.py`** [NEW]: Write unit tests (TDD: Red > Green > Refactor) to verify Round-robin switching, Cooldown timers, and exhausting all keys.
- **`tests/test_llm.py`** [MODIFY]: Mock the `gemini` CLI subprocess to return a rate limit error on the first call, and success on the second call. Assert that `Popen` was called twice, and the second call used the rotated API key in its environment.

### Manual Verification
- Add a dummy invalid key and a valid key into `.env` under `GOOGLE_API_KEYS`.
- Run a heavy generation task that hits the dummy key, verify logs print a warning and automatically switch to the valid key without stopping the process.
