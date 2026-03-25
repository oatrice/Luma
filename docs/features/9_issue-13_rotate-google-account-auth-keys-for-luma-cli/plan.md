# Implementation Plan: Rotate Google Account Auth Keys for Luma CLI

> **Refers to**: [Specification: Rotate Google Account Auth Keys for Luma CLI](docs/features/9_issue-13_rotate-google-account-auth-keys-for-luma-cli/spec.md)
> **Status**: Draft

## 1. Architecture & Design

เราจะปรับปรุงระบบการเรียกใช้ LLM ให้รองรับการสลับ API Key โดยใช้แนวทาง **Key Manager Pattern** ซึ่งจะคอยจัดการคลัง Key (Key Pool) และสถานะ Cooldown ของแต่ละ Key

### Component View
- **`luma_core/config.py`**: เพิ่ม Logic ในการโหลด `GOOGLE_API_KEYS` (comma-separated) จาก `.env` และรวมเข้ากับ `GOOGLE_API_KEY` เดิมเพื่อความ Backward Compatibility
- **`luma_core/key_manager.py` (New)**: คอมโพเนนต์ใหม่สำหรับจัดการการเลือก Key (Round-robin), บันทึกสถานะการใช้งาน และจัดการ Cooldown เมื่อติด Rate Limit (429)
- **`luma_core/llm.py`**: ปรับปรุง `GeminiClient` ให้เรียกใช้ `KeyManager` แทนการอ่านจาก config โดยตรง และเพิ่ม Retry Logic เมื่อพบ Error 429
- **`luma_core/ui.py`**: เพิ่ม Notification สำหรับแจ้งเตือนผู้ใช้เมื่อมีการสลับ Key

### Data Model Changes
```python
# luma_core/key_manager.py

class KeyStatus:
    key: str
    is_active: bool = True
    cooldown_until: Optional[float] = None
    fail_count: int = 0

class KeyManager:
    keys: List[KeyStatus]
    current_index: int = 0
    
    def get_next_key(self) -> str:
        """Returns the next available key that is not in cooldown."""
        ...

    def mark_rate_limited(self, key: str, retry_after: int = 60):
        """Sets cooldown for a specific key."""
        ...
```

---

## 2. Step-by-Step Implementation

### Step 1: Configuration Support for Multiple Keys
- **Code**: แก้ไข `luma_core/config.py` ให้มองหา `GOOGLE_API_KEYS` ใน `.env` (รูปแบบ: `key1,key2,key3`)
- **Logic**: ถ้ามีทั้ง `GOOGLE_API_KEY` และ `GOOGLE_API_KEYS` ให้รวมเข้าด้วยกันและขจัดตัวซ้ำ
- **Tests**: `tests/test_config.py` ตรวจสอบการโหลดลิสต์ของ Keys

### Step 2: Implement KeyManager Logic
- **Code**: สร้าง `luma_core/key_manager.py` 
- **Features**:
    - รองรับการเลือก Key แบบ Round-robin
    - ระบบ Cooldown (In-memory) เมื่อ Key ติด Error 429
    - ฟังก์ชันตรวจสอบว่ายังมี Key เหลือให้ใช้หรือไม่
- **Tests**: สร้าง `tests/test_key_manager.py` ทดสอบการสลับ Key และการข้าม Key ที่ติด Cooldown

### Step 3: Refactor LLM Client for Rotation
- **Code**: แก้ไข `luma_core/llm.py`
- **Logic**:
    - Inject `KeyManager` เข้าไปใน `GeminiClient` หรือ `LLMService`
    - ครอบการเรียก API ด้วย `try...except` สำหรับ `ResourceExhausted` (429)
    - เมื่อเจอ 429 ให้เรียก `key_manager.mark_rate_limited()` และทำ Retry ด้วย Key ใหม่ทันที (สูงสุดตามจำนวน Key ที่มี)
- **Tests**: `tests/test_llm_rotation.py` (Mocking API 429 response)

### Step 4: UI Feedback & Observability
- **Code**: ปรับปรุง `luma_core/ui.py` หรือเพิ่ม logging ใน `llm.py`
- **UI**: แสดงข้อความหรืองานกราฟิกเล็กน้อยเมื่อมีการ Rotate เช่น `[!] Rate limit hit. Switching to backup API key...`
- **Safety**: ห้าม Print API Key เต็มๆ ออกหน้าจอ (ให้แสดงแค่ 4 ตัวท้าย)

---

## 3. Verification Plan

### Automated Tests
- [ ] **Unit Test (Config)**: ตรวจสอบการ Parse comma-separated keys จาก `.env`
- [ ] **Unit Test (KeyManager)**: ทดสอบ Round-robin และการข้าม Key ที่ติด Cooldown จนกว่าจะหมดเวลา
- [ ] **Integration Test (LLM)**: Mock Gemini API ให้คืนค่า 429 ในครั้งแรก และตรวจสอบว่าระบบใช้ Key ที่สองในการเรียกซ้ำจนสำเร็จ

### Manual Verification
- [ ] ทดลองใส่ API Key ที่ใช้งานไม่ได้ (หรือ Key ปลอม) สลับกับ Key จริงใน `.env`
- [ ] รันคำสั่งที่ใช้ LLM หนักๆ (เช่น `SBE Generation` หรือ `Code Review`) แล้วสังเกตการสลับ Key ผ่าน Log
- [ ] ตรวจสอบว่าระบบยังทำงานได้ปกติหากมีเพียง Key เดียว (Backward Compatibility)
- [ ] ตรวจสอบว่าเมื่อ Key ทั้งหมดติด Limit ระบบแสดงข้อความแจ้งเตือน "All API keys are exhausted" อย่างถูกต้อง

### Security Check
- [ ] ตรวจสอบว่าไม่มีการ Print API Key ลงใน Console หรือ Log ไฟล์
- [ ] ยืนยันว่า `.env` ไม่ถูก Stage เข้า Git หลังจากเพิ่ม Keys ใหม่ๆ