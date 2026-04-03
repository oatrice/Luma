# Specification: Issue #29 Headless Action-Level Logging

> Status: Implemented
> Owner: Luma CLI
> Created: 2026-04-03
> Last Updated: 2026-04-03

## 1. Context

Luma มี headless CLI contract สำหรับ external caller อยู่แล้ว แต่ก่อนหน้านี้ยังไม่มี action-level execution log สำหรับ `run_headless()`

ผลคือ external automation เช่น Zenith สามารถอ่านผลลัพธ์จาก `stdout` ได้ แต่ trace lifecycle ของ action ได้จำกัดมาก

เป้าหมายของ issue นี้คือเพิ่ม telemetry สำหรับ headless action โดยไม่ทำให้ external contract เดิมแตก

## 2. Functional Requirements

- [x] เมื่อ `run_headless()` ถูกเรียก ต้องมี action-level telemetry event ถูกบันทึก
- [x] telemetry event ต้องมี `mode=headless`
- [x] telemetry event ต้องมี `action`
- [x] telemetry event ต้องมี `project`
- [x] telemetry event ต้องมี `status`
- [x] telemetry event ต้องมี `exit_code`
- [x] telemetry event ต้องมี `duration_ms`
- [x] telemetry event ต้องมี `session_id`
- [x] telemetry event ต้องมี `error` โดย success path ใช้ `null`
- [x] ต้องรองรับ caller identifier แบบ optional ผ่าน `--caller`
- [x] ถ้าไม่ได้ส่ง caller มา ต้องไม่บังคับเติมค่า caller ปลอม
- [x] `stdout` ใน headless `--json` mode ต้องยังเป็น machine-readable JSON only
- [x] ห้ามมี human-readable text เพิ่มลง `stdout`
- [x] `stderr` และ exit-code behavior เดิมต้องคงอยู่
- [x] change ต้องเป็น additive only

## 3. Telemetry Contract

event ใหม่ถูกบันทึกลง `.luma_ai_usage.jsonl` โดยใช้ `event: "action_run"`

### Required Fields

| Field | Type | Notes |
|------|------|-------|
| `ts` | string | ISO timestamp |
| `event` | string | ต้องเป็น `"action_run"` |
| `mode` | string | `"headless"` |
| `action` | string or null | action ที่ร้องขอ |
| `project` | string or null | requested project identifier |
| `status` | string | `"success"` หรือ `"error"` |
| `exit_code` | integer | final process exit code |
| `duration_ms` | integer | execution duration |
| `session_id` | string | reuse จาก process session ของ usage tracker |
| `luma_version` | string | version ของ Luma |
| `error` | string or null | error summary |

### Optional Fields

| Field | Type | Notes |
|------|------|-------|
| `caller` | string | มีเฉพาะเมื่อส่ง `--caller` |
| `project_name` | string | injected จาก usage tracker context เมื่อมี |
| `project_path` | string | injected จาก usage tracker context เมื่อมี |
| `project_repo` | string | injected จาก usage tracker context เมื่อมี |
| `phase` | string | injected จาก state เมื่อมี |
| `issue_numbers` | array | injected จาก state เมื่อมี |

## 4. CLI Contract

### Supported Caller Identifier

```bash
python3 main.py --auto --action code_review --json --project 1 --caller zenith-wrapper
```

`--caller` เป็น optional flag และไม่เปลี่ยน stdout payload

### Success JSON Payload

```json
{
  "status": "success",
  "action": "code_review",
  "project": "1",
  "result": {
    "summary": "review complete"
  }
}
```

### Error JSON Payload

```json
{
  "status": "error",
  "action": "code_review",
  "project": "1",
  "error": "review execution failed"
}
```

## 5. Specification by Example

### Scenario A: Successful headless code review

**Given** valid project `1` และ action `code_review`
  
**When** รัน:

```bash
python3 main.py --auto --action code_review --json --project 1 --caller zenith-wrapper
```

**Then**

- process exit code เป็น `0`
- `stdout` เป็น JSON success payload
- `stderr` อาจมี diagnostics จาก action ได้
- usage log มี `action_run` event ที่มี:
  - `mode: "headless"`
  - `action: "code_review"`
  - `project: "1"`
  - `status: "success"`
  - `exit_code: 0`
  - `caller: "zenith-wrapper"`

### Scenario B: Invalid action

**When** รัน:

```bash
python3 main.py --auto --action invalid_action --json --project 1
```

**Then**

- process exit code เป็น `1`
- `stdout` เป็น JSON error payload
- usage log มี `action_run` event ที่มี:
  - `action: "invalid_action"`
  - `status: "error"`
  - `exit_code: 1`
  - `error` อธิบายว่า action ไม่พบ

### Scenario C: Runtime failure inside headless action

**When** action โยน exception ระหว่าง execution

**Then**

- process exit code เป็น `2`
- `stdout` เป็น JSON error payload
- telemetry event มี `status: "error"` และ `error` summary
- ข้อความ debug/runtime ของ action ยังไป `stderr`

### Scenario D: Zenith-style consumer parsing

**When** wrapper ใช้ `subprocess.run(..., capture_output=True)` แล้วทำ `json.loads(result.stdout)`

**Then**

- parse ได้สำเร็จเหมือนเดิม
- action-level logging ไม่ทำให้มีข้อความอื่นปนใน `stdout`

## 6. Compatibility Notes

- งานนี้ไม่เปลี่ยน schema ของ success/error payload บน `stdout`
- งานนี้ไม่เปลี่ยน exit code semantics ของ headless flow
- งานนี้ไม่เปลี่ยน `stderr` routing ของ diagnostics
- งานนี้ไม่สร้าง breaking change ให้ Zenith consumer contract
- งานนี้เพิ่ม event ใหม่ใน usage log แบบ additive-only

## 7. Downstream Safety

เพราะมี event ใหม่ชื่อ `action_run` ถูกเพิ่มลง usage log เดิม จึงต้องมี guard เพิ่มใน consumer ที่คาดหวัง `llm_call`

consumer ที่ถูกอัปเดต:

- `luma_core.metrics_summarizer.summarize_usage_stats()`
- `luma_core.issue_metrics.get_earliest_usage_timestamp()`

เป้าหมายคือให้ metric และ heuristic เดิมยังตีความ usage log ได้เหมือนก่อนหน้า issue นี้
