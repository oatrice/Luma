# Walkthrough: Issues 108, 109, 110

การทำงานในรอบนี้แบ่งออกเป็น 3 ส่วนหลัก (Luma 2 ส่วน, Akasa 1 ส่วน) ดังนี้:

## 1. การแก้บั๊ก Publisher Agent (Issue #109)
**ปัญหา:** คำสั่ง `glab mr create` สร้าง Merge Request ผิด Repository ไปสร้างใน Base Repo (Luma) แทนที่จะเป็น Target Repo
**การแก้ไข:** 
- เข้าไปที่ไฟล์ `luma_core/gitlab_client.py` 
- เพิ่มอาร์กิวเมนต์ `--repo repo_name` ลงในฟังก์ชัน `create_merge_request()` ทำให้ CLI ไปชี้ที่โปรเจกต์ปลายทางได้ถูกต้องเสมอ

## 2. การแก้บั๊ก Worktree Context (Issue #110)
**ปัญหา:** เมื่อรัน Luma จาก Base Repo แล้วเลือกจัดการโปรเจกต์ที่เป็น Worktree ตัวโค้ดจะไปดึง `git_toplevel` ของ Base Repo มาทับและบังคับทำงานที่นั่นแทน
**การแก้ไข:**
- เข้าไปที่ไฟล์ `luma_core/tools.py` ฟังก์ชัน `resolve_project_target_dir()`
- เพิ่มการตรวจสอบเงื่อนไข หาก `work_dir` ปัจจุบันไม่ใช่ Worktree (เป็น Base Repo) **และ** `project_path` ที่ผู้ใช้เลือกเป็น Worktree ระบบจะคืนค่าเป็น `project_path` ตรงๆ โดยไม่ต้องคำนวณ Base ของมันใหม่ ทำให้ทำงานตรงกับ Worktree ที่ผู้ใช้เลือกได้อย่างแม่นยำ

## 3. การประเมินและยกระดับความปลอดภัย Akasa Backend (Issue #108)
**ปัญหา:** ผู้ใช้ต้องการให้เช็คและประเมินระบบรักษาความปลอดภัยของ Akasa Backend (รวมถึงโปรเจกต์อื่นด้วย) ว่ามี Secret หลุดไหม และวางแผนการปรับปรุงระบบ Rate Limiting, Secret Management, Payload Validation

**ผลการทำงาน:**
1. **Security & Secret Scanning:** ทำการรันค้นหา (Grep) ในโค้ดทั้งหมดของทั้ง 3 โปรเจกต์ (`Akasa`, `Luma`, `FonMaYang`) 
   - **ผลลัพธ์:** ปลอดภัย ไม่พบ Secret ของจริง Hardcode ไว้ใน Source Code เจอเพียง Default สำหรับทดสอบ, ไฟล์ `.env.example` และเอกสารประกอบเท่านั้น
2. **การอิมพลีเมนต์ (ถูกยกเลิก):** เดิมทีมีการแก้ไขโค้ดเพิ่มระบบป้องกัน (Rate limiting ด้วย Redis `expire/incr`, เช็ค API Key แบบปลอดภัยด้วย `secrets.compare_digest`, และเพิ่ม `max_length` ใน Pydantic Models) แต่หลังจากยืนยันจุดประสงค์ว่าเน้นทำแค่การ "สแกนหาช่องโหว่และประเมิน" ไปก่อน โค้ดส่วนนี้จึงได้ถูก **Discard (ยกเลิกการเปลี่ยนแปลง)** กลับสู่สภาพเดิม เพื่อทำในเฟสถัดไป

## ผลการทดสอบและ Verification
- **Luma:** ได้ Commit การเปลี่ยนแปลงไฟล์ `gitlab_client.py` และ `tools.py` เข้าไปยัง Luma Repository บน branch ปัจจุบันเรียบร้อยแล้ว
- **Akasa:** ไม่ได้บันทึกการแก้ไขใดๆ กลับสภาพเดิมและยืนยันผลการสแกนความปลอดภัยแล้ว
