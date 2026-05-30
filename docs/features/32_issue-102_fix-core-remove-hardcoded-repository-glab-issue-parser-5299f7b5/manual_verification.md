# การทดสอบแบบ Manual

1. สลับไปทำงานในโปรเจกต์อื่นที่ไม่ใช่ Luma (เช่น FonMaYang หรือโปรเจกต์ GitLab อื่น)
2. รันคำสั่งเปิดระบบ Luma เพื่อทำการเลือก Issue (ทั้งแบบ Interactive Menu หรือ Headless ก็ได้)
3. เข้าไปตรวจสอบในไฟล์ `.luma_state.json` (ของโปรเจกต์นั้น) ภายใต้โหนด `active_issues`
4. ยืนยันว่าค่า `repository` ภายใน Issue ไม่ได้เป็น `oatricedev/Luma` แต่เป็นชื่อ repository ของโปรเจกต์ปัจจุบัน
5. ยืนยันว่าเมื่อมีการสร้าง PR ระบบสร้างคำสั่งอ้างอิง (เช่น `Closes https://gitlab.com/<repo>/-/issues/<id>`) ได้อย่างถูกต้องตาม URL ของโปรเจกต์นั้น
/Users/oatrice/Software-projects/Luma-worktrees/luma1/docs/features/32_issue-102_fix-core-remove-hardcoded-repository-glab-issue-parser-5299f7b5/manual_verification.md