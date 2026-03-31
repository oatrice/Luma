ฉันได้จัดทำรายละเอียดคุณลักษณะ (Specification) สำหรับการเพิ่มฟิลด์ `post_story_point` เพื่อใช้ในการวัดความแม่นยำของการประเมินงาน (Estimation Accuracy) โดยมีรายละเอียดดังนี้ครับ

# Specification: Add post_story_point field to .luma_metrics.json and IssueMetricsRecord

> **Status**: Draft
> **Owner**: Gemini CLI
> **Dates**: Created: 2026-03-31 | Last Updated: 2026-03-31

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
ในปัจจุบัน Luma รองรับการเก็บ `estimate_points` (Story Points ที่ประเมินไว้ก่อนเริ่มงาน) แต่ยังไม่มีฟิลด์สำหรับบันทึกความซับซ้อนที่เกิดขึ้นจริง (Actual Complexity) หลังจากงานเสร็จสิ้น ทำให้ไม่สามารถเปรียบเทียบความแตกต่างระหว่างการประเมินและความเป็นจริงได้ ซึ่งเป็นข้อมูลสำคัญในการปรับปรุงทีมให้ประเมินงานได้แม่นยำขึ้นในอนาคต

### Goal
เพิ่มฟิลด์ `post_story_point` ในระบบบันทึก Metrics ของ Luma เพื่อเก็บค่า Story Points หลังจบงาน และปรับปรุง CLI ให้รองรับการรับค่านี้เมื่อมีการปิดงานหรืออัปเดตสถานะงานที่เสร็จสมบูรณ์

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
As a **Developer or Product Manager**, I want to **record the actual story points after finishing a task**, so that **I can analyze estimation accuracy and improve future project planning**.

### Functional Requirements
- [ ] เพิ่มฟิลด์ `post_story_point` (Optional Integer) ใน `IssueMetricsRecord` dataclass
- [ ] ปรับปรุงระบบ Serialization (JSON) ให้รองรับการอ่าน/เขียนฟิลด์ `post_story_point` ในไฟล์ `.luma_metrics.json`
- [ ] เพิ่ม prompt ใน CLI เมื่อผู้ใช้งานทำการปิด Issue หรือเปลี่ยนสถานะเป็น "Done" เพื่อให้ระบุค่า `post_story_point`
- [ ] รองรับการเว้นว่าง (Null) หากผู้ใช้ไม่ต้องการระบุในทันที

### Non-Functional Requirements
- [ ] **Data Integrity**: ต้องไม่ทำให้ข้อมูล Metrics เดิมในไฟล์ `.luma_metrics.json` สูญหาย หรือทำให้โครงสร้างไฟล์พัง
- [ ] **Backward Compatibility**: ไฟล์ `.luma_metrics.json` เดิมที่ไม่มีฟิลด์นี้ต้องสามารถใช้งานร่วมกับระบบใหม่ได้ (Default เป็น `None` หรือ `null`)

---

## 3. Specification by Example (SBE)
*Concrete examples of behavior.*

### Scenario: Recording post_story_point during issue closure
**Given** an issue with `estimate_points: 5` is currently in progress.
**When** the user closes the issue via Luma CLI.
**Then** the CLI should ask for "Actual Story Points (Post-completion)", and the value should be saved to `.luma_metrics.json`.

#### Examples
| initial_estimate | user_input (post) | saved_in_json | result_analysis (internal) |
|------------------|-------------------|---------------|----------------------------|
| 5                | 8                 | 8             | Underestimated             |
| 3                | 3                 | 3             | Accurate                   |
| 13               | 5                 | 5             | Overestimated              |
| 2                | (empty)           | null          | No data                    |

### Scenario: Preserving field during data synchronization
**Given** a metrics record already has `post_story_point` set.
**When** the metrics are synchronized or updated from GitHub activity.
**Then** the existing `post_story_point` value must not be overwritten unless explicitly changed by the user.

#### Examples
| existing_post_point | action                | final_post_point | notes                     |
|---------------------|-----------------------|------------------|---------------------------|
| 5                   | Sync with GitHub      | 5                | Value preserved           |
| null                | Manual update to 3    | 3                | Value updated             |
| 8                   | Issue reopened        | 8                | Value stays until re-closed|

---

## 4. Constraints & Risks
*What should we watch out for?*
- **Constraint**: ฟิลด์นี้ควรเป็น Optional เนื่องจากบางงานอาจจะเล็กเกินไปจนไม่ต้องประเมินหลังจบงาน
- **Risk**: หากผู้ใช้ปิดงานผ่านหน้าเว็บ GitHub โดยตรง (ไม่ใช่ผ่าน Luma CLI) ระบบอาจจะไม่มีโอกาสถามค่า `post_story_point` ซึ่งอาจต้องหาวิธีรองรับการกรอกย้อนหลังผ่านเมนู Metrics