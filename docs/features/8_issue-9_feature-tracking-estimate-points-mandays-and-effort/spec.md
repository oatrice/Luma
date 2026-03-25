# Specification: Feature: Tracking Estimate Points, Mandays, and Effort

> **Status**: Draft
> **Owner**: Gemini
> **Dates**: Created: March 19, 2026 | Last Updated: March 19, 2026

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
ระบบปัจจุบันยังขาดกลไกที่มีโครงสร้างในการติดตามเมตริกประสิทธิภาพการพัฒนา เช่น Estimate Points, Mandays และ Effort สำหรับ Issue และ Task ต่างๆ ทำให้การวิเคราะห์ความเร็ว (velocity), การวางแผนทรัพยากร และประสิทธิภาพโดยรวมของโปรเจกต์ทำได้ยากในหลายๆ โปรเจกต์

### Goal
เพื่อพัฒนาระบบที่มีมาตรฐานในการติดตามและจัดการ Estimate Points, Mandays และ Effort สำหรับ Issue และ Task ทั้งหมดในทุกโปรเจกต์ ซึ่งจะช่วยให้ทีมสามารถวิเคราะห์ประสิทธิภาพการพัฒนา ตรวจสอบความเร็ว และอำนวยความสะดวกในการวางแผนทรัพยากรและการวิเคราะห์เมตริกประสิทธิภาพได้อย่างมีข้อมูล

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
ในฐานะ **ผู้จัดการโปรเจกต์/หัวหน้าทีม** ฉันต้องการ **ป้อนและติดตาม Estimate Points, Mandays และ Effort สำหรับ Issue และ Task ต่างๆ และรวบรวมเมตริกเหล่านี้ในแต่ละโปรเจกต์** เพื่อที่ฉันจะได้ **วิเคราะห์ประสิทธิภาพการพัฒนา ตรวจสอบความเร็ว และปรับปรุงการวางแผนทรัพยากร**

### Functional Requirements
- [x] ผู้ใช้สามารถป้อนและแก้ไข Estimate Points สำหรับ Issue ที่กำหนดได้
- [x] ผู้ใช้สามารถป้อนและแก้ไข Mandays (Estimated และ Actual) สำหรับ Issue ที่กำหนดได้
- [x] ผู้ใช้สามารถป้อนและแก้ไข Effort level สำหรับ Issue ที่กำหนดได้
- [x] เมตริกที่ป้อนทั้งหมด (Estimate Points, Mandays, Effort) จะต้องถูกจัดเก็บอย่างถาวรและเข้าถึงได้ตลอดเซสชัน
- [x] ระบบต้องมีกลไกในการรวบรวมเมตริกเหล่านี้ในแต่ละโปรเจกต์
- [x] ระบบต้องมีคำสั่งหรือ UI เพื่อแสดงสรุปเมตริกประสิทธิภาพ
- [x] ระบบต้องอนุญาตให้ส่งออกข้อมูลสรุปประสิทธิภาพเพื่อการวิเคราะห์ภายนอกได้

### Non-Functional Requirements
- [x] Performance: ระบบควรอนุญาตให้ป้อนและเรียกค้นเมตริกได้อย่างรวดเร็ว แม้จะมี Issue และโปรเจกต์จำนวนมาก
- [x] Scalability: โครงสร้างข้อมูลควรสามารถรองรับการเพิ่มขึ้นของจำนวน Issue และโปรเจกต์ได้อย่างมีประสิทธิภาพโดยไม่ทำให้ประสิทธิภาพลดลงอย่างมีนัยสำคัญ
- [x] Data Integrity: ตรวจสอบความสอดคล้องของข้อมูลและป้องกันการสูญหายหรือเสียหายของเมตริกการติดตาม
- [x] Usability: กลไกการป้อนข้อมูลและการดูควรใช้งานง่ายและสะดวก
- [x] Compatibility: โซลูชันต้องเข้ากันได้กับโครงสร้างโปรเจกต์และเวิร์กโฟลว์ที่มีอยู่

---

## 3. Specification by Example (SBE)
*Concrete examples of behavior.*

