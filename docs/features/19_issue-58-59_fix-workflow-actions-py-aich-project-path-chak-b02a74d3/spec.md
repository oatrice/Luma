# Specification Template (SBE)

> 📋 Specification by Example สำหรับ Feature นี้

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| **Feature Name** | Fix workflow_actions.py PR path issue & Add LLM timeout controls |
| **Date** | April 9, 2026 |
| **Spec Author** | Senior Technical Spec Writer |
| **Status** | ✅ Complete |
| **Issue Number** | 58-59 |

---

## 1. บทนิยาม (Glossary)

| คำศัพท์ | ความหมาย |
|---------|---------|
| Worktree | Git worktree - การสร้าง working directory หลายตัวจาก repository เดียว |
| `resolve_project_target_dir()` | Function ที่ตรวจสอบว่าอยู่ใน worktree หรือไม่ และคืนค่า path ที่ถูกต้อง |
| `target_dir` | Path ที่ใช้จริงหลังจาก resolve worktree |
| `is_retryable` | Function ที่ตรวจสอบว่า error type ควร retry หรือไม่ |
| `LUMA_LLM_TIMEOUT_SCALE` | Environment variable สำหรับปรับ timeout (เช่น 0.5 = ครึ่งเวลา) |
| `LUMA_MAX_LLM_RETRIES` | Environment variable สำหรับจำกัดจำนวน retry |
| `LUMA_EXPORT_PROMPTS` | Environment variable สำหรับเปิด prompt export mode |
| `PromptExportModel` | Class ที่บันทึก prompt เป็นไฟล์ .md แทนการเรียก LLM |

---

## 2. กฎทางธุรกิจ (Business Rules)

### BR-58-1: Worktree Path Resolution
> เมื่อ Luma รันจาก worktree ทุก Git operations ต้องใช้ worktree path ไม่ใช่ main repo path

### BR-58-2: Git Branch Detection
> การตรวจสอบ branch ต้องทำบน worktree path เพื่อให้ได้ branch ที่ถูกต้อง

### BR-59-1: Import Completeness
> ทุก function ที่ถูกใช้ใน module ต้องถูก import อย่างถูกต้อง

### BR-59-2: Configurable LLM Timeout
> Timeout ของ LLM calls ต้องสามารถปรับได้ผ่าน `LUMA_LLM_TIMEOUT_SCALE` โดยมี minimum 10 วินาที

### BR-59-3: Configurable LLM Retries
> จำนวน retry attempts ต้องสามารถจำกัดได้ผ่าน `LUMA_MAX_LLM_RETRIES`

### BR-59-4: Prompt Export Mode
> เมื่อเปิด `LUMA_EXPORT_PROMPTS` ระบบต้องบันทึก prompt เป็นไฟล์ .md และ load response จาก `.response.md` เมื่อมีไฟล์นั้นอยู่

---

## 3. สถานการณ์และตัวอย่าง (Scenarios & Examples)

### Scenario 1: Issue #58 - PR Creation from Worktree

```gherkin
Given ผู้ใช้รัน Luma จาก Git worktree ที่ path /Users/oatrice/Software-projects/Cerebro-worktrees/feat-4-5-3
And worktree นี้อยู่บน branch "feat/4-5-3-dashboard-snapshots"
And state.active_branch มีค่า "feat/4-5-3-dashboard-snapshots"
When Luma เริ่มกระบวนการสร้าง PR
Then Luma ต้องตรวจจับ branch ปัจจุบันได้ว่าเป็น "feat/4-5-3-dashboard-snapshots"
And ไม่ต้องขึ้น error "Branch mismatch"
And PR ต้องถูกสร้างจาก worktree path ไม่ใช่ main repo path
```

**ตัวอย่างข้อมูล:**
| ตัวแปร | ค่าใน main repo | ค่าใน worktree | ค่าที่คาดหวัง |
|--------|----------------|---------------|--------------|
| `proj["path"]` | `/Users/oatrice/Software-projects/Cerebro` | `/Users/oatrice/Software-projects/Cerebro` | - |
| `target_dir` | - | `/Users/oatrice/Software-projects/Cerebro-worktrees/feat-4-5-3` | ใช้ค่านี้ |
| `current_branch` | `main` | `feat/4-5-3-dashboard-snapshots` | `feat/4-5-3-dashboard-snapshots` |

### Scenario 2: Issue #59 - LLM Fallback Retry

```gherkin
Given LLM call เกิด error
And มี fallback model ให้ retry
When ระบบตรวจสอบว่าควร retry หรือไม่
Then ระบบต้องเรียกใช้ `is_retryable()` ได้โดยไม่เกิด NameError
```

**ตัวอย่างข้อมูล:**
| Error Type | is_retryable ค่า |
|-----------|-----------------|
| TIMEOUT | True |
| RATE_LIMIT | False |
| UNKNOWN | True |

---

## 4. ข้อจำกัดและ Assumptions

### Assumptions
- `resolve_project_target_dir()` ทำงานถูกต้อง (ถูกทดสอบแล้วใน `quality_actions.py`)
- `is_retryable()` มีอยู่ใน `luma_core.error_classifier` และทำงานถูกต้อง

### Constraints
- แก้ไขต้องไม่เปลี่ยน API หรือ interface ของ functions ที่มีอยู่
- ต้อง backward compatible กับการรันจาก main repo (ไม่ใช่ worktree)

---

## 5. การยอมรับ (Acceptance Criteria)

| ID | Criteria | Status |
|----|----------|--------|
| AC-58-1 | รัน Luma จาก worktree แล้ว detect branch ถูกต้อง | ✅ Pass |
| AC-58-2 | PR ถูกสร้างจาก worktree ไม่ใช่ main repo | ✅ Pass |
| AC-58-3 | Git operations ทั้งหมดทำงานบน worktree path | ✅ Pass |
| AC-59-1 | ไม่มี NameError 'is_retryable' เมื่อ LLM fallback | ✅ Pass |
| AC-59-2 | `LUMA_LLM_TIMEOUT_SCALE` ปรับ timeout ได้ถูกต้อง (min 10s) | ✅ Pass |
| AC-59-3 | `LUMA_MAX_LLM_RETRIES` จำกัด retry ได้ถูกต้อง | ✅ Pass |
| AC-59-4 | `LUMA_EXPORT_PROMPTS` บันทึก prompt เป็นไฟล์ .md | ✅ Pass |
| AC-59-5 | `PromptExportModel` load response จาก `.response.md` ได้ถูกต้อง | ✅ Pass |

---

## 6. เอกสารอ้างอิง

- Issue #56 - แก้ไขปัญหาเดียวกันใน `quality_actions.py`
- Issue #58 - workflow_actions.py path issue
- Issue #59 - LLM timeout controls
