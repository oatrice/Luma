# Issue 103: Fix invalid branch name suggestion with special characters in Select issue menu

ปัญหานี้เกิดจากการที่ฟังก์ชันสร้างชื่อ git branch (ทั้งแบบ default และที่ได้จาก AI) ไม่ได้ทำความสะอาด (sanitize) ตัวอักษรพิเศษบางตัว เช่น เครื่องหมาย `:` ทำให้ได้ชื่อ branch ที่ไม่ถูกต้องตามมาตรฐานของ git หรือทำให้เกิดปัญหาในการใช้งาน

## Proposed Changes

### `luma_core/actions/utils.py`

#### [MODIFY] luma_core/actions/utils.py
- เพิ่มฟังก์ชัน `_sanitize_branch_name(name: str) -> str` เพื่อจัดการทำความสะอาดชื่อ:
  - ใช้ Regex: `re.sub(r'[^a-zA-Z0-9_\-/]', '-', name)` เปลี่ยนตัวอักษรที่ไม่ใช่ตัวอักษรภาษาอังกฤษ ตัวเลข, `_`, `-`, หรือ `/` ให้กลายเป็น `-`
  - ใช้ Regex: `re.sub(r'-+', '-', name)` เพื่อยุบ `-` ที่ติดกันหลายตัวให้เหลือตัวเดียว
  - ทำการ `strip('-')` ทั้งหน้าและหลัง
- แก้ไข `_build_default_branch_name` ให้นำ `title` มาผ่านฟังก์ชัน `_sanitize_branch_name` ก่อนสร้างเป็น `slug`
- แก้ไข `_normalize_branch_suggestions` ให้นำ `candidate` แต่ละตัวจาก AI มาทำความสะอาดด้วย `_sanitize_branch_name` ก่อนที่จะนำไปตรวจความถูกต้องด้วย `_is_valid_branch_name` เพื่อให้สามารถใช้ชื่อที่ AI แนะนำได้มากขึ้นแทนที่จะตัดทิ้งเลย

### `tests/test_branch_name_sanitization.py`

#### [NEW] tests/test_branch_name_sanitization.py
- สร้างไฟล์ทดสอบใหม่สำหรับทดสอบกระบวนการทำความสะอาดชื่อ branch โดยเฉพาะ รองรับกระบวนการ TDD:
  - Test `_sanitize_branch_name` กับกรณีที่มีตัวอักษรพิเศษเช่น `:`, `?`, `*`, `[`, `]`, `\`, ช่องว่าง
  - Test `_build_default_branch_name` 
  - Test `_normalize_branch_suggestions` ว่ามีการแก้ไขชื่อจาก AI ที่มีตัวอักษรพิเศษและเก็บไว้เป็นคำตอบที่ใช้ได้

## Verification Plan

### Automated Tests
- รันคำสั่ง `pytest tests/test_branch_name_sanitization.py` เพื่อทดสอบ logic การทำความสะอาดชื่อ
- รัน `pytest tests/` ภาพรวมเพื่อให้มั่นใจว่าไม่ได้ทำให้อะไรพัง

### Manual Verification
- สั่ง `luma` และเลือกเมนู `Select Issue` กับ issue ที่มีเครื่องหมาย `:` หรือตัวอักษรพิเศษอื่นๆ ในชื่อ
- สังเกตรายชื่อ branch ที่ระบบแนะนำว่าถูกตัดตัวอักษรพิเศษออกและอยู่ในรูปแบบที่ถูกต้องหรือไม่
