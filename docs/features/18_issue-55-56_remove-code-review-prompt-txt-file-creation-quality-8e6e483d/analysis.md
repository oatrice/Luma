ฉันจะดำเนินการวิเคราะห์ทางเทคนิคสำหรับ Issue #55 และ #56 โดยตรวจสอบรหัสต้นฉบับในไฟล์ที่เกี่ยวข้องเพื่อให้ได้ข้อมูลที่แม่นยำที่สุดก่อนจัดทำเอกสารครับ

เริ่มจากการตรวจสอบ `luma_core/actions/quality_actions.py` และ `luma_core/tools.py` เพื่อดูจุดที่มีการสร้างไฟล์และวิธีการจัดการ Path ในปัจจุบัน

ผมได้รวบรวมข้อมูลเบื้องต้นเกี่ยวกับจุดที่ต้องแก้ไขแล้วครับ ต่อไปนี้เป็นเอกสารวิเคราะห์ทางเทคนิค (Technical Analysis) สำหรับ Feature นี้ครับ

**หมายเหตุ**: ฟังก์ชัน `resolve_project_target_dir()` และ `get_git_worktree_path()` อยู่ใน `luma_core/tools.py` ไม่ใช่ `luma_core/project_context.py`

# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Remove code_review_prompt.txt & Fix Worktree Path Resolution |
| **Date** | 2026-04-09 |
| **Analyst** | Gemini CLI |
| **Priority** | 🔴 High |
| **Status** | ✅ Completed |
| **Issue URL** | [#55-56](https://github.com/users/oatrice/projects/1/views/1?pane=issue&itemId=55) |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

1. **Issue #55**: ระบบมีการสร้างไฟล์ชั่วคราว `code_review_prompt.txt` ในโฟลเดอร์โครงการทุกครั้งที่มีการรัน Code Review ซึ่งทำให้เกิดไฟล์ขยะ (clutter) ใน Workspace โดยไม่จำเป็น
2. **Issue #56**: เมื่อรัน Luma จาก Git Worktree โดยใช้ Path สัมพัทธ์ (เช่น `python3 ../../Luma/main.py`) ระบบจะใช้ Path ของโครงการจากไฟล์ Config ซึ่งชี้ไปยัง Repository หลัก แทนที่จะเป็น Path ของ Worktree ปัจจุบัน ทำให้ไฟล์ Output (เช่น `code_review.md`) ถูกเขียนผิดที่

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | Developer | ไม่เห็นไฟล์ `code_review_prompt.txt` ถูกสร้างขึ้นโดยอัตโนมัติ | Workspace สะอาดและไม่มีไฟล์ขยะ |
| 2 | Developer | ให้ Luma เขียนไฟล์ Output ลงใน Git Worktree ที่กำลังทำงานอยู่ | สามารถตรวจสอบผลลัพธ์ในบริบทของ Worktree นั้นๆ ได้ถูกต้อง |

### 1.3 Acceptance Criteria

- [ ] **AC1:** ลบโค้ดส่วนที่สร้างไฟล์ `code_review_prompt.txt` ใน `quality_actions.py` ออก
- [ ] **AC2:** เมื่อรัน Luma ใน Git Worktree ไฟล์ Output ทั้งหมด (Code Review, PR Preview, ฯลฯ) ต้องถูกบันทึกลงใน Root ของ Worktree นั้นๆ
- [ ] **AC3:** การรัน Luma ใน Repository ปกติ (Non-worktree) ยังต้องทำงานได้ถูกต้องเหมือนเดิม
- [ ] **AC4:** มีการเพิ่ม Unit Test เพื่อยืนยันการ Resolve Path ในกรณีที่เป็น Worktree

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    A[เริ่มรัน Code Review] --> B[Resolve Target Directory]
    B --> C{อยู่ใน Git Worktree?}
    C -->|ใช่| D[ใช้ Path ของ Worktree ปัจจุบัน]
    C -->|ไม่ใช่| E[ใช้ Path จาก Config/Default]
    D --> F[รัน AI Analysis]
    E --> F
    F --> G[แสดง Prompt บน Terminal]
    G --> H[บันทึก code_review.md ลงใน Target Dir]
    H --> I[สิ้นสุด (ไม่สร้าง code_review_prompt.txt)]
```

### 2.2 Input/Output Specification

#### Inputs
- **Current Working Directory**: ระบบต้องตรวจสอบว่า CWD อยู่ภายใต้ Git Worktree หรือไม่
- **Project Path**: Path ที่ระบุใน Configuration ของ Luma

#### Outputs
- **code_review.md**: ไฟล์รายงานผลการรีวิว (บันทึกใน Path ที่ถูกต้อง)
- **Terminal Output**: แสดงข้อความ Prompt เพื่อให้ User คัดลอกไปใช้ต่อได้ (แทนการบันทึกไฟล์)

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| `luma_core/actions/quality_actions.py` | 🔴 High | ต้องลบการสร้างไฟล์ prompt และแก้ไขการ Resolve `target_dir` |
| `luma_core/tools.py` | 🟡 Medium | ตรวจสอบการใช้ `resolve_project_target_dir()` ในเครื่องมือต่างๆ เช่น `generate_draft_code_review` |
| `luma_core/tools.py` | 🟡 Medium | ปรับปรุงฟังก์ชัน `resolve_project_target_dir()` และ `get_git_worktree_path()` ให้รองรับ worktree detection |

### 3.2 Breaking Changes
- ไม่พบ Breaking Changes ในระดับ API แต่พฤติกรรมการเขียนไฟล์จะเปลี่ยนไป (ไปอยู่ที่ Worktree แทน Main Repo) ซึ่งเป็นสิ่งที่ต้องการ

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Python และ Git CLI รองรับการตรวจสอบ Worktree |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | |
| Infrastructure รองรับหรือไม่? | ✅ | |

### 4.2 Time Feasibility
- **Estimated Effort**: 1-2 days
- **Feasible?**: ✅

---

## 5. Security Analysis

### 5.1 Sensitive Data
- **Code Review Content**: อาจมีข้อมูลสำคัญของ Code ในรายงาน แต่เนื่องจากเป็นการบันทึกในเครื่อง Local ของ User จึงถือว่าอยู่ในขอบเขตความปลอดภัยมาตรฐาน

### 5.2 Attack Vectors
- **Path Traversal**: การ Resolve Path ต้องระวังไม่ให้สามารถเขียนไฟล์นอกขอบเขตที่กำหนดได้ (แต่เนื่องจากเป็นการเขียนใน Project Root จึงมีความเสี่ยงต่ำ)

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| การ Resolve Path ผิดพลาดทำให้หาไฟล์ Git ไม่เจอ | 🟡 Medium | 🟡 Medium | 4 | ใช้คำสั่ง `git rev-parse --show-toplevel` เพื่อยืนยัน Root เสมอ |

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary
การแก้ไขนี้จะช่วยลดความซับซ้อนและไฟล์ขยะใน Workspace (#55) พร้อมทั้งปรับปรุง DX (Developer Experience) สำหรับผู้ที่ใช้งาน Git Worktree เป็นประจำ (#56) โดยการทำให้ Luma ฉลาดพอที่จะรู้ว่าตัวเองกำลังทำงานอยู่ในบริบทใด

### 9.2 Recommendations
1. ใช้ฟังก์ชันกลางใน `luma_core/tools.py` (`resolve_project_target_dir()`) สำหรับการ Resolve Path ทั้งหมด เพื่อให้เกิดความสม่ำเสมอทั่วทั้งระบบ
2. ในการทดสอบ (TDD) ควรสร้าง Temporary Git Repository พร้อม Worktree เพื่อจำลองสถานการณ์จริง

### 9.3 Next Steps
- [ ] สร้าง Failing Test สำหรับกรณี Worktree Path Resolution
- [ ] แก้ไข `quality_actions.py` เพื่อลบโค้ดสร้างไฟล์ prompt
- [ ] ปรับปรุงการ Resolve Path ใน `action_code_review` และ `tools.py`
- [ ] รันการทดสอบและยืนยันผล

---

## 📎 Appendix

### Sign-off
| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Gemini CLI | 2026-04-09 | ✅ |