### Scenario: ป้อนและอัปเดตเมตริกการติดตามสำหรับ Issue
**Given** มี Issue "Refactor User Authentication" (ID: #123) อยู่ใน "Project Alpha"
**When** ผู้ใช้ป้อน Estimate Points เป็น "8", Estimated Mandays เป็น "5", และ Effort Level เป็น "High" สำหรับ Issue #123 จากนั้นอัปเดต Estimated Mandays เป็น "6" และ Actual Mandays เป็น "7" ในภายหลัง
**Then** เมตริกการติดตามของ Issue จะถูกจัดเก็บและคงอยู่ โดยสะท้อนการอัปเดตล่าสุด

#### Examples
| Action | Issue ID | Project | Estimate Points | Estimated Mandays | Actual Mandays | Effort Level | Stored Metrics (JSON representation) |
|---|---|---|---|---|---|---|---|
| Initial Input | #123 | Project Alpha | 8 | 5 | N/A | High | `{"issue_id": "#123", "estimate_points": 8, "estimated_mandays": 5, "effort_level": "High"}` |
| Update | #123 | Project Alpha | 8 | 6 | 7 | High | `{"issue_id": "#123", "estimate_points": 8, "estimated_mandays": 6, "actual_mandays": 7, "effort_level": "High"}` |
| View | #123 | Project Alpha | 8 | 6 | 7 | High | `{"issue_id": "#123", "estimate_points": 8, "estimated_mandays": 6, "actual_mandays": 7, "effort_level": "High"}` |

### Scenario: ดูสรุปประสิทธิภาพที่รวบรวมจากหลายโปรเจกต์
**Given** มี Issue ที่มีเมตริกการติดตามบันทึกไว้ใน "Project Alpha" และ "Project Beta"
**When** ผู้ใช้ร้องขอเพื่อดูสรุปประสิทธิภาพในทุกโปรเจกต์
**Then** ระบบจะแสดงสรุป Estimate Points, Mandays และ Effort levels แบบรวม พร้อมตัวเลือกในการกรองหรือส่งออก

#### Examples
| Projects | Issues | Total Estimate Points | Total Estimated Mandays | Total Actual Mandays | Average Effort Level | Export Format |
|---|---|---|---|---|---|---|
| Project Alpha, Project Beta | Issue #123, #124, #201, #202 | 30 | 20 | 22 | Medium | JSON/CSV |
| Project Alpha | Issue #123, #124 | 18 | 12 | 13 | High | JSON/CSV |

---

## 4. Constraints & Risks
*What should we watch out for?*
- Constraint 1: โซลูชันจะต้องผสานรวมเข้ากับกลไกการติดตาม Issue ที่มีอยู่ได้อย่างราบรื่น
- Constraint 2: การจัดเก็บข้อมูลจะต้องสอดคล้องกับโครงสร้างข้อมูลโปรเจกต์ที่มีอยู่ (เช่น `.luma_state.json` หรือที่เก็บข้อมูลแบบถาวรในเครื่องที่คล้ายกัน)
- Constraint 3: UI/คำสั่งสำหรับการโต้ตอบจะต้องสอดคล้องกับประสบการณ์ CLI ปัจจุบัน

- Risk 1: **ความสอดคล้องของข้อมูล (Data Consistency):** การทำให้แน่ใจว่าเมตริกเชื่อมโยงกับ Issue และโปรเจกต์ได้อย่างถูกต้อง โดยเฉพาะเมื่อ Issue ถูกย้ายหรือลบ
- Risk 2: **ผลกระทบต่อประสิทธิภาพ (Performance Impact):** การรวบรวมเมตริกจากหลายโปรเจกต์/Issue อาจนำไปสู่ปัญหาคอขวดด้านประสิทธิภาพหากไม่มีการปรับปรุง
- Risk 3: **การยอมรับจากผู้ใช้ (User Adoption):** ผู้ใช้อาจต่อต้านการป้อนเมตริกเพิ่มเติมหากกระบวนการยุ่งยาก
- Risk 4: **ความกำกวมของคำจำกัดความ (Definition Ambiguity):** ทีมต่างๆ อาจตีความ "Estimate Points", "Mandays" และ "Effort Level" แตกต่างกัน ซึ่งนำไปสู่ข้อมูลที่ไม่สอดคล้องกันหากไม่มีการกำหนดที่ชัดเจน