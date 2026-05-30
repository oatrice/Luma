# Task Checklist for Batch A

- [x] **สร้าง GitLab Issue**
  - [x] สร้าง Issue ใหม่สำหรับการดึงข้อมูลจาก External API อื่น (Open-Meteo/TMD) และ backlink ไปที่ #13
- [x] **Issue #13: Extended Meteorological Data (TDD)**
  - [x] เขียน Failing Test สำหรับ `RainbowService.predict_rain_by_location` เพื่อคำนวณ `intensity` และ `duration`
  - [x] เขียน Production Code เพื่อให้ Test ผ่าน
  - [x] Refactor โค้ด
  - [x] อัปเดตการสร้างข้อความแจ้งเตือนใน `scheduler_tasks.py` ให้แสดงผล `intensity` และ `duration`
  - [x] อัปเดตการสร้างข้อความแจ้งเตือนใน `webhook.py`
- [/] **Issue #15: CI/CD Auto-deploy**
  - [x] เพิ่ม `deploy` stage ใน `.gitlab-ci.yml` โดยใช้ตัวแปร `$GCP_PROJECT_ID` และ `$GCP_SA_KEY`
  - [x] ตั้งค่าการอัปเดต Telegram Webhook อัตโนมัติหลัง Deploy
  - [x] จัดทำ `docs/development_guide.md` อธิบาย "Two Bots Strategy" และการใช้ `localtunnel`
- [x] **Verification & Cleanup**
  - [x] ตรวจสอบว่า `pytest` ผ่านทั้งหมด
  - [x] สรุปผลลงใน `walkthrough.md`
  - [x] เรียกใช้ `notify_task_complete`
