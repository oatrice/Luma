# Implementation Plan: Fix GitLab URL Generation & Git Push Authentication

## Goal
แก้ไขปัญหาที่ Luma สร้าง URL ของ issue ใน PR descriptions ผิดพลาดสำหรับ GitLab repositories อื่นที่ไม่ใช่โปรเจกต์ Luma เอง และแก้ไขปัญหา `git push` พังจาก Keychain บน macOS ด้วยการทำ inline credential helper

## Proposed Changes

### Core Workflow (URL Generation)
#### [MODIFY] luma_core/agents/publisher.py
- แก้ไข string interpolation ในส่วนของคำสั่ง LLM Prompt:
  จากเดิมที่ hardcode `https://github.com/` ให้เช็ค `platform == 'gitlab'` เพื่อสลับไปใช้ `https://gitlab.com/` อัตโนมัติ

### Authentication & VCS CLI
#### [MODIFY] luma_core/agents/publisher.py
- ดึง Token โดยตรงจากการรัน `gh auth token` หรือ `glab auth status -t`
- ล้าง credential helper ของระบบ (เช่น `osxkeychain`) ออกจากคำสั่ง `git push` และใส่ inline credential helper ลงไปแทน เพื่อบังคับให้ Git ใช้ Token ที่เพิ่งดึงมาได้ใหม่เสมอ

#### [MODIFY] luma_core/cli_wrapper.py
- เพิ่ม logic ลบ Environment Variables ประเภท Token (`GITHUB_TOKEN`, `GITLAB_TOKEN`, `GH_TOKEN`, `GL_TOKEN`) ออกชั่วคราวเมื่อต้องการรันคำสั่งกลุ่ม `auth` เพื่อบังคับให้ `gh` และ `glab` ดึง Token จากระบบ Config หรือ Keyring ของมันเอง แทนที่จะถูก Override ด้วยค่าเก่าใน env

#### [MODIFY] luma_core/github_client.py & luma_core/github_project.py
- เพิ่ม `try-except ValueError` ในจังหวะที่ `.split("/")` สำหรับชื่อ repo ป้องกันระบบ Crash เมื่อ string format ไม่ถูกต้อง

### Testing
#### [NEW] test_url_gen.py
- สคริปต์แบบ Standalone เพื่อจำลอง State แบบต่างๆ และทดสอบว่า URL ถูกสร้างออกมาถูกต้องทั้งในเคสที่มี Explicit URL และเคสที่ต้อง Fallback String Building

## Verification Plan
1. รัน `test_url_gen.py` เพื่อทดสอบว่า URL ตรงตามที่คาดหวัง
2. สั่งสร้าง PR ผ่าน Luma เพื่อให้ทดสอบ `git push` ว่าสามารถทำงานข้าม `osxkeychain` ได้อย่างสมบูรณ์
3. ดูผลลัพธ์ PR Description ในหน้าเว็บ GitLab ว่า Closes issue #100 ลิงก์ไปถูกหน้า
