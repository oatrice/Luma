# Analysis Template

> 📋 Template สำหรับการวิเคราะห์ก่อนเริ่มพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Restore: Auto-export failed prompt when LLM fails with human-readable timestamp |
| **Date** | 2026-04-09 |
| **Analyst** | AI Assistant |
| **Priority** | 🔴 High |
| **Status** | 📝 Draft |
| **Issue URL** | [Issue #67](https://github.com/your_org/your_repo/issues/67) |

---

## 1. Requirement Analysis

### 1.1 Problem Statement

> อธิบายปัญหาที่ต้องการแก้ไข

```
ฟีเจอร์ auto-export failed prompt ที่สำคัญสำหรับการ Debug และวิเคราะห์ข้อผิดพลาดของ LLM ได้ถูกลบออกไปใน commit `1aa97f2` ทำให้ผู้ใช้งานไม่มีกลไกอัตโนมัติในการกู้คืน prompt ที่ล้มเหลวเพื่อนำไปใช้ในการวิเคราะห์ภายนอก นอกจากนี้ timestamp ที่ใช้ในชื่อไฟล์เดิมเป็น Unix timestamp ซึ่งอ่านเข้าใจยาก จึงต้องการเปลี่ยนเป็น format ที่ human-readable มากขึ้น เพื่อให้ง่ายต่อการจัดการและค้นหาไฟล์
```

### 1.2 User Stories

| # | As a | I want to | So that |
|---|------|-----------|---------|
| 1 | Developer | Have failed LLM prompts auto-exported as a `.md` file | I can easily debug and analyze the cause of LLM failures. |
| 2 | Developer | Have the exported prompt filenames use a human-readable timestamp (YYYYMMDD_HHMMSS) | I can easily identify, sort, and manage the exported prompt files. |
| 3 | System | Automatically enable prompt export (`LUMA_EXPORT_PROMPTS=true`) when an LLM fails after retries | Users don't miss critical debugging information in case of LLM issues. |

### 1.3 Acceptance Criteria

- [x] **AC1:** เมื่อ LLM (Gemini CLI) failed/timeout หลังจาก retry ครบแล้ว ระบบต้องทำการ auto-export prompt เป็นไฟล์ `.md`
- [x] **AC2:** Timestamp ในชื่อไฟล์ที่ export ต้องเปลี่ยนจาก Unix timestamp เป็น human-readable format (`YYYYMMDD_HHMMSS`)
- [x] **AC3:** ไฟล์ที่ export ต้องถูกบันทึกที่ `docs/features/{issue_number}_issue-{id}/ai_brain/luma_failed_prompt_{timestamp}.md`
- [x] **AC4:** ค่า default ของ `LUMA_EXPORT_PROMPTS` ต้องถูกตั้งค่าเป็น `true` เพื่อให้ระบบ auto-export prompt โดยอัตโนมัติเมื่อพบ error จาก LLM
- [x] **AC5:** ต้องแสดงข้อความแจ้งเตือนผู้ใช้เกี่ยวกับการ export prompt ที่ชัดเจนตามที่กำหนด (`❌ Gemini CLI failed after retries. Exporting prompt to /path/to/ai_brain/luma_failed_prompt_20250409_210500.md for external AI.`)

---

## 2. Feature Analysis

### 2.1 User Flow

```mermaid
flowchart TD
    A[LLM Request Failed/Timeout] --> B{Retries Exhausted?}
    B -->|Yes| C[Check LUMA_EXPORT_PROMPTS Config]
    B -->|No| A
    C -->|True or Default True| D[Generate Human-Readable Timestamp]
    D --> E[Construct File Path: docs/features/{issue_number}_issue-{id}/ai_brain/luma_failed_prompt_{timestamp}.md]
    E --> F[Write Prompt to .md File]
    F --> G[Display Export Confirmation Message]
    G --> H[End Process]
    C -->|False| H
```

### 2.2 Screen/Page Requirements

> [!IMPORTANT]
> **Policy**: Web Full Implementation must be implemented and verified FIRST before Android/iOS logic.

| หน้าจอ | Actions | Components | UI Mock Status |
|--------|---------|------------|----------------|
| Console Output | Displaying export message | N/A | ✅ Done |

### 2.3 Input/Output Specification

#### Inputs

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `LLM_prompt` | string | ✅ | ไม่จำกัด |
| `LLM_response` | string | ✅ | ไม่จำกัด |
| `issue_number` | int | ✅ | ต้องเป็นตัวเลข, >0 |
| `issue_id` | string | ✅ | ไม่จำกัด, ใช้เป็นส่วนหนึ่งของชื่อโฟลเดอร์ |
| `LUMA_EXPORT_PROMPTS` | boolean | ❌ | `true` หรือ `false` (default: `true` เมื่อ LLM failed) |

#### Outputs

| Field | Type | Description |
|-------|------|-------------|
| `luma_failed_prompt_{timestamp}.md` | markdown file | ไฟล์ `.md` ที่มีเนื้อหาของ prompt ที่ล้มเหลว |
| Console Output Message | string | ข้อความแจ้งเตือนการ export prompt พร้อม path และ timestamp |

---

## 3. Impact Analysis

### 3.1 Affected Components

| Component | Impact Level | Description |
|-----------|--------------|-------------|
| `luma_core/llm.py` | 🔴 High | เป็น core logic ในการจัดการ LLM call และ error handling จำเป็นต้องเพิ่ม logic สำหรับการ export prompt และ timestamp formatting ในเมธอด `_generate()` |
| `luma_core/config.py` | 🟡 Medium | ต้องปรับค่า default ของ `LUMA_EXPORT_PROMPTS` ให้เป็น `true` เพื่อให้ฟีเจอร์ทำงานโดยอัตโนมัติเมื่อ LLM failed |
| `docs/features/` | 🟢 Low | จะมีการสร้างไดเรกทอรีและไฟล์ใหม่ภายใต้ไดเรกทอรีนี้เพื่อเก็บ prompt ที่ล้มเหลว |

### 3.2 Breaking Changes

- [ ] **BC1:** No breaking changes expected as this is restoring a previously removed feature and improving its functionality.

### 3.3 Backward Compatibility Plan

```
เนื่องจากเป็นการกู้คืนและปรับปรุงฟีเจอร์ที่เคยถูกลบไป จึงไม่ส่งผลกระทบต่อ Backward Compatibility โดยตรง แต่เป็นการเพิ่มความสามารถกลับคืนมา
```

---

## 4. Feasibility Analysis

### 4.1 Technical Feasibility

> [!IMPORTANT]
> **Android Build Policy**: MUST use scripts in `Android/scripts/` (e.g., `build_android.sh`) instead of direct `./gradlew` to ensure correct JDK version (Java 21).

| คำถาม | คำตอบ | หมายเหตุ |
|-------|-------|----------|
| เทคโนโลยีรองรับหรือไม่? | ✅ | Python มี library สำหรับจัดการไฟล์และวันที่อย่างครบถ้วน |
| ทีมมี Skills เพียงพอหรือไม่? | ✅ | เป็นงานที่สามารถทำได้โดยใช้ความรู้ Python พื้นฐานเกี่ยวกับการจัดการไฟล์, string formatting, และ datetime |
| Infrastructure รองรับหรือไม่? | ✅ | การเขียนไฟล์ลงบน local filesystem ไม่ต้องการ infrastructure พิเศษ |

### 4.2 Time Feasibility

| ประเด็น | รายละเอียด |
|--------|-----------|
| **Estimated Effort** | 1-2 days |
| **Deadline** | N/A |
| **Buffer Time** | 0.5 days |
| **Feasible?** | ✅ |

### 4.3 Budget Feasibility

| รายการ | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----------|----------|
| Development | Internal | N/A |
| **Total** | N/A | |

---

## 5. Security Analysis

### 5.1 Sensitive Data

| ข้อมูล | Sensitivity Level | Protection Method |
|--------|------------------|-------------------|
| LLM Prompts | 🟡 Sensitive | ไฟล์จะถูกเก็บไว้ใน local filesystem โดยมี `.gitignore` ป้องกันไม่ให้ commit เข้าสู่ Git. ควรพิจารณาถึงเนื้อหาที่อาจมีข้อมูลส่วนตัวหรือ confidential data. |
| API Keys/Secrets | 🔴 Critical | ต้องมั่นใจว่า prompt ที่ export จะไม่หลุดข้อมูล API Keys หรือ Secrets ออกไป. ควร scrub ข้อมูลที่อ่อนไหวออกจาก prompt ก่อน export หากมีโอกาสหลุด. |

### 5.2 Attack Vectors

| Vector | Risk Level | Mitigation |
|--------|-----------|------------|
| Path Traversal | 🟢 Low | ชื่อไฟล์และ path ถูกสร้างขึ้นโดยระบบภายในโดยใช้ `issue_number`, `issue_id`, และ timestamp ซึ่งลดความเสี่ยงจากการถูก manipulated ได้ |
| Data Leakage | 🟡 Medium | ไฟล์ `.md` ที่ export อาจมีข้อมูลที่ละเอียดอ่อน. mitigation คือ การตรวจสอบอย่างละเอียดว่าไม่มี sensitive data หลุด และผู้ใช้รับทราบถึงความเสี่ยงนี้. |

### 5.3 Authentication & Authorization

```
การ export prompt เกิดขึ้นใน local machine ไม่เกี่ยวข้องโดยตรงกับระบบ Authentication & Authorization ของแอปพลิเคชัน. การเข้าถึงไฟล์ที่ export จะขึ้นอยู่กับการจัดการสิทธิ์ของ OS ที่ผู้ใช้ใช้งานอยู่.
```

---

## 6. Performance & Scalability Analysis

### 6.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Latency (export) | < 100ms | N/A |
| Throughput (export) | N/A | N/A |
| Error Rate (export) | < 0.1% | N/A |

### 6.2 Scalability Plan

| Scenario | Expected Users | Scaling Strategy |
|----------|---------------|------------------|
| Normal | 1 user | N/A (local operation) |
| Peak | N/A | N/A |
| Growth (1yr) | N/A | N/A |

---

## 7. Gap Analysis

| ด้าน | As-Is (ปัจจุบัน) | To-Be (ต้องการ) | Gap |
|------|-----------------|-----------------|-----|
| Auto-export Failed Prompt | ไม่มีฟีเจอร์นี้ | มีฟีเจอร์ auto-export prompt เมื่อ LLM failed | ฟีเจอร์ที่หายไป |
| Timestamp Format | N/A (ฟีเจอร์ถูกลบ) | Human-readable (`YYYYMMDD_HHMMSS`) | ความสะดวกในการใช้งานและจัดการไฟล์ |
| Default Export Behavior | N/A (ฟีเจอร์ถูกลบ) | `LUMA_EXPORT_PROMPTS=true` โดย default เมื่อ LLM failed | การรับประกันว่า prompt ที่ล้มเหลวจะไม่ถูกละเลย |

---

## 8. Risk Analysis

| Risk | Probability | Impact | Score | Mitigation Plan |
|------|-------------|--------|-------|-----------------|
| ข้อมูลละเอียดอ่อนรั่วไหลใน prompt ที่ export | 🟡 Medium | 🔴 High | 6 | ตรวจสอบเนื้อหาของ prompt อย่างละเอียดก่อน export, ให้ผู้ใช้รับทราบถึงความเป็นไปได้นี้, พิจารณาเพิ่มความสามารถในการ scrub sensitive data (ถ้าจำเป็นในอนาคต) |
| ผู้ใช้ไม่รับรู้ถึงการ export ไฟล์ | 🟢 Low | 🟡 Medium | 2 | มีการแสดงข้อความแจ้งเตือนที่ชัดเจนบน console |
| ปัญหาการเขียนไฟล์ (เช่น permissions) | 🟢 Low | 🟡 Medium | 2 | ใช้ try-except block ในการจัดการ error การเขียนไฟล์และแจ้งเตือนผู้ใช้ |

> **Risk Score:** Probability × Impact (High=3, Medium=2, Low=1)

---

## 9. Summary & Recommendations

### 9.1 Analysis Summary

| หมวด | Status | Key Findings |
|------|--------|--------------|
| Requirement | ✅ Clear | ความต้องการในการกู้คืนฟีเจอร์และปรับปรุง timestamp ชัดเจน |
| Feature | ✅ Defined | ฟังก์ชันการทำงานและรายละเอียดการบันทึกไฟล์ถูกกำหนดไว้แล้ว |
| Impact | ⚠️ Medium | มีการเปลี่ยนแปลงใน `llm.py` และ `config.py` ซึ่งเป็น core component |
| Feasibility | ✅ Feasible | สามารถทำได้ด้วยเทคโนโลยีและทักษะที่มีอยู่ ไม่มีความซับซ้อนทางเทคนิค |
| Security | ⚠️ Needs Review | มีความเสี่ยงที่ข้อมูลละเอียดอ่อนใน prompt อาจรั่วไหล ควรมีการตรวจสอบและแจ้งเตือนผู้ใช้ |
| Performance | ✅ Acceptable | ผลกระทบต่อประสิทธิภาพน้อยมากเนื่องจากเป็นกระบวนการที่เกิดเฉพาะเมื่อ LLM failed |
| Risk | ⚠️ Some Risks | ความเสี่ยงหลักคือการรั่วไหลของข้อมูลละเอียดอ่อนใน prompt |

### 9.2 Recommendations

1.  **ดำเนินการกู้คืนและปรับปรุงฟีเจอร์** auto-export failed prompt ตามที่ระบุไว้
2.  **เพิ่มการแจ้งเตือนผู้ใช้ที่ชัดเจน** ถึงความเสี่ยงที่อาจมีข้อมูลละเอียดอ่อนใน prompt ที่ export
3.  **พิจารณาเพิ่มความสามารถในการ scrub ข้อมูลอ่อนไหว** ออกจาก prompt ก่อน export ในอนาคต หากพบว่ามีกรณีที่จำเป็นต้องทำ

### 9.3 Next Steps

- [x] สร้าง branch สำหรับพัฒนานี้
- [ ] เขียน test cases (Red phase) สำหรับการ auto-export prompt, timestamp format, และการบันทึกไฟล์
- [ ] Implement code (Green phase) ใน `luma_core/llm.py` และ `luma_core/config.py`
- [ ] Refactor code (Refactor phase) หากจำเป็น
- [ ] ทดสอบและยืนยันการทำงานของฟีเจอร์

---

## 📎 Appendix

### Related Documents

- [Commit `1aa97f2b9621567f7d0f1d3b2c384c21442c7c55`](https://github.com/your_org/your_repo/commit/1aa97f2b9621567f7d0f1d3b2c384c21442c7c55)

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Analyst | AI Assistant | 2026-04-09 | ✅ |
| Tech Lead | [Name] | [Date] | ⬜ |
| PM | [Name] | [Date] | ⬜ |