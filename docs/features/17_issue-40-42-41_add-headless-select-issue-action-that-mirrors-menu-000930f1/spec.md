# Specification: Headless CLI Expansion & First-Class Issue Management

> **Status**: Draft
> **Owner**: Expert Product Manager & Systems Analyst
> **Dates**: Created: 2026-04-06 | Last Updated: 2026-04-06

## 1. Context & Goal
ปัจจุบัน Luma มีความสามารถในการทำงานแบบ Interactive ผ่าน Menu ต่างๆ ได้อย่างครบถ้วน แต่ในส่วนของ **Headless CLI Contract** (สำหรับการเรียกใช้งานจากภายนอกหรือ Automation) ยังรองรับเพียงแค่ `code_review` เท่านั้น ทำให้ไม่สามารถเริ่ม Workflow ใหม่ (Bootstrap), สร้าง Issue หรือรัน Workflow แบบเต็มรูปแบบ (Auto Full Workflow) ผ่านเครื่องมือภายนอกได้

### Problem
1. **Issue #40**: การเลือก Issue และการสร้าง Branch (Menu 2) ผูกติดกับ Interactive UI เท่านั้น ทำให้ Automation ไม่สามารถตั้งค่าสถานะ (State) เริ่มต้นที่ถูกต้องได้
2. **Issue #42**: การสร้าง GitHub Issue ถูกซ่อนอยู่ในเมนู Update Roadmap ทำให้ค้นหาได้ยากและไม่สามารถสั่งงานแยกต่างหากผ่าน CLI ได้
3. **Issue #41**: Workflow แบบอัตโนมัติ (Auto Full Workflow - Menu A) ซึ่งเป็นจุดแข็งของ Luma ไม่สามารถสั่งการผ่าน Headless mode ได้ ทำให้การขยายผลไปใช้กับ CI/CD หรือ Agent ภายนอกทำได้ยาก

### Goal
ขยายความสามารถของ Headless CLI ให้ครอบคลุมการทำงานหลักของ Luma ทั้งหมด ตั้งแต่การเลือก Issue (Bootstrap), การสร้าง Issue ใหม่แบบ First-class และการรัน Full Workflow แบบเก็บสถานะ (Resumable) โดยยังคงรักษามาตรฐาน JSON stdout contract ไว้

---

## 2. User Journey & Requirements

### User Story
As a **Developer/Automation Tool**, I want to **trigger Luma actions via machine-readable commands**, so that **I can integrate Luma's powerful workflow into my external scripts and CI pipelines without manual intervention**.

### Functional Requirements
- [ ] **Headless Issue Selection (#40)**: เพิ่ม Action สำหรับเลือก Issue จาก Kanban และทำการ Bootstrap branch โดยอัตโนมัติ พร้อมคืนค่า JSON state
- [ ] **First-Class Issue Creation (#42)**: เพิ่มเมนูสำหรับสร้าง Issue โดยตรง (ทั้ง Interactive และ Headless) และต้องรองรับ Template ที่มีส่วน `## Related`
- [ ] **Headless Guided Workflow (#41)**: รองรับการรัน `Auto Full Workflow` ผ่าน Headless mode โดยมีการเก็บ Checkpoint เพื่อให้สามารถ Resume งานต่อได้หากเกิดการหยุดชะงัก
- [ ] **JSON Contract Consistency**: ผลลัพธ์ของ Headless actions ทั้งหมดต้องเป็น JSON ผ่าน STDOUT เท่านั้น (ห้ามมี Log อื่นปน)
- [ ] **Interactive Parity**: ฟีเจอร์ใหม่ในส่วน Interactive ต้องไม่ทำให้ Workflow เดิมถดถอย (No regressions)

### Non-Functional Requirements
- **Reliability**: การเปลี่ยนสถานะ (State transitions) ใน Headless mode ต้องแม่นยำและบันทึกลง `.luma_state.json` เสมอ
- **Observability**: Headless output ต้องระบุชัดเจนว่าขณะนี้อยู่ใน Phase ใดของ Workflow

---

## 3. Specification by Example (SBE)

### Scenario: Headless Issue Selection & Bootstrap (#40)
**Given** มี Issue #123 ในสถานะ 'Ready' บน GitHub Kanban
**When** เรียกใช้คำสั่ง headless ด้วย action `select_issue` และระบุหมายเลข issue
**Then** Luma ต้องสร้าง branch ตาม naming convention, อัปเดต state เป็น `coding` และคืนค่า JSON รายละเอียดของ issue และ branch

#### Examples
| Input (Action + Issue) | System State (Before) | Output (JSON) | Resulting Branch |
|-------------------------|-----------------------|---------------|------------------|
| `select_issue --id 123` | `idle`                | `{"issue": 123, "branch": "feat/123-login", "status": "success"}` | `feat/123-login` |
| `select_issue --id 999` | `idle` (Issue not found)| `{"error": "Issue not found", "status": "failure"}` | (No change) |

### Scenario: First-Class Issue Creation (#42)
**Given** ผู้ใช้ต้องการสร้าง Issue ใหม่สำหรับบั๊กที่พบ
**When** เรียกใช้เมนู `Create Issue` (Interactive) หรือ headless action `create_issue`
**Then** ระบบต้องสร้าง Issue บน GitHub โดยมีส่วนประกอบ `## Related` ใน Body และคืนค่า URL/Number กลับมา

#### Examples
| Input (Title) | Body Contains | Result |
|---------------|---------------|--------|
| "Fix UI bug"  | `## Related: #10` | Created Issue #124 |
| "New Feature" | (Empty Related) | Created Issue #125 with placeholder `## Related` |

### Scenario: Resuming Headless Guided Workflow (#41)
**Given** Workflow เคยรันค้างไว้ที่ Phase `planning`
**When** เรียกใช้ headless `auto_workflow` พร้อมส่ง Flag หรือ State เดิมกลับไป
**Then** ระบบต้องอ่าน Checkpoint และเริ่มทำงานต่อจากจุดเดิมโดยไม่เริ่มใหม่ตั้งแต่ต้น

#### Examples
| Current State (in json) | Command | Expected Output Phase |
|-------------------------|---------|-----------------------|
| `{"phase": "coding"}`   | `auto_workflow --resume` | `{"phase": "reviewing", ...}` |
| `{"phase": "idle"}`     | `auto_workflow` | `{"phase": "selecting", ...}` |

---

## 4. Constraints & Risks
- **JSON STDOUT Conflict**: ต้องระวังไม่ให้ Python print ค่าอื่นๆ ออกมานอกจาก JSON เมื่ออยู่ในโหมด Headless (ต้องใช้ `RedirectStdout` หรือการจัดการ Logger ที่เข้มงวด)
- **State Lock**: การรัน Headless workflow หลายตัวพร้อมกันอาจทำให้ `.luma_state.json` เกิดการเขียนทับกันได้ (Race condition)
- **Interactive Prompts**: ในโหมด Headless หากโค้ดเดิมมีการเรียก `input()` จะทำให้โปรแกรมค้าง (Hanging) ต้องแน่ใจว่าได้จำลอง Input (Mock) หรือ Bypass ส่วนที่ต้องการ Interactive ทั้งหมดเมื่อรันแบบ Machine-readable

---
**Next Step**: เมื่อ Spec นี้ได้รับการอนุมัติ จะดำเนินการสร้าง `plan.md` เพื่อลงรายละเอียดการแก้ไขใน `main.py` และ `luma_core/actions/` ต่อไป