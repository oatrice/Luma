# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Fix worktree support for Select Issue action & Code Review |
| **Date** | Friday, April 10, 2026 |
| **Analyst** | Gemini |
| **Priority** | 🔴 High |
| **Status** | 📝 Draft |
| **Issue URL** | [Issue #64](https://github.com/oatrice/Luma/issues/64), [Issue #70](https://github.com/oatrice/Luma/issues/70) |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

> อธิบายปัญหาที่ต้องการแก้ไข

```
เมื่อใช้งาน Luma AI Architect V2 ใน Git worktree, การเลือก Issue (Select Issue action) และการทำ Code Review ไม่รองรับ worktree path อย่างถูกต้อง ทำให้เกิดปัญหาดังนี้:
1. สำหรับ Select Issue (`[2] 📥 Select Issue (from Kanban)`): ไฟล์ที่ถูกสร้างขึ้น (spec.md, plan.md, sbe.md) และ Git operations (เช่น การสร้าง branch, checkout) ถูกดำเนินการบน main repository แทนที่จะเป็น worktree ปัจจุบัน
2. สำหรับ Code Review: ฟังก์ชัน `get_git_changed_files()` และฟังก์ชันที่เกี่ยวข้องในการสร้างรายงาน Code Review ยังคงอ้างอิง path ของ main repository ทำให้ Code Review ไม่สามารถตรวจจับการเปลี่ยนแปลงที่เกิดขึ้นใน worktree ได้อย่างถูกต้อง และไฟล์รายงาน `code_review.md` ถูกบันทึกผิดตำแหน่ง (ใน main repo แทนที่จะเป็น worktree)

ปัญหานี้ส่งผลกระทบต่อ Developer ที่ใช้ worktree ในการพัฒนาแบบขนาน เนื่องจาก feature ที่พัฒนาและรายงานจะไม่ถูกจัดเก็บใน worktree ที่ถูกต้อง และกระบวนการ Code Review ไม่สามารถทำงานได้ตามที่ควรจะเป็น
```

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | Developer (ใช้ worktree) | เลือก Issue จาก Kanban แล้วให้ Luma ดำเนินการ Git operations และบันทึกไฟล์ทั้งหมดใน worktree ปัจจุบัน | สามารถทำงานใน worktree ได้อย่างราบรื่นและแยกการเปลี่ยนแปลงออกจาก main repository ได้อย่างชัดเจน |
| 2 | Developer (ใช้ worktree) | ทำ Code Review และให้ Luma ตรวจจับการเปลี่ยนแปลงและบันทึกรายงานใน worktree ปัจจุบัน | ได้รับ Code Review ที่ถูกต้องสำหรับงานใน worktree และรายงานถูกจัดเก็บในตำแหน่งที่เหมาะสม |

### 1.3 Acceptance Criteria

- [x] **AC1:** ฟังก์ชัน `_start_issues()` (สำหรับ Select Issue) ต้องเคารพ worktree path สำหรับ Git operations ทั้งหมด (เช่น การสร้าง branch และ checkout)
- [x] **AC2:** ฟังก์ชัน `_start_issues_headless()` ต้องเคารพ worktree path เช่นกัน
- [x] **AC3:** การทำงานของ Menu actions ทั้งหมดที่สร้างไฟล์ (เช่น spec.md, plan.md, sbe.md, code_review.md) ต้องใช้ `resolve_project_target_dir()` อย่างสอดคล้องกัน
- [x] **AC4:** Test case ที่เกี่ยวข้องกับ worktree path resolution (เช่น `tests/test_worktree_path_resolution.py`) ต้องผ่านทั้งหมด
- [x] **AC5:** ต้องมีการ Regression test เพื่อยืนยันว่าการทำงานปกติบน main repository (ไม่ใช่ worktree) ยังคงทำงานได้อย่างถูกต้อง
- [x] **AC6:** ฟังก์ชันใน `luma_core/tools.py` ที่ใช้ `DEFAULT_TARGET_DIR` เป็น default parameter ควรได้รับการปรับปรุงให้รับ `target_dir` parameter อย่างชัดเจน
- [x] **AC7:** `action_code_review()` และฟังก์ชัน downstream ทั้งหมดที่ถูกเรียกใช้ ต้องส่ง `target_dir` ที่ resolve แล้วไปยัง Git operations และการบันทึกไฟล์อย่างถูกต้อง

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    A[เริ่มต้น Luma ใน Git Worktree] --> B{ผู้ใช้เลือก Menu Action?}
    B -->|📥 Select Issue (from Kanban)| C[Luma ตรวจจับ Worktree Path]
    C --> D[สร้าง Branch ใน Worktree]
    D --> E[Check out Branch ใน Worktree]
    E --> F[สร้าง spec.md, plan.md, sbe.md ใน Worktree/docs/features/]
    F --> G[เข้าสู่สถานะ Coding ใน Worktree]
    G --> H{Coding เสร็จสิ้น?}
    H -->|ใช่| I[ผู้ใช้เลือก Code Review]
    I --> J[Luma ตรวจจับ Worktree Path และ Git Changes ใน Worktree]
    J --> K[สร้างรายงาน Code Review ใน Worktree]
    K --> L[สิ้นสุด]
    B -->|Action อื่นๆ (ที่ไม่เกี่ยวข้องโดยตรง)| L
```

### 2.2 Screen/Page Requirements

Not Applicable (CLI-based feature, no specific screen/page UI changes).

### 2.3 Input/Output Specification

#### Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Current Git Worktree Path | string | ✅ | Valid path to a git worktree |
| Issue Selection (via Kanban) | string | ✅ | Valid issue ID/name |
| User Actions | CLI input | ✅ | (e.g., menu choices) |

#### Outputs

| Field | Type | Description |
|-------|------|-------------|
| Git Branch Created | string | ชื่อ branch ที่ถูกสร้างใน worktree |
| Files Generated | list of strings | `spec.md`, `plan.md`, `sbe.md`, `code_review.md` ถูกบันทึกใน worktree |
| Code Review Report | markdown string | รายงาน Code Review ที่ถูกต้องตามการเปลี่ยนแปลงใน worktree |
| Git Operations | N/A | Git commands ที่ทำงานใน worktree |

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| `luma_core/actions/utils.py` | 🔴 High | ฟังก์ชัน `_start_issues()` และ `_start_issues_headless()` ต้องได้รับการแก้ไขเพื่อให้ใช้ worktree path อย่างถูกต้องสำหรับ Git operations. |
| `luma_core/tools.py` | 🔴 High | ฟังก์ชันที่เกี่ยวข้องกับ Git operations (เช่น `get_git_changed_files()`) และการสร้างไฟล์ที่ใช้ `DEFAULT_TARGET_DIR` ต้องได้รับการปรับปรุงให้รับ `target_dir` parameter อย่างชัดเจน. `resolve_project_target_dir()` ต้องถูกใช้บ่อยขึ้น. |
| `luma_core/config.py` | 🟡 Medium | `TARGET_DIR` ซึ่งใช้ `os.getcwd()` ในการกำหนดค่าเริ่มต้น อาจต้องพิจารณาให้เป็น dynamic หรือมีกลไก override ที่ชัดเจนยิ่งขึ้น. |
| `luma_core/actions/quality_actions.py` | 🔴 High | `action_code_review()` ต้องมั่นใจว่ามีการส่ง `target_dir` ที่ resolve แล้วไปยังฟังก์ชัน downstream ทั้งหมดที่เกี่ยวข้องกับ Git และการสร้าง/บันทึกไฟล์. |
| `luma_core/actions/plan_actions.py` | 🟢 Low | ปัจจุบันใช้ `resolve_project_target_dir()` ถูกต้องแล้ว แต่ต้องยืนยันความสอดคล้องหลังการแก้ไข. |
| LLM Agents (Analyst, Coder, Reviewer) | 🟡 Medium | การทำงานของ Agent เหล่านี้ขึ้นอยู่กับ path ของไฟล์ที่ถูกต้อง. การแก้ไขนี้จะช่วยให้ Agent ทำงานใน worktree ได้อย่างสมบูรณ์. |
| State Manager | 🟢 Low | ไม่มีการเปลี่ยนแปลงโดยตรง แต่ได้รับผลประโยชน์จากการดำเนินการที่ถูกต้อง. |
| GitHub Project Sync | 🟢 Low | ไม่มีการเปลี่ยนแปลงโดยตรง แต่ relies on correct git operations. |
| Pre-flight Checker, CI Checker | 🟢 Low | ไม่มีการเปลี่ยนแปลงโดยตรง แต่ relies on correct git operations and file paths. |

### 3.2 Breaking Changes

- [ ] **BC1:** No anticipated breaking changes if `target_dir` is introduced as an optional parameter with a sensible default (e.g., falling back to `DEFAULT_TARGET_DIR` if not provided), ensuring backward compatibility for non-worktree scenarios.

### 3.3 Backward Compatibility Plan

```
เพื่อให้มั่นใจว่าไม่มี Breaking Changes, การแก้ไขฟังก์ชันใน `luma_core/tools.py` และ `luma_core/actions/` จะเป็นการเพิ่ม `target_dir` เป็น optional parameter ในฟังก์ชันที่เกี่ยวข้อง. หาก `target_dir` ไม่ได้ถูกส่งผ่านเข้ามา (ในกรณีของ Main repository หรือการทำงานแบบเดิม), ฟังก์ชันจะยังคงใช้ค่า default ซึ่งอ้างอิงจาก Main repository หรือ `os.getcwd()` เพื่อให้การทำงานในปัจจุบันยังคงไม่ได้รับผลกระทบ. การใช้ `resolve_project_target_dir()` จะถูกนำมาใช้เพื่อกำหนด `target_dir` สำหรับ Worktree scenarios.
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

> [!IMPORTANT]
> **Android Build Policy**: MUST use scripts in `Android/scripts/` (e.g., `build_android.sh`) instead of direct `./gradlew` to ensure correct JDK version (Java 21).

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Python, Git, และ Git worktree เป็นเทคโนโลยีหลักที่ Luma ใช้งานอยู่แล้ว และ `gh` CLI ก็รองรับ. |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | ทีมมีความเข้าใจใน Python, Git, และโครงสร้าง codebase ของ Luma เป็นอย่างดี. |
| Infrastructure รองรับหรือไม่? | ✅ | การแก้ไขนี้ไม่ต้องการ Infrastructure เพิ่มเติม. |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | 3-5 วัน | ครอบคลุมการวิเคราะห์, การแก้ไขหลายไฟล์, และการเขียน/แก้ไข Test cases. |
| **Deadline** | N/A | |
| **Buffer Time** | 1 วัน | สำหรับการแก้ไขปัญหาที่ไม่คาดคิดหรือการปรับปรุงเพิ่มเติม. |
| **Feasible?** | ✅ | เป็นไปได้ในกรอบเวลาที่กำหนด. |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----------|----------|
| N/A | N/A | เป็นการพัฒนา feature ภายใน ไม่เกี่ยวข้องกับงบประมาณภายนอกโดยตรง |
| **Total** | N/A | |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| N/A | N/A | ไม่มีการแนะนำ Sensitive Data ใหม่ |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| N/A | N/A | ไม่มีการแนะนำ Attack Vectors ใหม่ |

### 5.3 Authentication & Authorization

```
ไม่มีการเปลี่ยนแปลงในกลยุทธ์ Authentication & Authorization. การทำงานยังคงใช้การตรวจสอบสิทธิ์ GitHub CLI (`gh`) ที่มีอยู่เดิม.
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Response Time | < 500ms | N/A | การเปลี่ยนแปลง path ของ Git operations ไม่น่าส่งผลกระทบต่อประสิทธิภาพอย่างมีนัยสำคัญ |
| Throughput | N/A | N/A | |
| Error Rate | < 0.1% | N/A | |

### 6.2 Scalability Plan

| Scenario | Expected Users | Scaling Strategy |
|----------|---------------|------------------|
| Normal | [X] users | การรองรับ worktree เป็นการเพิ่มประสิทธิภาพการทำงานของแต่ละ user ไม่ได้เพิ่ม load โดยรวม |
| Peak | [X] users | N/A |
| Growth (1yr) | [X] users | N/A |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|------|-----------------|-----------------|-----|
| Worktree Support | Luma ไม่รองรับ Git worktree อย่างสมบูรณ์ในฟังก์ชันหลักบางส่วน (Select Issue, Code Review), ทำให้ Git operations และการบันทึกไฟล์เกิดขึ้นใน main repository | Luma รองรับ Git worktree อย่างสมบูรณ์, โดยทุก Git operations และการบันทึกไฟล์จะถูกดำเนินการภายใน worktree ปัจจุบัน | การใช้ `resolve_project_target_dir()` อย่างไม่สอดคล้องกัน และการอ้างอิง `DEFAULT_TARGET_DIR` ที่เป็น static ในฟังก์ชันสำคัญ |
| User Experience | Developer ที่ใช้ worktree ต้องจัดการไฟล์และ Git operations นอก Luma เพิ่มเติม เพื่อให้มั่นใจว่าการเปลี่ยนแปลงอยู่ใน worktree ที่ถูกต้อง | Developer สามารถทำงานใน worktree ผ่าน Luma ได้อย่างเต็มที่ โดย Luma จะจัดการ Git operations และไฟล์ใน worktree โดยอัตโนมัติ | ความไม่สะดวกในการทำงานกับ worktree และความเสี่ยงที่ข้อมูลจะถูกบันทึกผิดที่ |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| Regression ใน Main repository (non-worktree) scenarios | 🟡 Medium | 🔴 High | 6 | สร้างและรัน unit และ integration tests ที่ครอบคลุมทั้ง worktree และ non-worktree scenarios อย่างละเอียด. |
| ตกหล่นฟังก์ชันที่ใช้ `DEFAULT_TARGET_DIR` ที่ต้องการการแก้ไข | 🟡 Medium | 🟡 Medium | 4 | ทำการ `grep` หรือค้นหา `DEFAULT_TARGET_DIR` ใน codebase เพื่อระบุทุกจุดที่ต้องพิจารณาแก้ไข. ตรวจสอบ code review อย่างเข้มงวด. |
| ความซับซ้อนในการส่ง `target_dir` ผ่าน nested function calls | 🟢 Low | 🟡 Medium | 2 | Refactor โค้ดอย่างระมัดระวัง, อาจพิจารณาใช้ context object หรือ global variable ชั่วคราวสำหรับการส่ง `target_dir` ใน scope ที่จำกัด. |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|------|--------|--------------|
| Requirement | ✅ Clear | ความต้องการในการสนับสนุน Git worktree อย่างเต็มรูปแบบในฟังก์ชัน Select Issue และ Code Review มีความชัดเจนและสำคัญต่อประสบการณ์ Developer. |
| Feature | ✅ Defined | Feature มีขอบเขตที่ชัดเจน โดยมุ่งเน้นที่การแก้ไขการจัดการ worktree path ในฟังก์ชันหลักของ Luma. |
| Impact | ⚠️ Medium | การแก้ไขจะส่งผลกระทบต่อหลายไฟล์ใน `luma_core/actions` และ `luma_core/tools` ซึ่งเป็นส่วนประกอบหลักของระบบ. |
| Feasibility | ✅ Feasible | การเปลี่ยนแปลงสามารถทำได้ด้วยเทคโนโลยีและทักษะที่มีอยู่ โดยใช้ความพยายามปานกลาง. |
| Security | ✅ Acceptable | ไม่มีผลกระทบด้านความปลอดภัยที่สำคัญ. |
| Performance | ✅ Acceptable | ไม่มีการเปลี่ยนแปลงประสิทธิภาพที่คาดการณ์ไว้. |
| Risk | ⚠️ Some Risks | มีความเสี่ยงปานกลางในเรื่อง regression และการตกหล่นจุดที่ต้องแก้ไข แต่มีแผนการบรรเทาที่ชัดเจน. |

### 9.2 Recommendations

1.  **Standardize `resolve_project_target_dir()`:** ทำให้การใช้ฟังก์ชัน `resolve_project_target_dir()` เป็นมาตรฐานในทุกส่วนของ codebase ที่ต้องการทราบ path ของ project/worktree ปัจจุบัน.
2.  **Explicit `target_dir` Parameter:** Refactor ฟังก์ชันใน `luma_core/tools.py` และ `luma_core/actions/` ให้รับ `target_dir` เป็น explicit parameter แทนการพึ่งพา `DEFAULT_TARGET_DIR` ที่เป็น static.
3.  **Comprehensive Testing:** พัฒนาและรันชุดทดสอบที่ครอบคลุมทั้ง worktree และ non-worktree scenarios เพื่อป้องกัน regression และยืนยันความถูกต้องของการเปลี่ยนแปลง.

### 9.3 Next Steps

- [x] สร้าง Detailed Implementation Plan สำหรับการแก้ไข.
- [ ] พัฒนา Failing Tests (RED phase) สำหรับ scenarios ที่เกี่ยวข้องกับ worktree ที่ยังทำงานไม่ถูกต้อง.
- [ ] Implement Code เพื่อแก้ไขปัญหาและทำให้ Tests ผ่าน (GREEN phase).
- [ ] Refactor Code เพื่อปรับปรุงโครงสร้างและความชัดเจน โดยยังคงรักษาให้ Tests ทั้งหมดผ่าน (REFACTOR phase).

---

## 📎 Appendix

### Related Documents

- [GitHub Issue #64](https://github.com/oatrice/Luma/issues/64)
- [GitHub Issue #70](https://github.com/oatrice/Luma/issues/70)
- `luma_core/tools.py`
- `luma_core/actions/utils.py`
- `luma_core/actions/quality_actions.py`
- `luma_core/config.py`

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | Gemini | Friday, April 10, 2026 | ✅ |
| Tech Lead | [Name] | [Date] | ⬜ |
| PM | [Name] | [Date] | ⬜ |