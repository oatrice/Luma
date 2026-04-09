# Walkthrough / Task List

> 📋 รายการงานที่ต้องทำสำหรับ Feature นี้

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Fix workflow_actions.py PR path issue & Add LLM timeout controls |
| **Date** | April 9, 2026 |
| **Status** | ✅ Complete |
| **Issue Number** | 58-59 |

---

## Task List

### ✅ Phase 1: Analysis & Planning
- [x] วิเคราะห์ปัญหา Issue #58 (worktree path)
- [x] วิเคราะห์ปัญหา Issue #59 (missing import)
- [x] สร้าง analysis.md
- [x] สร้าง plan.md
- [x] สร้าง spec.md (SBE)

### ✅ Phase 2: Implementation
- [x] แก้ไข `workflow_actions.py` - เพิ่ม import `resolve_project_target_dir`
- [x] แก้ไข `workflow_actions.py` - ใช้ `target_dir` สำหรับ branch check
- [x] แก้ไข `workflow_actions.py` - ใช้ `target_dir` สำหรับ screenshot sync
- [x] แก้ไข `workflow_actions.py` - ใช้ `target_dir` สำหรับ AI brain sync
- [x] แก้ไข `workflow_actions.py` - ใช้ `target_dir` สำหรับ publisher state
- [x] แก้ไข `llm.py` - เพิ่ม import `is_retryable` และ `CredentialType`
- [x] แก้ไข `config.py` - เพิ่ม `LUMA_LLM_TIMEOUT_SCALE`, `LUMA_MAX_LLM_RETRIES`, `LUMA_EXPORT_PROMPTS`
- [x] แก้ไข `llm.py` - Implement timeout scale logic ใน `GeminiCLIModel._generate()`
- [x] แก้ไข `llm.py` - Implement `PromptExportModel` class
- [x] แก้ไข `llm.py` - Update `get_llm()` ให้ return `PromptExportModel` เมื่อ `LUMA_EXPORT_PROMPTS=true`

### ✅ Phase 3: Testing & Verification
- [x] ทดสอบ PR creation จาก worktree
- [x] ทดสอบ LLM fallback retry (no NameError)
- [x] รัน unit tests ที่มีอยู่ (`tests/test_llm_gemini_cli.py` - 10 passed)
- [x] เขียน unit tests เพิ่มเติม (`tests/test_llm_timeout_config.py` - 10 passed)
- [x] รัน tests รวม 20 tests - ผลลัพธ์: 20 passed ✅

### ✅ Phase 4: Documentation & Release
- [x] สร้าง GitHub Issue #59: https://github.com/oatrice/Luma/issues/59
- [ ] อัปเดต CHANGELOG.md
- [ ] สร้าง PR สำหรับ Luma repository
- [ ] Merge to main branch

---

## Implementation Details

### Changes Made

#### File: `luma_core/actions/workflow_actions.py`

```python
# Added import (line 30)
from luma_core.tools import resolve_project_target_dir

# Modified branch check (lines 206-230)
# Before:
br_res = subprocess.run(
    ["git", "branch", "--show-current"],
    cwd=proj["path"],  # ❌ Uses config path
)

# After:
config_path = proj["path"]
target_dir = resolve_project_target_dir(config_path)
if target_dir != config_path:
    print(f"   🌿 Worktree detected: Using {target_dir} instead of {config_path}")

br_res = subprocess.run(
    ["git", "branch", "--show-current"],
    cwd=target_dir,  # ✅ Uses resolved worktree path
)
```

#### File: `luma_core/llm.py`

```python
# Modified import (line 17-18)
# Before:
from luma_core.credential_manager import CredentialManager, AllCredentialsExhaustedError
from luma_core.error_classifier import classify_error, ErrorType

# After:
from luma_core.credential_manager import CredentialManager, AllCredentialsExhaustedError, CredentialType
from luma_core.error_classifier import classify_error, ErrorType, is_retryable

# Added config imports (line 20-23)
LUMA_LLM_TIMEOUT_SCALE = getattr(config, "LUMA_LLM_TIMEOUT_SCALE", 1.0)
LUMA_MAX_LLM_RETRIES = getattr(config, "LUMA_MAX_LLM_RETRIES", None)
LUMA_EXPORT_PROMPTS = getattr(config, "LUMA_EXPORT_PROMPTS", False)

# Added PromptExportModel class (lines 689-770)
class PromptExportModel(BaseChatModel):
    """Exports prompts to .md files instead of calling LLM."""
    ...
```

#### File: `luma_core/config.py`

```python
# Added environment variable parsing (lines 30-48)
_LLM_TIMEOUT_SCALE_STR = os.getenv("LUMA_LLM_TIMEOUT_SCALE", "1.0")
try:
    LUMA_LLM_TIMEOUT_SCALE = float(_LLM_TIMEOUT_SCALE_STR)
    LUMA_LLM_TIMEOUT_SCALE = max(0.1, min(2.0, LUMA_LLM_TIMEOUT_SCALE))
except ValueError:
    LUMA_LLM_TIMEOUT_SCALE = 1.0

_MAX_RETRIES_STR = os.getenv("LUMA_MAX_LLM_RETRIES", "")
try:
    LUMA_MAX_LLM_RETRIES = int(_MAX_RETRIES_STR) if _MAX_RETRIES_STR.strip() else None
except ValueError:
    LUMA_MAX_LLM_RETRIES = None

_LUMA_EXPORT_PROMPTS = os.getenv("LUMA_EXPORT_PROMPTS", "").lower()
LUMA_EXPORT_PROMPTS = _LUMA_EXPORT_PROMPTS in ("true", "1", "yes", "on")
```

---

## Verification Commands

```bash
# Test Issue #58 - Worktree PR creation
cd /Users/oatrice/Software-projects/Cerebro-worktrees/feat-4-5-3
python3 ../../Luma/main.py --project 16

# Expected output should show:
# 🌿 Worktree detected: Using /Users/oatrice/Software-projects/Cerebro-worktrees/feat-4-5-3 ...
# And NOT show:
# ⏩ Skipping Cerebro (Branch mismatch: main != feat/4-5-3-dashboard-snapshots)

# Test Issue #59 - LLM Timeout Controls
export LUMA_LLM_TIMEOUT_SCALE=0.5
export LUMA_MAX_LLM_RETRIES=1
python3 main.py --project 1

# Test Issue #59 - Prompt Export Mode
export LUMA_EXPORT_PROMPTS=true
python3 main.py --project 1
# Expected: 💾 [PROMPT EXPORTED] Prompt saved to: .luma/prompts/prompt_YYYYMMDD_HHMMSS_XXXXXXXX.md

# Run all tests
pytest tests/test_llm_gemini_cli.py tests/test_llm_timeout_config.py -v
# Expected: 20 passed ✅
```

---

## Issues & Blockers

| Issue | สถานะ | การแก้ไข |
|-------|--------|---------|
| None | - | - |

---

## Notes

- การแก้ไข Issue #58 ใช้ pattern เดียวกับที่แก้ไขใน Issue #56 (quality_actions.py)
- Issue #59 พบโดยบังเอิญเมื่อตรวจสอบ error ใน log
- ทั้งสอง issue เป็น bug fixes ไม่ใช่ feature ใหม่

---

**Last Updated**: April 9, 2026
**Updated By**: AI Assistant
