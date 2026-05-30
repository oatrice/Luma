# Issue #102: Fix core remove hardcoded repository in glab issue parser

## อาการของปัญหา (Problem Statement)
เมื่อ Luma พยายามสร้าง PR description สำหรับ repository ปลายทางที่อยู่บน GitLab เช่น `FonMaYang` ระบบสร้าง URL สำหรับอ้างอิง Issue ไปยัง `oatricedev/Luma` ตลอด (เช่น `https://gitlab.com/oatricedev/Luma/-/issues/17`) ทั้งที่ควรจะอ้างอิงไปยัง repository เป้าหมาย

## สาเหตุ (Root Cause)
ฟังก์ชัน `_parse_glab_issue_list` ภายใน `luma_core/github_project.py` มีการใส่ชื่อ repository เป็น `oatricedev/Luma` ไว้แบบ hardcode ทำให้ทุกครั้งที่แปลงผลลัพธ์ของคำสั่ง `glab` CLI ออกมาเป็น `KanbanCard` ข้อมูล repository และ URL จะโดนผูกติดกับโปรเจกต์ Luma ตลอดเวลา

## แนวทางการแก้ไข (Proposed Changes)

### Luma Core (`luma_core/github_project.py`)
- สร้าง helper function ใหม่ชื่อ `_get_current_gitlab_repo()` เพื่อดึงชื่อ repository ออกมาจาก configuration (`PROJECTS`) อย่างไดนามิก โดยอ้างอิงจากไดเรกทอรีที่กำลังทำงานอยู่
- แก้ไขฟังก์ชัน `_parse_glab_issue_list` ให้เรียกใช้ `_get_current_gitlab_repo()` เพื่อกำหนด `repository` และ `url` แทนการใช้สตริง hardcode

## Verification Plan
1. รัน Test หรือพ่นค่า URL จาก state ของโปรเจกต์อื่นที่ไม่ใช่ Luma
2. ยืนยันว่า `luma_state.json` ของโปรเจกต์นั้น (เช่น FonMaYang) สามารถบันทึก repository ที่ถูกต้องลงใน `active_issues` ได้
