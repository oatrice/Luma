# Implementation Plan: Issue #29 Headless Action-Level Logging

> Status: Completed

## สถาปัตยกรรมที่เลือกใช้

งานนี้ไม่ได้เพิ่ม subsystem ใหม่ แต่ขยาย flow เดิมแบบ additive-only

### Component ที่แก้จริง

- `main.py`
  - เพิ่ม `--caller`
  - instrument `run_headless()` เพื่อ capture outcome ของ action
  - บันทึก telemetry ใน `finally`
- `luma_core/usage_tracker.py`
  - แยก helper `_write_event()`
  - เพิ่ม `record_action_event()` สำหรับ `action_run`
- `luma_core/metrics_summarizer.py`
  - ignore event ที่ไม่ใช่ `llm_call`
- `luma_core/issue_metrics.py`
  - ignore `action_run` ตอนหา earliest usage timestamp
- `tests/test_main_headless_cli.py`
  - เพิ่ม Red tests สำหรับ success/failure logging, caller, และ Zenith-style parsing
- `tests/test_metrics_summarizer.py`
  - เพิ่ม test กัน action event ปน usage summary
- `tests/test_issue_metrics.py`
  - เพิ่ม test กัน action event ปน earliest usage timestamp

## แผนการทำงานที่ใช้จริง

### Step 1: RED

เขียน failing tests ก่อนสำหรับ behavior ต่อไปนี้:

- parse `--caller` ได้
- success path ของ headless action ต้องเขียน `action_run`
- failure path ของ headless action ต้องเขียน `action_run`
- Zenith-style consumer ยัง `json.loads(stdout)` ได้เหมือนเดิม
- usage summary เดิมต้องไม่โดน `action_run` ปน
- issue metrics earliest usage ต้องไม่โดน `action_run` ปน

### Step 2: GREEN

เพิ่ม implementation ขั้นต่ำให้เทสต์ผ่าน:

- เพิ่ม `--caller` ใน parser
- set `usage_tracker` context ก่อนเรียก action
- เพิ่ม `record_action_event()` และเรียกจาก `run_headless()` ใน `finally`
- คง JSON response และ exit code เดิมทุก path

### Step 3: REFACTOR

ปรับโครงสร้างเล็กน้อยเพื่อลด duplication และปิด side effects:

- แยก `_write_event()` ใน `usage_tracker`
- filter event type ใน metrics consumer ที่ควรอ่านเฉพาะ `llm_call`

## สิ่งที่ตั้งใจไม่ทำ

- ไม่สร้าง log file ใหม่
- ไม่เพิ่ม dependency ใหม่
- ไม่เปลี่ยน success/error payload บน `stdout`
- ไม่เปลี่ยน external exit-code contract
- ไม่เพิ่มข้อความ human-readable บน `stdout` ใน headless mode

## Verification Plan

### Automated

- `python3 -m pytest -q tests/test_main_headless_cli.py tests/test_metrics_summarizer.py`
- `python3 -m pytest -q tests/test_usage_tracker.py`
- `python3 -m pytest -q tests/test_main_headless_cli.py tests/test_metrics_summarizer.py tests/test_usage_tracker.py tests/test_issue_metrics.py -k 'headless or usage or earliest or summarize_usage_stats'`

### Manual

- รัน `code_review` แบบ headless success path แล้วตรวจว่า `stdout` ยังเป็น JSON ล้วน
- รัน invalid action หรือ forced failure path แล้วตรวจว่า `stdout` ยังเป็น JSON error
- ตรวจว่า diagnostics อยู่ `stderr`
- ตรวจว่า usage log มี `action_run`
- ตรวจว่า wrapper ที่ parse `stdout` แบบ Zenith ยังทำงานได้
