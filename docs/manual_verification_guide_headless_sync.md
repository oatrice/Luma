# คู่มือการทดสอบด้วยตนเอง (Manual Verification Guide) สำหรับการเปลี่ยนแปลงใน `action_sync_ai_brain` เพื่อรองรับโหมด Headless

### วัตถุประสงค์
เพื่อยืนยันว่าระบบสามารถทำงานในโหมด Headless ได้โดยไม่หยุดรอ Input จากผู้ใช้ (Non-interactive) และยังคงทำงานในโหมดปกติ (Interactive) ได้อย่างถูกต้องตามเดิม โดยเฉพาะการเลือก Session อัตโนมัติและการปิดกั้นข้อความแสดงผลที่ไม่จำเป็น

---

### เตรียมความพร้อมก่อนเริ่ม
1. ตรวจสอบว่ามี Antigravity session อยู่ในเครื่อง (หรือจำลองไฟล์ session ไว้ในโฟลเดอร์ที่เกี่ยวข้อง)
2. ตรวจสอบว่ามี issue ที่ active อยู่ในสถานะปัจจุบัน (`.luma_state.json`) โดยรัน `python main.py` เพื่อเลือก issue ก่อน (ถ้ายังไม่มี)

---

### กรณีการทดสอบที่ 1: โหมดปกติ (Interactive Mode) - ตรวจสอบ Regression
**ขั้นตอน:**
1. รัน Luma CLI ในโหมดปกติ:
   ```bash
   python main.py
   ```
2. เลือกโปรเจกต์และ Issue ที่ต้องการ
3. เข้าไปที่เมนู **Admin/Settings** (หรือเมนูที่เรียกใช้ Sync AI Brain)
4. เลือกคำสั่ง **Sync AI Brain**

**ผลที่คาดหวัง:**
- ระบบต้องแสดงรายการ Antigravity session ล่าสุด
- ระบบต้องหยุดรอและแสดง Prompt: `✅ Use this Antigravity session? (Y/n/s to skip):`
- เมื่อตอบ `Y` ระบบต้องดำเนินการ Sync และแสดง Log การทำงานบนหน้าจอปกติ

---

### กรณีการทดสอบที่ 2: โหมด Headless (Auto-select & Silencing)
ทดสอบการทำงานผ่าน Python script เพื่อจำลองการเรียกแบบ Headless

**ขั้นตอน:**
1. สร้างไฟล์ทดสอบ `verify_headless_sync.py`:
   ```python
   import sys
   from luma_core.state import LumaState
   from luma_core.actions.admin_actions import action_sync_ai_brain

   # โหลด state ปัจจุบัน (ต้องมั่นใจว่ามี active_issue และ project config)
   state = LumaState.load()
   project = state.context.get("project_config", {"name": "Test Project"})

   print("--- Running Headless Sync ---")
   # เรียกใช้ action พร้อม headless=True
   success = action_sync_ai_brain(state, project, headless=True)
   print(f"--- Finished Headless Sync: Result={success} ---")
   ```
2. รันคำสั่ง: `python verify_headless_sync.py`

**ผลที่คาดหวัง:**
- **ไม่มีการหยุดรอ** การกด Enter หรือการตอบ Y/N ใดๆ
- **ไม่มีการพิมพ์ข้อความ** "🧠 Syncing...", "📂 Latest Session...", หรือ "📄 Preview..." ออกมาที่หน้าจอ (stdout)
- ฟังก์ชันต้องคืนค่า `True` (หากมี session ให้ sync) และดำเนินการ sync เบื้องหลังโดยอัตโนมัติ

---

### กรณีการทดสอบที่ 3: โหมด Headless เมื่อไม่มี Active Issue
**ขั้นตอน:**
1. แก้ไขไฟล์ `.luma_state.json` ชั่วคราว โดยตั้งค่า `"active_issue": null`
2. รันคำสั่ง: `python verify_headless_sync.py` อีกครั้ง

**ผลที่คาดหวัง:**
- ระบบต้องคืนค่า `False` ทันที
- **ต้องไม่มี** ข้อความ `❌ No active issue selected...` พิมพ์ออกมาที่หน้าจอ (เพราะถูกครอบด้วย `if not headless`)

---

### การตรวจสอบความถูกต้อง (Verification Checkpoints)
- [ ] **No Blocking:** ต้องไม่มีการเรียก `safe_input()` ในโหมด Headless
- [ ] **Clean Stdout:** ข้อความการ Preview และ Confirmation ต้องถูกซ่อนในโหมด Headless เพื่อไม่ให้รบกวนการ parse JSON ของระบบภายนอก
- [ ] **Auto-confirm:** ในโหมด Headless ตัวแปร `confirm` ต้องถูกตั้งเป็น `"y"` โดยอัตโนมัติเพื่อให้งานดำเนินต่อไปได้
