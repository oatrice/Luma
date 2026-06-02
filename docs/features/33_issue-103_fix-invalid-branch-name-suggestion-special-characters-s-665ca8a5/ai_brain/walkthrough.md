# สรุปการแก้ไข Issue 103 (Fix invalid branch name suggestion)

## ปัญหาที่พบ
เมื่อผู้ใช้เลือก `Select Issue` ถ้าชื่อของ issue นั้นๆ มีตัวอักษรพิเศษที่ไม่ได้รับอนุญาตให้เป็นชื่อ branch ของ git (เช่น `:`, `?`, `*`, `\`, หรือช่องว่างที่เกิดจากการต่อคำ) ระบบแนะนำชื่อ branch ก็จะนำตัวอักษรนั้นไปใช้ ทำให้เมื่อ git branch ถูกสร้างขึ้นจะเกิดข้อผิดพลาด 

## สิ่งที่แก้ไข
1. เพิ่มฟังก์ชัน `_sanitize_branch_name` ใน `luma_core/actions/utils.py`:
   - แปลงตัวอักษรพิเศษทั้งหมดที่ไม่ใช่ `A-Z`, `a-z`, `0-9`, `_`, `-`, `/` ให้กลายเป็นขีดกลาง `-`
   - ทำการยุบเครื่องหมายขีดกลางหลายๆ อันให้เหลือแค่อันเดียว
   - ตัดขีดกลางและ slashes ที่หัว/ท้ายออก

2. อัปเดต `_build_default_branch_name`:
   - ให้ประมวลผล slug ผ่านฟังก์ชัน `_sanitize_branch_name` ก่อนสร้างเป็น `feat/{issue}-slug`

3. อัปเดต `_normalize_branch_suggestions`:
   - นำชื่อที่ AI แนะนำมาผ่านการแปลงผ่าน `_sanitize_branch_name` ก่อน
   - ทำให้แม้ AI จะส่งกลับมาเป็นชื่ออย่าง `feat/21-bug:-active-alert` ระบบก็จะแก้ไขเป็น `feat/21-bug-active-alert` แทนที่จะถูกระบบปัดทิ้งทั้งหมด

## การทดสอบ (Verification)
- เพิ่มไฟล์ `tests/test_branch_name_sanitization.py` 
- ทดสอบครอบคลุมทั้งรูปแบบที่มีเครื่องหมายวรรคตอนต่างๆ 
- รัน `python3 -m pytest tests/test_branch_name_sanitization.py` พบว่าผ่าน 100% 
- รัน `python3 -m pytest tests/` ภาพรวมระบบก็ยังทำงานได้ตามปกติ ไม่พบข้อผิดพลาด
