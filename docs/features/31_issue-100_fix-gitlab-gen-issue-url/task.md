# Tasks: Issue 100 - Fix GitLab URL Generation

- [x] ตรวจสอบโครงสร้างของ Issue URL ใน `luma_core/agents/publisher.py`
- [x] แก้ไข prompt template ให้รองรับทั้ง GitHub และ GitLab แบบ Dynamic
- [x] สร้างสคริปต์ `test_url_gen.py` เพื่อจำลองการทำงาน
- [x] ตรวจสอบสาเหตุที่ `git push` เฟลจาก `osxkeychain`
- [x] สร้างกระบวนการทำ Inline Credential Helper ใน `publisher.py`
- [x] เพิ่มความสามารถในการ Scrub Token ของ Environment Variables ใน `cli_wrapper.py` 
- [x] รันเทสต์และยืนยันว่า `git push` ทำงานได้จริง
- [x] เพิ่ม error handling ใน `github_client.py` 
