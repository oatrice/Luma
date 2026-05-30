# แผนการพัฒนา: เพิ่มตัวเลือกสลับ Endpoint (Radar / Global) ใน Telegram Bot

การพัฒนานี้มีจุดประสงค์เพื่อให้ผู้ใช้สามารถเลือกเปรียบเทียบข้อมูลระหว่าง `precip-global` (ใช้ภาพดาวเทียม+เรดาร์ทั่วโลก) และ `precip` (ใช้เรดาร์ภาคพื้นดินเฉพาะพื้นที่) ได้โดยตรงผ่านปุ่มบนข้อความแชทบอท

## User Review Required
- **[IMPORTANT]** การสลับไปใช้ `Radar` อาจทำให้บางพื้นที่ (เช่นกลางทะเล) เกิด Error (ได้ผลลัพธ์ว่าไม่มีฝน หรือข้อมูลดิบไม่มีค่า) ระบบจะป้องกันเบื้องต้นด้วยการดักจับ HTTP Error และคืนค่าว่า "ไม่มีฝน" เหมือนที่ทำอยู่เพื่อไม่ให้บอทพัง
- การสลับข้อมูลจะใช้วิธี **Edit Message** (แก้ไขข้อความเดิม) แทนการส่งข้อความใหม่ เพื่อไม่ให้รกหน้าต่างแชท

## Proposed Changes

### 1. `backend/app/services/rainbow.py`
เพิ่มพารามิเตอร์เพื่อรองรับการเลือก Endpoint แบบไดนามิก
- **[MODIFY]** `predict_rain_by_location(self, lat: float, lng: float, endpoint_type: str = "global") -> dict`
  - หาก `endpoint_type == "radar"` ให้ใช้ API `.../nowcast/v1/precip/{lng}/{lat}`
  - หาก `endpoint_type == "global"` ให้ใช้ API `.../nowcast/v1/precip-global/{lng}/{lat}`
  - เพิ่มค่า `endpoint` คืนกลับไปใน Dictionary ผลลัพธ์ เพื่อให้ฝั่ง UI รู้ว่าได้ข้อมูลจากแหล่งใด

### 2. `backend/app/services/telegram.py`
- **[MODIFY]** เพิ่มฟังก์ชันใหม่ `edit_telegram_message(chat_id: int, message_id: int, text: str, reply_markup: Optional[dict] = None) -> bool` สำหรับใช้แก้ไขข้อความเดิมแทนการพิมพ์ข้อความพยากรณ์ใหม่ซ้ำๆ

### 3. `backend/app/routers/webhook.py`
ปรับปรุงลอจิกของการรับ Location และการตอบกลับปุ่ม (Callback)
- **[MODIFY]** `process_telegram_location(chat_id, lat, lng, endpoint_type="global", message_id_to_edit=None)`
  - แก้ไขข้อความตอบกลับให้มีแท็กบอกแหล่งที่มา เช่น `🌍 แหล่งข้อมูล: Rainbow (Global)` หรือ `📡 แหล่งข้อมูล: Rainbow (Local Radar)`
  - เพิ่มปุ่ม Inline Keyboard แถวใหม่ สำหรับสลับโหมด: 
    - `[{"text": "🔄 สลับไปใช้ Local Radar", "callback_data": f"switch_radar_{lat}_{lng}"}]`
    - หรือ `[{"text": "🔄 สลับไปใช้ Global", "callback_data": f"switch_global_{lat}_{lng}"}]`
  - หากมี `message_id_to_edit` จะใช้ฟังก์ชัน `edit_telegram_message` แทน `send_telegram_message`
- **[MODIFY]** `handle_callback_query(callback_query: dict)`
  - ดักจับ Prefix `switch_radar_` และ `switch_global_`
  - ดึงค่าละติจูด/ลองจิจูด และสั่งรัน `process_telegram_location` แบบ Background ใหม่โดยส่งค่า `message_id_to_edit` ไปด้วย

### 4. `backend/tests/test_services.py` และ `test_webhook.py`
- **[MODIFY]** เพิ่มเคสทดสอบ (Unit Tests) ให้ครอบคลุมการเรียกใช้ `endpoint_type="radar"` และการสลับโหมด

---
## Verification Plan
### Automated Tests
- รัน `pytest` ตรวจสอบความถูกต้องของการแปลง API URL ใน `RainbowService` และการดักจับปุ่ม `switch_*`

### Manual Verification
- นำ Bot ขึ้นมารันด้วย `uvicorn` และเปิด `localtunnel` เพื่อเทสแบบ End-to-End
- ส่ง Location เข้า Telegram Bot 
- กดปุ่ม `🔄 สลับไปใช้ Local Radar` และดูว่าข้อความถูกแก้ไขเนื้อหาเปลี่ยนไปใช้แหล่งข้อมูล Radar โดยบอทไม่พ่น Error ออกมา
