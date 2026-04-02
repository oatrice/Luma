# Story Points Programming Examples

เอกสารนี้เป็นภาคผนวกสำหรับช่วยตีความ Story Points ในงาน programming โดยใช้ตัวอย่างที่คุ้นกับงานซอฟต์แวร์มากขึ้น

## หลักคิดก่อนดูตัวอย่าง

- Story Points วัดความซับซ้อน ความเสี่ยง และ uncertainty
- ไม่ได้วัดชั่วโมงตรงๆ
- งานใช้เวลาสั้น แต่มี unknowns เยอะ ก็อาจได้ point สูง
- งานใช้เวลานานเพราะรอคนอื่นหรือรอ CI ไม่ได้แปลว่าต้อง point สูง

## ตารางจำง่าย

| Points | ความรู้สึกของงาน programming |
|---|---|
| `1` | แก้เล็กและชัดมาก |
| `2` | งานเล็ก มี logic เพิ่มขึ้นนิดหน่อย |
| `3` | งานกลาง มีหลายจุดที่ต้องแตะ |
| `5` | งาน feature/fix ที่ต้องวางแผน |
| `8` | งานใหญ่หรือเสี่ยง ควรแตก issue ก่อน |

## ตัวอย่างตามประเภทงาน

### 1. Bug Fix

- `1`: แก้ typo ใน error message หรือ mapping key ผิด 1 จุด
- `2`: แก้ bug ใน validation function ที่มีผลแค่ module เดียว
- `3`: แก้ bug ที่ต้องไล่หลายขั้นตอนและเพิ่ม regression test
- `5`: แก้ bug production ที่เกี่ยวข้องกับหลาย layer เช่น UI + API + persistence
- `8`: bug ที่ต้นเหตุยังไม่ชัด ต้องสืบสวนก่อน และกระทบหลาย flow

### 2. Refactor

- `1`: rename variable/function ให้ชัดขึ้นในไฟล์เดียว
- `2`: แยก helper function ออกจาก method ที่ยาว
- `3`: ปรับโครงสร้าง module หนึ่งพร้อม test ตาม
- `5`: refactor หลายไฟล์เพื่อเปลี่ยน boundary หรือ shared abstraction
- `8`: refactor cross-cutting ที่เสี่ยงกระทบหลาย feature

### 3. Test Work

- `1`: เพิ่ม unit test 1-2 เคสในไฟล์เดิม
- `2`: เพิ่ม test coverage สำหรับ function ที่มีหลาย branch
- `3`: เพิ่ม integration test สำหรับ flow หนึ่งชุด
- `5`: สร้าง test harness หรือ fixture ใหม่ที่หลาย test ต้องใช้ร่วมกัน
- `8`: ยกเครื่อง test strategy ของ subsystem หนึ่ง

### 4. UI / Frontend

- `1`: ปรับ spacing, label, หรือ empty state เล็กน้อย
- `2`: เพิ่มฟอร์ม field หรือ interaction ง่ายๆ
- `3`: สร้าง component ใหม่ที่มี state และ validation พื้นฐาน
- `5`: ทำ flow ใหม่ทั้งชุด เช่น wizard, settings screen, dashboard section
- `8`: ทำ UI ที่ผูกหลาย data source และมี responsive/edge case เยอะ

### 5. API / Backend

- `1`: เพิ่ม response field ที่ derive จากข้อมูลเดิม
- `2`: เพิ่ม endpoint ง่ายๆ ที่ logic ตรงไปตรงมา
- `3`: endpoint ที่มี validation, auth, และ persistence พื้นฐาน
- `5`: feature backend ที่แตะ schema, service, และ background flow
- `8`: เปลี่ยน contract หลักหรือแตะหลายบริการพร้อม migration risk

### 6. CLI / Tooling

- `1`: เพิ่ม flag ใหม่ที่ไม่กระทบ flow หลัก
- `2`: เพิ่ม command ย่อยแบบ simple
- `3`: command ที่มี parse input, validate, และ structured output
- `5`: CLI flow ใหม่ที่มีหลาย mode และ error handling หลายแบบ
- `8`: redesign contract ของ CLI หรือ compatibility-sensitive workflow

### 7. Integration / External Systems

- `1`: เปลี่ยน config หรือ endpoint URL อย่างปลอดภัย
- `2`: ต่อ service ภายนอกใน path ง่ายๆ ที่มีตัวอย่างชัด
- `3`: integration หนึ่งตัวที่มี auth, retry, หรือ mapping data
- `5`: integration ที่ต้อง handle state mismatch, contract drift, และ observability
- `8`: integration สำคัญต่อระบบ ที่ยังไม่ชัดเรื่อง failure modes และ rollback

## ตัวอย่างเปรียบเทียบที่คนชอบสับสน

### “เพิ่ม field เดียว” ไม่ได้แปลว่า `1` เสมอ

- ถ้าเพิ่ม field ใน DTO เดียวและ test ง่ายมาก = `1`
- ถ้าต้องแตะ serializer, validation, DB, API docs, และ backward compatibility = `3` หรือ `5`

### “ทำวันเดียว” ไม่ได้แปลว่า `1` หรือ `2`

- งานวันเดียวแต่ชัดมาก = `1` หรือ `2`
- งานวันเดียวแต่ต้องตัดสินใจเยอะ เสี่ยงพังหลายจุด = `3` หรือ `5`

### “โค้ดน้อย” ไม่ได้แปลว่า point ต่ำ

- 5 บรรทัดที่แก้ config ชัดๆ อาจเป็น `1`
- 5 บรรทัดที่เปลี่ยน behavior สำคัญของระบบ อาจเป็น `5`

## Rule of Thumb สำหรับ reviewer / planner

- ถ้าอธิบายงานได้ในประโยคเดียวและไม่มี hidden work: เริ่มที่ `1`
- ถ้ามี 2-3 ขั้นตอนชัดๆ: เริ่มที่ `2` หรือ `3`
- ถ้าต้องพูดถึง risk, compatibility, migration, rollback, หรือ coordination: เริ่มที่ `5`
- ถ้ายัง debate กันนานระหว่าง `5` กับ `8`: มักแปลว่าควรแตก issue ก่อน

## ใช้คู่กับเอกสารไหน

- เวอร์ชันหลัก: [Story Points Convention](/Users/oatrice/Software-projects/Luma/docs/story_points.md)
- เวอร์ชันเร็ว: [Story Points Cheat Sheet](/Users/oatrice/Software-projects/Luma/docs/story_points_cheatsheet.md)
