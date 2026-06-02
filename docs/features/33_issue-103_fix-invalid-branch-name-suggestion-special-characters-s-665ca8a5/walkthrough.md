# สรุปการแก้ไข Issue 103 (Fix invalid branch name suggestion)

## ปัญหาที่พบ

### Root Cause 1: ตัวอักษรพิเศษใน issue title ไม่ถูก sanitize
เมื่อผู้ใช้เลือก `Select Issue` ถ้าชื่อของ issue นั้นๆ มีตัวอักษรพิเศษที่ไม่ได้รับอนุญาตให้เป็นชื่อ branch ของ git (เช่น `:`, `?`, `*`, `\`, หรือช่องว่างที่เกิดจากการต่อคำ) ระบบแนะนำชื่อ branch ก็จะนำตัวอักษรนั้นไปใช้ ทำให้เมื่อ git branch ถูกสร้างขึ้นจะเกิดข้อผิดพลาด

### Root Cause 2: Placeholder จาก PromptExportModel รั่วเข้า branch suggestion list
เมื่อ LLM ไม่สามารถตอบสนองได้ (เช่น prompt ถูก export ออกไปให้ AI ภายนอก) `PromptExportModel` จะคืนค่า placeholder string อย่าง:
```
[PROMPT EXPORTED] Your prompt was saved to: /Users/.../prompt_xxx.md
```
เดิม `_normalize_branch_suggestions` ไม่ได้กรอง string นี้ออก ทำให้หลังจากผ่าน `_sanitize_branch_name` (เนื่องจาก `/` ยังถูกรักษาไว้) string ยังผ่าน `_is_valid_branch_name` ได้ จึงปรากฏในเมนูและทำให้ระบบ crash

## สิ่งที่แก้ไข

1. **เพิ่มฟังก์ชัน `_sanitize_branch_name`** ใน `luma_core/actions/utils.py`:
   - แปลงตัวอักษรพิเศษทั้งหมดที่ไม่ใช่ `A-Z`, `a-z`, `0-9`, `_`, `-`, `/` ให้กลายเป็นขีดกลาง `-`
   - ยุบเครื่องหมายขีดกลางหลายๆ อันให้เหลือแค่อันเดียว
   - ตัดขีดกลางและ slashes ที่หัว/ท้ายออก

2. **อัปเดต `_build_default_branch_name`**:
   - ให้ประมวลผล slug ผ่านฟังก์ชัน `_sanitize_branch_name` ก่อนสร้างเป็น `feat/{issue}-slug`

3. **อัปเดต `_normalize_branch_suggestions`**:
   - นำชื่อที่ AI แนะนำมาผ่านการแปลงผ่าน `_sanitize_branch_name` ก่อน
   - ทำให้แม้ AI จะส่งกลับมาเป็นชื่ออย่าง `feat/21-bug:-active-alert` ระบบก็จะแก้ไขเป็น `feat/21-bug-active-alert`

4. **เพิ่ม guard ใน `_normalize_branch_suggestions`** (แก้ Root Cause 2):
   - ตรวจสอบ `[PROMPT EXPORTED]` และ `Paste the AI response` ก่อน sanitize เพื่อ reject placeholder ทันที
   - ตรวจสอบ max length `> 80` หลัง sanitize เพื่อป้องกัน string ขยะที่ยาวมาก

## การทดสอบ (Verification)
- ไฟล์ `tests/test_branch_name_sanitization.py` มีทั้งหมด 5 test cases ครอบคลุม:
  - `_sanitize_branch_name` กับตัวอักษรพิเศษหลายรูปแบบ
  - `_build_default_branch_name` กับ title ที่มี `:`
  - `_normalize_branch_suggestions` กับ colon suggestion
  - `_normalize_branch_suggestions` กับ PromptExportModel placeholder
  - `_normalize_branch_suggestions` กับ branch name ที่ยาวเกิน
- รัน `python3 -m pytest tests/test_branch_name_sanitization.py` → **5 passed**
- รัน regression tests ครบ → **16 passed, 1 skipped**
