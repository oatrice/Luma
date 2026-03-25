# Specification: Rotate Google Account Auth Keys for Luma CLI

> **Status**: Draft
> **Owner**: Gemini CLI
> **Dates**: Created: 2026-03-25 | Last Updated: 2026-03-25

## 1. Context & Goal
*ทำไมเราถึงสร้างสิ่งนี้? ปัญหาคืออะไร?*

### Problem
ปัจจุบัน Luma CLI ใช้ API Key เดียวในการเรียกใช้งาน LLM (Gemini) ซึ่งทำให้เกิดข้อจำกัดด้าน Rate Limit (RPM/TPM) และโควตาการใช้งานรายวัน เมื่อมีการใช้งานหนักหรือทำงานพร้อมกันหลาย Task จะทำให้เกิด Error และหยุดชะงัก

### Goal
เพิ่มระบบ **Key Rotation** เพื่อให้ Luma CLI สามารถสลับใช้งาน Google API Keys หลายชุดได้โดยอัตโนมัติ ช่วยเพิ่มเพดานการเรียกใช้งาน (Throughput) และทำให้ระบบทำงานต่อเนื่องได้ยาวนานขึ้นโดยไม่ติดปัญหา Rate Limit

---

## 2. User Journey & Requirements
*ประสบการณ์ที่ผู้ใช้ควรได้รับคืออะไร?*

### User Story
As a **Developer**, I want **Luma to automatically rotate between multiple Google API keys**, so that **I can perform heavy AI tasks without being interrupted by rate limit errors**.

### Functional Requirements
- [ ] รองรับการระบุ `GOOGLE_API_KEY` หลายรายการในไฟล์ `.env` หรือ configuration
- [ ] ตรวจจับ Error ประเภท Rate Limit (เช่น HTTP 429) จาก Google AI API
- [ ] สลับไปใช้ Key ถัดไปโดยอัตโนมัติเมื่อ Key ปัจจุบันติด Limit
- [ ] มีกลไกการเลือก Key แบบ Round-robin หรือ Random เพื่อกระจาย Load
- [ ] บันทึกสถานะการใช้งานหรือ Cooldown ของแต่ละ Key เพื่อไม่ให้เลือก Key ที่ยังติด Limit อยู่มาใช้ซ้ำทันที

### Non-Functional Requirements
- **Security**: API Keys ทั้งหมดต้องถูกเก็บเป็นความลับใน `.env` และไม่ถูก Commit เข้า Repository
- **Robustness**: ระบบสลับ Key ต้องทำงานได้รวดเร็ว (Low Latency) และไม่ทำให้ Request ล้มเหลวถ้ายังมี Key อื่นที่ใช้งานได้
- **Observability**: ผู้ใช้ควรทราบ (ผ่าน log หรือ UI) เมื่อมีการสลับ Key เกิดขึ้น

---

## 3. Specification by Example (SBE)
*ตัวอย่างพฤติกรรมที่เป็นรูปธรรม*

### Scenario: Automatic Switch on Rate Limit
**Given** มีการตั้งค่า API Keys ไว้ 2 ชุด (Key_A, Key_B) และปัจจุบันใช้ Key_A อยู่
**When** ส่ง Request ไปยัง Google AI แล้วได้รับ Error `429: Rate limit reached`
**Then** ระบบต้องสลับไปใช้ Key_B และส่ง Request เดิมซ้ำทันทีโดยที่ User ไม่ต้องทำอะไร

#### Examples
| Configured Keys | Current Key | API Response | Action | Final Result |
|-------|--------|-------|-------|-------|
| [Key_A, Key_B] | Key_A | 429 Too Many Requests | Switch to Key_B & Retry | Success via Key_B |
| [Key_A, Key_B] | Key_B | 200 OK | None | Success via Key_B |

### Scenario: All Keys Exhausted
**Given** API Keys ทุกชุด (Key_A, Key_B) ติด Rate Limit ทั้งหมด
**When** ส่ง Request ใหม่เข้าไป
**Then** ระบบต้องแสดง Error Message ที่ชัดเจนบอกว่า "All API keys are exhausted" และระบุเวลาที่ควรลองใหม่ (ถ้าทราบ)

#### Examples
| Configured Keys State | Request | Expected System Behavior |
|-------|--------|-------|
| All keys in Cooldown | Any Prompt | Display: "Critical: All API keys rate limited. Please wait." |
| 1 Key available | Any Prompt | Use the available key and process normally. |

---

## 4. Constraints & Risks
*สิ่งที่ควรระวัง*
- **Constraint**: ต้องยังคงรองรับการใช้งานแบบ Single Key (Backward Compatibility) สำหรับผู้ใช้ทั่วไป
- **Risk**: Google อาจตรวจพบพฤติกรรมการใช้หลาย Key จาก IP เดียวกันเพื่อเลี่ยง Limit (Violation of ToS) หากใช้งานหนักจนเกินไป
- **Risk**: การจัดการสถานะ Cooldown ของ Key ข้าม Process (ถ้ามีหลาย Instance รันพร้อมกัน) อาจต้องใช้ไฟล์ Shared State หรือฐานข้อมูลขนาดเล็ก

---
**หมายเหตุ**: เมื่อ Specification นี้ได้รับการอนุมัติ จะเข้าสู่ขั้นตอนการเขียน `plan.md` เพื่อกำหนดโครงสร้างข้อมูลใน `.env` และ Logic การสลับ Key ใน `luma_core/llm.py` ต่อไป