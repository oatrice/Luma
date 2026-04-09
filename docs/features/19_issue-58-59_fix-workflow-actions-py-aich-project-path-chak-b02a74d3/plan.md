# Plan Template

> 📋 Template สำหรับวางแผนการพัฒนา Feature

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Fix workflow_actions.py PR path issue & Add LLM timeout controls |
| **Date** | April 9, 2026 |
| **Planner** | Senior Technical Planner |
| **Status** | ✅ Complete |
| **Issue Number** | 58-59 |

---

## 1. สรุปจาก Analysis

### 1.1 ปัญหาหลักที่ต้องแก้ไข

1. **Issue #58**: `workflow_actions.py` ใช้ `proj["path"]` ตรงๆ แทนที่จะใช้ `resolve_project_target_dir()` ทำให้ Git operations ทำงานผิดที่ (main repo แทน worktree)
2. **Issue #59**: `is_retryable` function ถูกใช้ใน `llm.py` แต่ไม่ได้ import ทำให้เกิด NameError เมื่อ fallback model chain ทำงาน

### 1.2 ขอบเขตการทำงาน (Scope)

- แก้ไข `workflow_actions.py` ให้ใช้ worktree path ถูกต้อง
- แก้ไข `llm.py` เพิ่ม missing import
- ไม่มีการเปลี่ยนแปลง logic หลักของระบบ

---

## 2. แผนการพัฒนา

### Phase 1: แก้ไข Issue #58 (Workflow Actions)

| งาน | รายละเอียด | ไฟล์ที่แก้ไข |
|-----|-----------|-------------|
| 1.1 | เพิ่ม import `resolve_project_target_dir` | `workflow_actions.py` บรรทัด 30 |
| 1.2 | แก้ไข branch check ให้ใช้ `target_dir` | `workflow_actions.py` บรรทัด 206-230 |
| 1.3 | แก้ไข screenshot sync ให้ใช้ `target_dir` | `workflow_actions.py` บรรทัด 262-309 |
| 1.4 | แก้ไข AI brain sync ให้ใช้ `target_dir` | `workflow_actions.py` บรรทัด 318-333 |
| 1.5 | แก้ไข publisher agent state | `workflow_actions.py` บรรทัด 434 |

### Phase 2: แก้ไข Issue #59 (LLM Import & Timeout Controls)

| งาน | รายละเอียด | ไฟล์ที่แก้ไข |
|-----|-----------|-------------|
| 2.1 | เพิ่ม import `is_retryable` และ `CredentialType` | `llm.py` บรรทัด 17-18 |
| 2.2 | เพิ่ม config variables (`LUMA_LLM_TIMEOUT_SCALE`, `LUMA_MAX_LLM_RETRIES`, `LUMA_EXPORT_PROMPTS`) | `config.py` บรรทัด 30-48 |
| 2.3 | Implement timeout scale logic ใน `GeminiCLIModel` | `llm.py` บรรทัด 152-164 |
| 2.4 | Implement `PromptExportModel` class | `llm.py` บรรทัด 689-770 |
| 2.5 | Update `get_llm()` ให้รองรับ export mode | `llm.py` บรรทัด 596-608 |

---

## 3. การทดสอบ

### 3.1 Test Cases

| TC ID | รายละเอียด | วิธีทดสอบ | ผลลัพธ์ที่คาดหวัง |
|-------|-----------|-----------|-----------------|
| TC-58-1 | Worktree branch detection | รัน Luma จาก worktree และสร้าง PR | ตรวจจับ branch ถูกต้อง ไม่มี "Branch mismatch" error |
| TC-58-2 | Git operations on worktree | สร้าง PR จาก worktree | PR ถูกสร้างจาก worktree path ถูกต้อง |
| TC-59-1 | LLM fallback retry | รัน workflow ที่ใช้ LLM จนเกิด error และ fallback | ไม่มี NameError 'is_retryable' |
| TC-59-2 | Timeout scale | ตั้งค่า `LUMA_LLM_TIMEOUT_SCALE=0.5` และเรียก LLM | Timeout ถูกลดลงครึ่งหนึ่ง (min 10s) |
| TC-59-3 | Max retries | ตั้งค่า `LUMA_MAX_LLM_RETRIES=1` และเรียก LLM | Retry แค่ครั้งเดียว |
| TC-59-4 | Prompt export | ตั้งค่า `LUMA_EXPORT_PROMPTS=true` และเรียก LLM | Prompt ถูกบันทึกเป็นไฟล์ .md |

### 3.2 Verification Steps

```bash
# Test Issue #58
cd /Users/oatrice/Software-projects/Cerebro-worktrees/feat-4-5-3
python3 ../../Luma/main.py --project 16

# Expected: ไม่มี "Branch mismatch" error และ PR ถูกสร้างได้
```

---

## 4. ความเสี่ยงและการบริหารจัดการ

| ความเสี่ยง | ระดับ | การแก้ไข |
|-----------|------|---------|
| แก้ไขอาจกระทบ flow อื่นใน workflow_actions.py | ต่ำ | เปลี่ยนแปลงเฉพาะบรรทัดที่จำเป็น โดยใช้ pattern เดียวกับ quality_actions.py |
| Import อาจมีชื่อ conflict | ต่ำ | ใช้ absolute import จาก `luma_core.error_classifier` |

---

## 5. สรุป

แผนการพัฒนาครอบคลุม:
- ✅ Issue #58: Worktree path resolution fix
- ✅ Issue #59: Missing import fix
- ✅ Test cases สำหรับ verification
- ✅ Risk assessment

**สถานะ**: พร้อมดำเนินการ (และเสร็จสิ้นแล้ว)
