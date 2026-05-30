# Manual Verification Plan: GitLab URL Generation & Platform Detection

เอกสารนี้ใช้สำหรับตรวจสอบการทำงานของโค้ดที่ได้รับการแก้ไขใน branch `feat/100-fix-gitlab-url-generation-issu` (อ้างอิงถึงระบบรองรับ GitLab)

## 1. จุดประสงค์ของการตรวจสอบ
- เพื่อให้มั่นใจว่าระบบสามารถวิเคราะห์และแยกแยะได้ว่าโปรเจกต์ปัจจุบันอยู่บนแพลตฟอร์ม GitHub หรือ GitLab โดยอัตโนมัติ (ผ่าน `git config --get remote.origin.url`)
- เพื่อยืนยันว่าการสร้าง Issue URL และ PR/MR Description ใน `analyst.py`, `spec_agent.py` และ `publisher.py` ชี้ไปที่ `https://gitlab.com/...` อย่างถูกต้อง หากรันอยู่ในโปรเจกต์ GitLab
- เพื่อทดสอบ Error Handling ใน `github_client.py` เมื่อได้รับรูปแบบชื่อ Repository ที่ไม่ใช่มาตรฐาน (เช่น มี Slash มากกว่า 1 ตัว) ว่าจะไม่แครช (Crash) แต่ข้ามไปอย่างปลอดภัย

## 2. ขั้นตอนการทดสอบ (Manual Steps)

### Test Case 1: การจำลองสภาพแวดล้อม GitLab และ URL Generation
**ขั้นตอน:**
1. เข้าไปที่โฟลเดอร์โปรเจกต์ที่ต้องการทดสอบ
2. ตั้งค่า git remote ชั่วคราวให้เป็น GitLab:
   ```bash
   git config remote.origin.url git@gitlab.com:owner/repo.git
   ```
3. สั่งรัน Agent ที่เกี่ยวข้อง (เช่น Analyst หรือ Spec Agent) ผ่าน CLI หรือ Mock State
4. ตรวจสอบผลลัพธ์ของไฟล์ที่สร้างขึ้น (เช่น `analysis.md` หรือ `spec.md`) ว่าลิงก์ Issue ที่สร้างชี้ไปยัง GitLab หรือไม่ (ควรเป็น `https://gitlab.com/owner/repo/issues/...`)
5. ตรวจสอบใน Publisher Agent หากมีการสร้าง PR Description จะต้องมีบรรทัด `Closes https://gitlab.com/...` ปรากฏอยู่
6. เมื่อทดสอบเสร็จ ให้เปลี่ยน remote คืน (หากจำเป็น)

### Test Case 2: การจำลองสภาพแวดล้อม GitHub
**ขั้นตอน:**
1. ตั้งค่า git remote ให้เป็น GitHub:
   ```bash
   git config remote.origin.url git@github.com:owner/repo.git
   ```
2. รัน Agent แบบเดียวกับ Test Case 1
3. ยืนยันว่า Issue URL ในเอกสารชี้ไปที่ `https://github.com/...` ได้ถูกต้องเหมือนเดิม (Regression Test)

### Test Case 3: การตรวจสอบ Error Handling ของ Repository Format ใน `github_client.py`
**ขั้นตอน:**
1. รันฟังก์ชัน `create_pull_request`, `get_open_pr`, หรือ `update_pull_request` ใน `github_client.py` แบบแมนนวล (ผ่าน Python REPL หรือ Script ทดสอบ)
2. โยนค่า `repo_name` เป็น `group/subgroup/repo` (ซึ่งผิดรูปแบบ `owner/repo`)
3. **สิ่งที่ควรจะเกิดขึ้น:** ระบบจะพิมพ์ข้อความ `❌ Invalid repo format. Use 'owner/repo'.` ออกมาทาง Console และคืนค่า `None` โดยไม่มี Exception `ValueError` ปรากฏจนทำให้โปรแกรมหยุดทำงาน

## 3. Self Code Review Notes
จากการรีวิวโค้ดด้วยตัวเอง มีข้อสังเกตเพิ่มเติมที่ควรทราบ:
- **ข้อดี:** การทำ Auto-detect ผ่าน `git config` ช่วยให้โค้ดยืดหยุ่นและรองรับ GitLab ได้ง่ายขึ้นโดยไม่ต้องแก้ Config Project แบบแมนนวล และ Error handling ช่วยลดโอกาสที่ระบบ Agent จะพังกลางคัน
- **ข้อจำกัด (Edge Case) ที่อาจต้องพิจารณาในอนาคต:**
  - รูปแบบ URL ของ Issue ใน GitLab บางครั้งอาจใช้เป็น `/-/issues/` แทนที่จะเป็น `/issues/` ล้วนๆ ถึงแม้ว่า GitLab ส่วนใหญ่จะมีการ Redirect ให้ แต่ควรทราบไว้
  - สำหรับ `github_client.py` การ `split("/")` หากเป็นโปรเจกต์ GitLab ที่อยู่ใน Sub-group หลายชั้น จะถือว่าผิดรูปแบบและไม่ทำงานต่อ (คืนค่า `None` และข้ามการใช้ GitHub API ไป) ซึ่งเป็นพฤติกรรมที่ยอมรับได้ชั่วคราวเพราะ API ส่วนนี้ตั้งใจเรียก GitHub API อยู่แล้ว แต่หากอนาคตจะรวม API เข้าด้วยกัน อาจต้องพิจารณาใช้ `.rsplit("/", 1)` หรือรองรับ Path เต็มๆ

---
**สถานะการตรวจสอบ:** 
- [ ] Test Case 1: GitLab URL Generation 
- [ ] Test Case 2: GitHub URL Generation
- [ ] Test Case 3: Invalid Repo Format Error Handling
