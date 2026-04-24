# Analysis: Historical Packet for Luma #40 / #42 / #41

> อัปเดตล่าสุด: 2026-04-24
> สถานะเอกสาร: Current-state refresh
> ขอบเขตอ้างอิง: `oatrice/Luma#40`, `#42`, `#41`, และ follow-up `#84`

## 1. Executive Summary

เอกสารชุดนี้เดิมถูกสร้างขึ้นเพื่อวางแผนงานเป็นแพ็กเดียวสำหรับ:

- `#40` Headless Select Issue / branch bootstrap
- `#42` First-class Issue Creation
- `#41` Headless Guided Workflow

แต่สถานะปัจจุบันของ codebase เปลี่ยนไปแล้ว:

- `#40` ถูกปิดและมี implementation จริงใน codebase
- implementation ของ `#40` ไปถึงระดับ “ใช้งาน core behavior ได้” แต่ยังไม่ parity กับ acceptance ปัจจุบันทุกข้อ
- `#42` และ `#41` ยังเป็นงานคนละแกน และไม่ใช่ blocker หลักของ one-click chain รอบนี้
- blocker หลักตอนนี้คือ `#84` ซึ่งต้องทำ stable headless project selection ให้ใช้ได้กับ external caller และลดการพึ่ง numeric `--project`

ดังนั้นเอกสารชุดนี้ไม่ควรถูกใช้เป็น roadmap สำหรับแพ็ก `#40/#42/#41` แบบเดิมอีกต่อไป แต่ควรถูกใช้เป็น historical packet ที่อธิบาย:

1. อะไรใน `#40` ถูก implement ไปแล้ว
2. อะไรยังขาด
3. อะไรควรย้ายไป follow-up หรือเชื่อมกับ `#84`

## 2. Current Status Snapshot

### 2.1 Issue State

| Issue | สถานะบน GitHub | ความหมายเชิงปฏิบัติ |
|---|---|---|
| `#40` | Closed | มี implementation จริงอยู่ใน codebase แล้ว |
| `#42` | Open/Deferred context | ไม่ใช่ dependency ตรงของ selector correctness |
| `#41` | Open/Deferred context | ใหญ่เกิน scope ของ downstream routing fix รอบนี้ |
| `#84` | Open | เป็นงานหลักถัดไปสำหรับ stable selector contract |

### 2.2 Code Reality for `#40`

หลักฐานจาก codebase ปัจจุบัน:

- [main.py](/Users/oatrice/Software-projects/Luma/main.py:47) รองรับ headless action `bootstrap`
- [main.py](/Users/oatrice/Software-projects/Luma/main.py:448) route action `bootstrap` ไปยัง `actions.bootstrap_issue(...)`
- [issue_actions.py](/Users/oatrice/Software-projects/Luma/luma_core/actions/issue_actions.py:358) มี `bootstrap_issue(...)`
- [utils.py](/Users/oatrice/Software-projects/Luma/luma_core/actions/utils.py:453) มี `_start_issues_headless(...)` ที่:
  - transition state ไป `coding`
  - set `active_issues`
  - set `active_branch`
  - create/switch git branch
- [tests/test_headless_bootstrap.py](/Users/oatrice/Software-projects/Luma/tests/test_headless_bootstrap.py:23) มี test ยืนยัน happy path ขั้นพื้นฐาน

สรุป: `#40` “มีจริง” และ “ไม่ได้เป็นเพียงเอกสาร”

## 3. Acceptance Audit for `#40`

| Acceptance | Verdict | Notes |
|---|---|---|
| มี headless action สำหรับ issue selection / branch bootstrap | PASS | ใช้ action name `bootstrap` ไม่ใช่ `select_issue` |
| reuse branch suggestion / creation logic แบบ interactive | PASS | ใช้ branch generation และ git checkout path เดียวกัน |
| update state ให้สอดคล้อง (`active_issues`, `active_branch`, phase) | PASS | transition ไป `coding` จริง |
| preserve headless JSON stdout contract | PASS WITH NOTE | JSON ยังออกได้ แต่ payload content ยังบาง |
| return machine-readable payload ที่บอกรายละเอียด selected issues / branch / resulting state | PARTIAL / FAIL | ตอนนี้ผลลัพธ์หลักยัง bool-centric มากกว่า structured payload |
| reuse same selection constraints as interactive Kanban flow | NOT PROVEN / LIKELY FAIL | headless path ดูเหมือน match by issue number โดยตรง มากกว่าจะใช้ `_get_selectable_cards(...)` แบบ interactive |
| ไม่ regress interactive Menu 2 | PASS | interactive flow ยังอยู่ครบ |

## 4. Why `#84` Is Now the Primary Scope

ปัญหาปัจจุบันของ cross-repo automation ไม่ได้อยู่ที่ “Luma มี headless bootstrap หรือยัง” แต่เป็น:

- external caller ยังต้องพึ่ง numeric `--project`
- numeric mapping นี้ drift ได้ระหว่าง environment
- ใน live verification มีเคสที่ intent ต้องการ `Zenith` แต่ downstream กลับ resolve ไป `JarWise`

ดังนั้น priority จริงคือ:

1. ทำ stable selector contract (`repo`, `path`, `slug`, หรือ equivalent durable identity)
2. ให้ machine-readable response echo target ที่ resolve จริง
3. ทำให้ action เดิมอย่าง `bootstrap` ใช้ resolver เดียวกัน

## 5. Recommendation

### 5.1 สำหรับเอกสารชุดนี้

- ให้ถือว่าเป็น historical packet ที่ “ต้องอัปเดตให้ตรง code reality”
- หยุดมอง `#40/#42/#41` เป็นแพ็ก implement รอบเดียว
- แยกชัดว่า:
  - `#40` = implemented substantially, but not perfectly aligned
  - `#42/#41` = deferred / separate track
  - `#84` = current priority

### 5.2 สำหรับงานถัดไป

- ทำ `#84` เป็น primary scope
- ระหว่างทำ `#84` ให้ audit compatibility กับ `bootstrap` implementation จาก `#40`
- อย่า reopen `#40` ทันทีเพียงเพราะ acceptance บางข้อยังไม่ครบ
- ถ้าหลังทำ `#84` แล้วยังมี gap ที่เฉพาะกับ `bootstrap` เช่น:
  - response shape ยังไม่ rich พอ
  - selection constraints ยังไม่ parity
  - contract naming ยังชวนสับสน
  ค่อยเปิด follow-up issue ใหม่ที่แคบและอธิบาย gap นั้นโดยตรง

## 6. Related

- [Luma #40](https://github.com/oatrice/Luma/issues/40)
- [Luma #84](https://github.com/oatrice/Luma/issues/84)
- [Zenith #36](https://github.com/oatrice/Zenith/issues/36)
- [main.py](/Users/oatrice/Software-projects/Luma/main.py:47)
- [issue_actions.py](/Users/oatrice/Software-projects/Luma/luma_core/actions/issue_actions.py:358)
- [utils.py](/Users/oatrice/Software-projects/Luma/luma_core/actions/utils.py:453)
