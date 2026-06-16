# วางแผนแก้ไขปัญหา Issue 108, 109, และ 110

แผนการทำงานนี้ครอบคลุมการแก้บั๊ก 3 ส่วนหลักจากทั้งโปรเจกต์ Luma และ Akasa Backend

## 1. Issue #110: Worktree Context Bug (โปรเจกต์ Luma)
**ปัญหา:** ปัจจุบันถ้าเราเปิด Luma ขึ้นมาจาก Base Repository แล้วเลือกโปรเจกต์ในเมนูที่เป็น Worktree (เช่น `luma1`) ตัวโค้ดใน `resolve_project_target_dir` จะทำการคำนวณ `git_toplevel` ของ `work_dir` (ซึ่งคือ Base Repo) และบังคับสลับกลับไปใช้ Base Repo แทนที่จะเป็น Worktree ที่ผู้ใช้เลือก
**แนวทางแก้ไข:** 
- เข้าไปแก้ไขไฟล์ `luma_core/tools.py` ฟังก์ชัน `resolve_project_target_dir`
- เพิ่มเงื่อนไขว่า หาก `work_dir` ไม่ใช่ Worktree (เป็น Base) แต่ `project_path` เป็น Worktree ให้ **คืนค่า `project_path` เดิม** แทนที่จะเป็น `git_toplevel` ของ Base Repo
```python
if os.path.realpath(active_common_dir) == os.path.realpath(project_common_dir):
    # ถ้าเปิดจาก Base repo แต่กำลังจะจัดการ Worktree ให้รักษา project_path เดิมไว้
    if not is_git_worktree(work_dir) and is_git_worktree(project_path):
        return project_path
    return git_toplevel
```

## 2. Issue #109: Publisher Agent MR Repo Bug (โปรเจกต์ Luma)
**ปัญหา:** ตอนที่ Publisher Agent รันคำสั่ง `glab mr create` มันไปสร้าง Merge Request ใน Luma repo แทนที่จะเป็น Target repo (`FonMaYang` เป็นต้น) เพราะไม่ได้แนบ parameter `--repo` ไปด้วยใน `args` ของ subprocess
**แนวทางแก้ไข:** 
- เข้าไปแก้ไขไฟล์ `luma_core/gitlab_client.py` ในฟังก์ชัน `create_merge_request()`
- เพิ่ม `--repo` และ `repo_name` เข้าไปในลิสต์ของ `args` คล้ายกับที่ทำในฟังก์ชัน `update_merge_request` หรือ `get_open_merge_request`
```python
args = [
    "mr", "create",
    "--repo", repo_name,
    "--title", title,
    ...
]
```

## 3. Issue #108: Evaluate and enhance Akasa backend security (โปรเจกต์ Akasa)
**ปัญหา:** ฝั่ง Akasa Backend ใน `FonMaYang/backend` (หรือ `Akasa` repo) ต้องการการประเมินและยกระดับความปลอดภัย (Rate limiting, Secret management, Payload validation)
**แนวทางการประเมินและยกระดับ:**
1. **Secret Management:** ใน `app/routers/notifications.py` ฟังก์ชัน `verify_api_key` มีการตรวจสอบโดยใช้ `if x_akasa_api_key == settings.AKASA_API_KEY:` ซึ่งสามารถเกิด Timing Attack ได้ จะเปลี่ยนไปใช้ `secrets.compare_digest` ในการเช็ค string
2. **Payload Validation:** Pydantic Models ใน `app/models/notification.py` เช่น `TaskNotificationRequest` ปัจจุบันรับค่า String ใดๆ โดยไม่จำกัดความยาว จะมีการเพิ่ม `Field(..., max_length=2000)` ให้ฟิลด์ `message` หรือ `task` เพื่อป้องกันปัญหา Memory Exhaustion หรือ Payload ขนาดใหญ่เกินไป (DoS)
3. **Rate Limiting:** *(ถ้าจำเป็นต้องทำใน Issue นี้)* สามารถเพิ่ม Dependency ที่ประยุกต์ใช้ Redis หรือใช้ `slowapi` ใน FastAPI เพื่อจำกัดจำนวน Request เข้ามายัง Route `/task-complete` ต่อ IP หรือ ต่อ API Key ได้

## User Review Required
> [!IMPORTANT]  
> ในส่วนของ **Issue #108 (Akasa Security)** 
> - การเพิ่ม **Rate Limiter** ต้องพึ่งพา Dependency เช่น `slowapi` หรือสร้าง Custom Dependency ด้วย Redis ที่มีอยู่แล้ว ต้องการให้ผมเขียน Rate Limiting Logic ด้วย Redis เองแบบง่ายๆ (Token bucket / Fixed window) หรือว่าสนใจให้ใช้ไลบรารี `slowapi` แยกต่างหากครับ? 
> - ปัจจุบัน Akasa Backend มี Redis Pool อยู่แล้ว การทำ Fixed Window Rate Limiting ง่ายๆ ด้วย Redis อาจจะลดจำนวน Dependencies ของโปรเจกต์ลงได้

หากแผนด้านบนครบถ้วนสมบูรณ์แล้ว รบกวน **อนุมัติ (Approve)** เพื่อให้ผมเริ่มแก้โค้ดได้เลยครับ หรือสามารถตอบคำถามข้างต้นเพื่อปรับแผนเพิ่มเติมได้ครับ
