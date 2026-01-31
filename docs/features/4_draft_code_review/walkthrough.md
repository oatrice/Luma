# Feature Implementation Walkthrough: SBE & Draft Code Review

## Summary
เพิ่มฟีเจอร์ใหม่ 2 อย่างใน Luma v1.1.0+:
1. **SBE (Specification by Example)**: สร้าง specs จาก issue
2. **Draft Code Review**: สร้าง draft markdown พร้อม full diff

---

## 1. Draft Code Review (New)

### Changes
| File | Change |
|------|--------|
| `luma_core/tools.py` | Added `generate_draft_code_review()` |
| `luma_core/agents/publisher.py` | Updated to read `draft_code_review.md` |
| `luma_core/actions.py` | Added `action_generate_draft()` |
| `main.py` | Added menu option `D` |

### Usage
1. กด **D** เพื่อ Generate Draft
2. ไฟล์ `draft_code_review.md` จะถูกสร้าง (มี Full Diff)
3. แก้ไขไฟล์ได้ตามต้องการ
4. เมื่อกด **6** (Create PR), Publisher จะใช้ไฟล์นี้เป็น Context อัตโนมัติ

---

## 2. SBE (Specification by Example)

### Changes
| File | Description |
|------|-------------|
| `luma_core/sbe.py` | Core module |
| `luma_core/agents/sbe_agent.py` | AI Agent |
| `docs/templates/sbe_template.md` | Template |
| `tests/test_sbe.py` | Unit tests |

### Usage
1. Select Issue (Option 2)
2. กด **S**
3. Output: `docs/features/xxx/specs/sbe_issue-N.md`

---

## Test Results
```
✅ tests/test_sbe.py (9 passed)
✅ Manual verification of 'D' option: Success
✅ Manual verification of Publisher integration: Success
```
