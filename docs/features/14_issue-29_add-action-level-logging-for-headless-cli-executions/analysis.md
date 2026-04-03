# Analysis: Issue #29 Headless Action-Level Logging

## ข้อมูลฟีเจอร์

| รายการ | รายละเอียด |
|--------|-----------|
| Feature | Add action-level logging for headless CLI executions |
| Issue | `#29` |
| Issue URL | `https://github.com/oatrice/Luma/issues/29` |
| Date | 2026-04-03 |
| Status | Implemented |
| Priority | High |

## ปัญหาที่ต้องแก้

ก่อนแก้ไข `run_headless()` ของ Luma มี contract สำหรับ external consumer อยู่แล้ว:

- `stdout` ใน headless `--json` mode เป็น machine-readable JSON
- diagnostics และ runtime noise ถูกส่งไป `stderr`
- exit code ใช้แยก success และ error ได้

แต่ยังไม่มี action-level telemetry สำหรับ headless execution ทำให้:

- trace การรันจาก external wrapper เช่น Zenith ได้ยาก
- แยก success/failure ของ action ระดับ process ได้ไม่ชัด
- ไม่มีจุดบันทึก `duration_ms`, `session_id`, และ `error` สำหรับ headless action โดยตรง

## Constraints ที่ต้องรักษา

- ห้ามทำ breaking change กับ headless JSON stdout contract
- ห้ามพิมพ์ข้อความ human-readable เพิ่มลง `stdout` ใน headless mode
- change ต้องเป็น additive only
- ต้องรักษา `stdout`, `stderr`, และ exit-code behavior เดิมสำหรับ external consumer

## การตัดสินใจเชิงออกแบบ

### 1. Reuse usage log เดิม

แทนที่จะสร้าง log file ใหม่ งานนี้เลือก reuse `.luma_ai_usage.jsonl` ผ่าน `luma_core.usage_tracker`

เหตุผล:

- ลดการแตก branch ของ observability data
- reuse `session_id` เดิมของ process ได้ทันที
- ลด dependency และหลีกเลี่ยง schema ใหม่ที่ external tooling ต้องเรียนรู้

### 2. เพิ่ม event type ใหม่แบบ additive

เพิ่ม event ใหม่ชื่อ `action_run` โดยอย่างน้อยมี field ต่อไปนี้:

- `mode`
- `action`
- `project`
- `status`
- `exit_code`
- `duration_ms`
- `session_id`
- `error`
- `caller` เมื่อ caller ถูกส่งเข้ามา

พร้อมทั้งอนุญาตให้มี context เสริมจาก `usage_tracker` เช่น `project_name`, `project_path`, `project_repo`, `phase`, `issue_numbers`

### 3. เก็บ telemetry ใน `finally`

การบันทึก action-level event ถูกวางใน `finally` ของ `run_headless()` เพื่อให้ครอบคลุมทั้ง:

- success path
- `CLIError`
- exception ทั่วไป

แนวทางนี้ทำให้ log ถูกเขียนแม้ action จะล้ม และไม่ต้อง duplicate logic หลาย branch

### 4. รองรับ caller identifier แบบ explicit

เลือกเพิ่ม CLI flag `--caller` แบบ optional แทนการเดาจาก environment หรือ OS user

เหตุผล:

- explicit ชัดเจนสำหรับ external wrapper
- ควบคุม contract ได้ง่าย
- ลด ambiguity และลด risk เรื่อง attribution ผิด

### 5. กัน downstream consumer เดิมไม่ให้เพี้ยน

เมื่อเพิ่ม `action_run` ลง usage log เดิม ต้องกัน logic ที่คาดว่าอ่านเฉพาะ `llm_call`

จึงเพิ่ม filter ให้:

- `luma_core.metrics_summarizer.summarize_usage_stats()` นับเฉพาะ `llm_call`
- `luma_core.issue_metrics.get_earliest_usage_timestamp()` มองเฉพาะ `llm_call`

สิ่งนี้ช่วยให้ dashboard และ metric heuristics เดิมไม่โดน action event ใหม่ปน

## ความเสี่ยงและวิธีลดความเสี่ยง

| ความเสี่ยง | ผลกระทบ | วิธีลดความเสี่ยง |
|-----------|---------|------------------|
| stdout contract แตกเพราะมี log ปน | Zenith parse ไม่ได้ | ไม่พิมพ์อะไรเพิ่มลง stdout และทดสอบ subprocess parseability |
| success/failure path บันทึกไม่ครบ | trace ไม่สมบูรณ์ | บันทึก telemetry ใน `finally` |
| usage summary เพี้ยนจาก event ใหม่ | metrics dashboard ให้ค่าผิด | filter `event != "llm_call"` ใน summarizer |
| issue metrics ใช้ timestamp ผิด | start datetime ถูก backfill ผิด | filter `action_run` ออกจาก earliest-usage logic |

## ผลลัพธ์ที่ได้จริง

- `run_headless()` มี action-level telemetry แล้ว
- external consumer ยัง parse `stdout` JSON ได้เหมือนเดิม
- diagnostics ยังไป `stderr`
- exit code ไม่เปลี่ยน semantics
- มี optional `--caller` สำหรับ caller attribution
- downstream metrics เดิมยังอ่าน usage log ได้ตาม semantics เดิม
