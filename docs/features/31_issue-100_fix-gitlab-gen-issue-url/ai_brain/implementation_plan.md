# Update RainbowService to use official Rainbow Weather API

จากที่คุณค้นคว้าเอกสาร API ของ Rainbow Weather มาให้ พบว่าโครงสร้างการเรียก (Endpoint) และโครงสร้างข้อมูลที่ส่งกลับมา (Response) แตกต่างจากที่เราเคยมโน (Mock) ไว้ตอนเริ่มต้นโปรเจกต์อย่างสิ้นเชิงครับ นี่คือสาเหตุหลักที่ทำให้ API คืนค่า 404 Not Found และตกลงไปใน `except` block 

## Proposed Changes

### `backend/app/services/rainbow.py`
เราจะต้องแก้ไข 3 จุดหลักๆ ในคลาส `RainbowService`:

1. **เปลี่ยน Endpoint URL:**
   - **เก่า:** `https://api.rainbow.ai/v1/nowcast?lat=X&lon=Y&duration=240`
   - **ใหม่:** `https://api.rainbow.ai/nowcast/v1/precip-global/{longitude}/{latitude}`
2. **ปรับปรุงการดึงข้อมูล (Parsing):**
   - ดึงข้อมูลจากคีย์ `forecast` ซึ่งเป็น Array ของ `{"precipRate": X, "timestampBegin": Y, "timestampEnd": Z}` 
   - แปลงค่า Unix Timestamp ให้กลับมาเป็นรูปแบบ ISO 8601 (`"YYYY-MM-DDTHH:MM:SSZ"`) ตามที่ระบบของเรา (เช่น `scheduler.py` และ UI) คาดหวัง
   - ทำการจับคู่ตัวแปร `precipRate` แปลงให้เป็นชื่อตัวแปร `rain` ตามระบบเดิม
3. **การคำนวณ Intensity & Duration:**
   - ดึงข้อมูล `summary.intensity` จาก API ของ Rainbow มาใช้โดยตรง (ถ้ามี) หรือคำนวณใหม่จาก `precipRate` 
   - คำนวณ `duration_minutes` จาก `timestampBegin` และ `timestampEnd` ของช่วงเวลาที่ฝนตก

### `backend/tests/test_rainbow.py` และ Test ที่เกี่ยวข้อง
- อัปเดต Mock Response ในชุดทดสอบให้ตรงกับโครงสร้างใหม่ (มี `forecast`, `latitude`, `longitude`, `summary`) 
- ตรวจสอบให้แน่ใจว่าระบบจะรับมือกับโครงสร้างใหม่ได้อย่างถูกต้อง และไม่ทำลายกระบวนการแจ้งเตือนของ `scheduler`

## Open Questions

> [!WARNING]
> **เรื่อง Authentication Header:** ในเอกสารที่คุณแปะมาไม่ได้ระบุว่า Rainbow API ต้องการ API Key ในรูปแบบใด ปัจจุบันเราใช้ `Ocp-Apim-Subscription-Key` อยู่ หากคุณมีข้อมูลในเอกสารว่าเขาให้ส่ง Key ผ่าน Header ชื่ออะไร (เช่น `Authorization: Bearer <token>` หรือ `x-api-key`) รบกวนแจ้งให้ผมทราบด้วยนะครับ จะได้อัปเดตไปพร้อมกันทีเดียว

## Verification Plan
1. **Automated Tests:** แก้ไข Test ของ RainbowService ให้จำลองโครงสร้างใหม่ และรันด้วยคำสั่ง `pytest` จนกว่าจะผ่าน (Red -> Green -> Refactor)
2. **Manual Verification:** หลังแก้โค้ดเสร็จ จะให้คุณใช้คำสั่ง `curl` จำลองยิง หรือ Deploy ขึ้น Cloud Run เพื่อทดสอบอีกครั้ง
