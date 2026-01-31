# SBE & Draft Code Review Implementation

เพิ่มฟีเจอร์สำคัญ 2 อย่างให้ Luma:
1. **SBE (Specification by Example):** สร้าง specs จาก issue
2. **Draft Code Review:** สร้าง draft PR/Review พร้อม full diff context

---

## 1. Draft Code Review Feature (Latest)

### Goal
ช่วยให้ Developer สร้าง Code Review Draft ที่มี Full Context (Diff, Commits, Stats) ได้ทันที เพื่อใช้ส่งต่อให้ AI หรือ Reviewer โดยไม่ต้อง copy-paste เอง

### Implementation

#### [NEW] `generate_draft_code_review()` in `tools.py`
- เก็บ logic การดึง git info (commits, stats, full diff)
- สร้างไฟล์ `draft_code_review.md`

#### [MODIFY] `publisher.py`
- Update ให้ check `draft_code_review.md` ก่อน
- ถ้ามีไฟล์นี้ ให้ใช้ content ในนั้นเป็น context ในการ generate PR body แทนการดึง git ใหม่ (ซึ่งอาจได้ context น้อยกว่า)

#### [MODIFY] `actions.py` & `main.py`
- เพิ่ม Action `action_generate_draft`
- เพิ่ม Menu Option `D`: "📑 Draft Code Review"

---

## 2. SBE (Specification by Example) Feature (Completed)

เพิ่มฟีเจอร์ให้ Luma สามารถ **สร้างและอ่าน** Specification by Example (SBE) specs ในรูปแบบ Markdown

### Core Module
#### `luma_core/sbe.py`
- `Scenario`, `SBESpec` dataclasses
- `parse_sbe_spec()`, `validate_sbe_spec()`, `generate_sbe_from_issue()`

### SBE Agent
#### `luma_core/agents/sbe_agent.py`
- AI-powered SBE generator using LLM

### Template
#### `docs/templates/sbe_template.md`

### Integration
- `main.py`: Menu Option `S`
- `actions.py`: `action_generate_sbe()`

### Tests
- `tests/test_sbe.py`: Unit tests (9 passed)
