### Manual Verification Guide

**การทดสอบ Issue 106 & 107: VS Code CLI Crash Fix**
1. จำลองสถานการณ์ที่ระบบหาคำสั่ง `code` (VS Code CLI) ไม่เจอ เช่น ชั่วคราวเปลี่ยนชื่อไฟล์ executable หรือลบออกจาก PATH
2. รัน Luma Workflow (ผ่าน `python main.py`) และรันคำสั่งให้มีการสร้างหรืออัปเดต `CHANGELOG.md` / `README.md`
3. ถึงขั้นตอนที่ Luma พยายามเปิด Preview Diff ให้สังเกตผลลัพธ์ว่า **ระบบจะไม่แครช** (ไม่ติด `FileNotFoundError`)
4. Luma จะแสดงคำเตือนว่า `⚠️ VS Code CLI ('code') not found, skipping diff preview` และรันขั้นตอนต่อไปตามปกติ

**การทดสอบ Issue 111: Force Export Prompt & Fix MR URL Bug**
1. **ทดสอบ Force Export Prompt Only:**
   - รัน Luma Workflow ไปจนถึงขั้นตอนยืนยันการสร้าง PR/MR (`Create PRs?`)
   - ระบบจะมีตัวเลือกใหม่โผล่ขึ้นมา ให้พิมพ์เลือก `f` (Force Export Prompt Only)
   - **ผลลัพธ์ที่คาดหวัง**: ระบบจะทำการบันทึกไฟล์ Draft Prompt (`draft_pr_prompt.md`) จากนั้นจะขึ้นข้อความ `✅ Force Export Complete. Skipping PR creation.` และสิ้นสุดการทำงานโดยไม่มีการยิง API ไปสร้าง MR บน GitLab/GitHub จริงๆ

2. **ทดสอบแก้บั๊ก MR URL ขึ้น None:**
   - ใช้ Luma Workflow เลือก Branch / Issue ที่มีการเปิด Merge Request บน GitLab เอาไว้อยู่แล้ว
   - ดำเนินการจนถึงหน้าจอสร้าง PR/MR และเลือกให้ระบบทำการสร้าง (พิมพ์ `y` หรือ `a`)
   - **ผลลัพธ์ที่คาดหวัง**: ระบบจะตรวจพบ MR เดิม และข้ามการทำงาน โดยจะต้องแสดง URL ของ MR ที่มีอยู่ได้อย่างถูกต้อง (เช่น `⏩ Skipping ... (PR/MR already exists: https://...)`) แทนที่จะแสดงเป็นคำว่า `None` เหมือนก่อนหน้านี้
