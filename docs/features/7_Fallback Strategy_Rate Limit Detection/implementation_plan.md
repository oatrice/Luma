# Smart Fallback Strategy + Rate Limit Detection

ปรับปรุง Luma LLM fallback chain ให้มี rate limit detection, per-model timeout, และ error classification

## User Review Required

> [!IMPORTANT]
> **Model chain order ใหม่:** `gemini-3-flash-preview` → `gemini-2.5-flash` → `gemini-2.5-pro` → `gemini-3-pro-preview` → `gemini-2.5-flash-lite`
> เลื่อน `gemini-2.5-flash` ขึ้นมาเป็น #2 (ตามข้อมูล stat: เสถียรสุด, Avg 22s, 0 error) และเลื่อน `gemini-3-pro-preview` ลงไปเป็น #4 (เผื่อไว้ใช้กับงานหนัก ไม่ตัดออก)

> [!IMPORTANT]
> **Rate limit detection keywords:** จะตรวจจับ `429`, `RESOURCE_EXHAUSTED`, `quota`, `rate limit`, `Too Many Requests` จาก error message — ถ้าเจอจะ skip retry ภายใน model เดียวกัน แล้วข้ามไป fallback ทันที

## Proposed Changes

### Error Classification Module

#### [NEW] [error_classifier.py](file:///Users/oatrice/Software-projects/Luma/luma_core/error_classifier.py)

สร้าง module ใหม่สำหรับจำแนกประเภท error:
- `ErrorType` enum: `RATE_LIMIT`, `TIMEOUT`, `QUOTA_EXCEEDED`, `OUTPUT_TRUNCATED`, `UNKNOWN`
- `classify_error(error_msg: str) -> ErrorType` — ตรวจ keyword จาก error string
- `is_retryable(error_type: ErrorType) -> bool` — `TIMEOUT` retryable, `RATE_LIMIT`/`QUOTA_EXCEEDED` ไม่ retryable (ข้ามไป fallback เลย)

---

### LLM Fallback Improvements

#### [MODIFY] [llm.py](file:///Users/oatrice/Software-projects/Luma/luma_core/llm.py)

1. **`GeminiCLIModel._generate()`** — เปลี่ยน timeout จากค่าเดียว 300s → ใช้ `MODEL_TIMEOUTS` dict:
   - `gemini-3-flash-preview`: 180s (3 นาที)
   - `gemini-2.5-flash`: 120s (2 นาที)
   - `gemini-2.5-pro`: 300s (5 นาที)
   - `gemini-3-pro-preview`: 420s (7 นาที)
   - `gemini-2.5-flash-lite`: 90s (1.5 นาที)
   - default: 300s

2. **`GeminiCLIModel._generate()`** — เมื่อเจอ rate limit error (จาก `classify_error`), **ไม่ retry** ภายใน model → raise ทันทีเพื่อให้ `FallbackModel` จัดการ

3. **`FallbackModel._generate()`** — เพิ่ม error classification ใน catch block:
   - ถ้า `RATE_LIMIT`/`QUOTA_EXCEEDED` → log ด้วย `usage_tracker` พร้อม `error_type` field → ข้ามไป model ถัดไป **ไม่ต้องรอ** `time.sleep(1)`
   - ถ้า `TIMEOUT` → log แล้ว fallback ปกติ

---

### Model Chain Order

#### [MODIFY] [config.py](file:///Users/oatrice/Software-projects/Luma/luma_core/config.py)

เปลี่ยนลำดับ `AVAILABLE_GEMINI_CLI_MODELS`:

```diff
 AVAILABLE_GEMINI_CLI_MODELS = [
     "gemini-3-flash-preview",
-    "gemini-3-pro-preview",
-    "gemini-2.5-pro",
     "gemini-2.5-flash",
+    "gemini-2.5-pro",
+    "gemini-3-pro-preview",
     "gemini-2.5-flash-lite",
 ]
```

---

### Usage Tracker Enhancement

#### [MODIFY] [usage_tracker.py](file:///Users/oatrice/Software-projects/Luma/luma_core/usage_tracker.py)

เพิ่ม `error_type` field ใน `record_llm_event()`:
- parameter ใหม่: `error_type: Optional[str] = None`
- บันทึกลง event dict เมื่อมีค่า

---

### Tests (TDD)

#### [NEW] [test_error_classifier.py](file:///Users/oatrice/Software-projects/Luma/tests/test_error_classifier.py)

- `test_classify_rate_limit_429` — error ที่มี "429" → `RATE_LIMIT`
- `test_classify_resource_exhausted` — "RESOURCE_EXHAUSTED" → `RATE_LIMIT`
- `test_classify_quota_exceeded` — "quota" → `QUOTA_EXCEEDED`
- `test_classify_timeout` — "timed out" → `TIMEOUT`
- `test_is_retryable_timeout` — `TIMEOUT` → `True`
- `test_is_retryable_rate_limit` — `RATE_LIMIT` → `False`

#### [MODIFY] [test_llm_gemini_cli.py](file:///Users/oatrice/Software-projects/Luma/tests/test_llm_gemini_cli.py)

- `test_gemini_cli_uses_model_specific_timeout` — ตรวจว่า timeout ที่ส่งเข้า `communicate()` ตรงกับ `MODEL_TIMEOUTS`
- `test_gemini_cli_skips_retry_on_rate_limit` — ตรวจว่าเมื่อเจอ rate limit error จะไม่ retry

#### [MODIFY] [test_usage_tracker.py](file:///Users/oatrice/Software-projects/Luma/tests/test_usage_tracker.py)

- `test_record_llm_event_includes_error_type` — ตรวจว่า `error_type` ถูกบันทึก

## Verification Plan

### Automated Tests

```bash
cd /Users/oatrice/Software-projects/Luma
python -m pytest tests/test_error_classifier.py -v
python -m pytest tests/test_llm_gemini_cli.py -v
python -m pytest tests/test_usage_tracker.py -v
python -m pytest tests/ -v  # full suite
```

### Manual Verification

ไม่จำเป็นสำหรับ iteration นี้ — ทุกอย่างทดสอบได้ด้วย unit tests กับ mocked subprocess
