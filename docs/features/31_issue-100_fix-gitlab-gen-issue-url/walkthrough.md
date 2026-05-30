# Walkthrough: GitLab URL & Git Auth Fix

## สิ่งที่ดำเนินการเสร็จสิ้น (Changes Made)

1. **URL Generation Fix**:
   - ปัญหาคือ Luma จะ Hardcode URL ว่าต้องไปที่ `github.com` เสมอหากไม่ได้มี URL แบบ Explicit มาให้ ซึ่งทำให้การปิด Issue อัตโนมัติ (Closes #100) ของ GitLab ทำงานไม่ได้ในโปรเจกต์ภายนอก
   - ดำเนินการแก้ Prompt instruction สำหรับ Publisher agent โดยเช็ค `platform == "gitlab"` หากเป็นจริงจะใช้ Base URL ของ GitLab แทน

2. **Git Push Authentication Override**:
   - แก้ปัญหาที่น่าปวดหัวของระบบ `git credential-osxkeychain` ที่ชอบจำ Token เก่าเอาไว้จนทำให้ Luma สั่ง `git push` ไม่ได้
   - เพิ่มกระบวนการให้ Luma อ่าน Token ใหม่เสมอจาก `glab auth status -t` หรือ `gh auth token` 
   - ฉีด Token ใหม่นี้เข้าไปในคำสั่ง Git ด้วยรูปแบบ `-c credential.helper=` (เพื่อลบ Helper ปัจจุบัน) และ `-c credential.helper='!f() { echo "username=oauth2"; echo "password=$TOKEN"; }; f'`
   - ทำความสะอาด Environment Variables ก่อนเรียก CLI ย่อย เพื่อป้องกัน Token ชนกัน

3. **URL Test Script**:
   - สร้างไฟล์ `test_url_gen.py` ขึ้นมาเพื่อเช็ค Logic การต่อ String URL โดยแยกเคส Luma, Zenith และ Cerebro ว่าแสดงผลตรงกับความต้องการหรือไม่

## สิ่งที่ทำการทดสอบ (What was tested)
- ✅ `test_url_gen.py` รันผ่านครบ 5 Test Cases
- ✅ การสั่ง Push code แบบ Automated (Headless) ไม่เกิด Authentication Failed อีกต่อไป
- ✅ PR Description บนเว็บถูกลิงก์มายัง Issue อย่างถูกต้อง

## Validation Results
ระบบสามารถทำงานบน GitLab และ GitHub พร้อมกับ Bypass ระบบ Authentication เดิมที่เกะกะการทำงานเบื้องหลังของ AI ได้อย่างสมบูรณ์แบบ
