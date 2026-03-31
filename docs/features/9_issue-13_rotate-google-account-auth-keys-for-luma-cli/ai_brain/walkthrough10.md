# Walkthrough: Gemini CLI OAuth Isolation Fix

I have successfully resolved the issue where `gemini-cli` was not respecting the profile isolation, leading to a single `~/.gemini/oauth_creds.json` being used for all accounts.

## 🛠️ Changes Implemented

### 🛡️ Profile Isolation via `HOME` Override
The `gemini-cli` (v0.35.3) does not support a specific configuration home variable. To achieve isolation, I have switched Luma to use a **`HOME` environment variable override** for subprocess calls.
- **New Logic**: When an OAuth profile is selected, Luma sets the `HOME` of the child process to `~/.config/gemini/{profile_name}/`.
- **Result**: The CLI tool is fooled into creating/using `.gemini/oauth_creds.json` inside that specific folder, keeping accounts completely separate.

### 🏠 Updated Base Path
- Changed the default OAuth profiles base path from `~/.luma/profiles` to **`~/.config/gemini`** to better align with standard Linux/Mac config locations and the user's manual tests.

### 🏷️ Config Alias Support
- Added support for **`GEMINI_OAUTH_PROFILES`** as an alias for `GEMINI_CLI_PROFILES` in `.env`, making it more intuitive for users setting up OAuth rotation.

## 🧪 Verification Results

### Automated Tests
I have updated the test suite to verify the new isolation logic and ensure compatibility with multiple credentials.

| Test Case | Status | Description |
|---|---|---|
| `test_gemini_cli_oauth_isolation` | ✅ Passed | Verified that `HOME` is correctly overridden and `GOOGLE_API_KEY` is removed for OAuth profiles. |
| `test_gemini_cli_skips_retry_on_rate_limit` | ✅ Passed | Verified robust retry/failover logic across multiple mixed credentials. |
| All other CLI tests | ✅ Passed | No regressions in timeout or response parsing. |

## 🚀 How to use multiple OAuth accounts
1. **Login to each account once** in your terminal using the `HOME` trick:
   ```bash
   HOME=~/.config/gemini/personal gemini auth
   HOME=~/.config/gemini/work gemini auth
   ```
2. **Update your `.env`**:
   ```bash
   GEMINI_OAUTH_PROFILES=personal,work
   ```
3. Luma will now automatically rotate between these accounts whenever a Rate Limit is hit.

---
**Task Status:** ✅ Successfully Completed.
**Notification:** Sending final Telegram update...
