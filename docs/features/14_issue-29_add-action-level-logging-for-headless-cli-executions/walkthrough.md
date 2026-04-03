# Walkthrough: Headless Action-Level Logging for `run_headless()`

## สรุป

Issue #29 เพิ่ม action-level logging ให้ headless CLI ของ Luma โดยไม่แตะ external JSON contract ที่ Zenith ใช้อยู่

สิ่งที่ได้จากรอบนี้:

- `run_headless()` บันทึก `action_run` telemetry ทุกครั้ง
- telemetry มีอย่างน้อย `mode`, `action`, `project`, `status`, `exit_code`, `duration_ms`, `session_id`, `error`
- รองรับ optional caller identifier ผ่าน `--caller`
- `stdout` ใน headless `--json` mode ยังเป็น JSON only
- diagnostics ยังอยู่ `stderr`
- exit-code behavior เดิมยังคงเดิม
- usage summary และ issue metrics เดิมไม่โดน event ใหม่ทำให้เพี้ยน

## ไฟล์ที่เกี่ยวข้อง

| ไฟล์ | การเปลี่ยนแปลง |
|------|---------------|
| `main.py` | เพิ่ม `--caller` และ instrument `run_headless()` ให้บันทึก telemetry ใน `finally` |
| `luma_core/usage_tracker.py` | เพิ่ม `_write_event()` และ `record_action_event()` |
| `luma_core/metrics_summarizer.py` | กรอง `action_run` ออกจาก summary ที่ควรนับเฉพาะ `llm_call` |
| `luma_core/issue_metrics.py` | กรอง `action_run` ออกจาก earliest usage timestamp |
| `tests/test_main_headless_cli.py` | เพิ่ม tests สำหรับ caller, success/failure telemetry และ Zenith-style parsing |
| `tests/test_metrics_summarizer.py` | เพิ่ม test กัน `action_run` ปน usage summary |
| `tests/test_issue_metrics.py` | เพิ่ม test กัน `action_run` ปน earliest usage timestamp |

## พฤติกรรมที่ verify ได้แล้ว

### 1. Success path ของ headless action

คำสั่งเชิงแนวคิด:

```bash
python3 main.py --auto --action code_review --json --project 1 --caller zenith-wrapper
```

ผลที่ยืนยันได้:

- action รันโดยไม่เข้า interactive mode
- `stdout` ยังเป็น JSON success
- `stderr` ยังรับ diagnostics ของ action
- usage log มี `action_run` event พร้อม `caller`

### 2. Failure path ของ headless action

เมื่อ action โยน exception:

- process จบด้วย exit code `2`
- `stdout` ยังเป็น JSON error
- usage log มี `action_run` event พร้อม `status: "error"`
- `error` field ถูกบันทึก

### 3. Invalid action path

```bash
python3 main.py --auto --action invalid_action --json --project 1
```

ผลที่ยืนยันได้:

- process จบด้วย exit code `1`
- `stdout` parse เป็น JSON ได้
- telemetry event ถูกบันทึกแม้ action หาไม่เจอ

### 4. Zenith-style consumer ยัง parse ได้เหมือนเดิม

ทดสอบผ่าน subprocess wrapper ที่ทำ `json.loads(result.stdout)` แล้วผ่านตามเดิม

สิ่งที่ยืนยันได้:

- action-level logging ไม่ทำให้มีข้อความปน `stdout`
- external consumer ยังใช้ contract เดิมได้โดยไม่ต้องแก้ parser

### 5. Downstream metrics ยังไม่เพี้ยน

หลังเพิ่ม event `action_run` ลง `.luma_ai_usage.jsonl`

สิ่งที่ยืนยันได้:

- `summarize_usage_stats()` ยังนับเฉพาะ `llm_call`
- `get_earliest_usage_timestamp()` ยังหา timestamp จาก `llm_call` เท่านั้น

## Automated Verification ที่รันแล้ว

### Targeted headless + summarizer tests

```bash
python3 -m pytest -q tests/test_main_headless_cli.py tests/test_metrics_summarizer.py
```

ผลลัพธ์:

```text
25 passed, 2 warnings in 3.39s
```

### Usage tracker regression

```bash
python3 -m pytest -q tests/test_usage_tracker.py
```

ผลลัพธ์:

```text
4 passed in 0.02s
```

### Cross-check รวม headless / usage / earliest timestamp

```bash
python3 -m pytest -q tests/test_main_headless_cli.py tests/test_metrics_summarizer.py tests/test_usage_tracker.py tests/test_issue_metrics.py -k 'headless or usage or earliest or summarize_usage_stats'
```

ผลลัพธ์:

```text
27 passed, 32 deselected, 2 warnings in 3.44s
```

## Manual Verification Scenarios

### Scenario A: Success path พร้อม caller
1. รัน `python3 main.py --auto --action code_review --json --project 1 --caller zenith-wrapper`
2. ตรวจว่า `stdout` เป็น JSON success
3. ตรวจว่า diagnostics อยู่ `stderr`
4. ตรวจว่า `.luma_ai_usage.jsonl` มี `event: "action_run"` และ `caller: "zenith-wrapper"`

### Scenario B: Invalid action
1. รัน `python3 main.py --auto --action invalid_action --json --project 1`
2. ตรวจว่า `stdout` เป็น JSON error
3. ตรวจว่า exit code เป็น `1`
4. ตรวจว่า usage log มี `action_run` event พร้อม error summary

### Scenario C: Runtime failure ของ action
1. บังคับให้ action โยน exception
2. ตรวจว่า `stdout` ยังเป็น JSON error
3. ตรวจว่า exit code เป็น `2`
4. ตรวจว่า usage log มี `status: "error"` และ `error`

### Scenario D: Wrapper parse stdout
1. ใช้ subprocess wrapper จับ `stdout`
2. ทำ `json.loads(result.stdout)`
3. ตรวจว่า parse ผ่านโดยไม่ต้อง trim ข้อความอื่น

## หมายเหตุ

- งานนี้ใช้ usage log เดิม `.luma_ai_usage.jsonl` ไม่ได้สร้างไฟล์ log ใหม่
- caller identifier ใช้ CLI flag `--caller` ไม่ได้ใช้ environment variable
- event ใหม่เป็น additive-only และออกแบบให้ downstream consumer เดิมกรองทิ้งได้เมื่อไม่ต้องการ
