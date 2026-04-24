# Specification Update: Existing Headless Bootstrap and Stable Selector Follow-up

> อัปเดตล่าสุด: 2026-04-24
> สถานะ: Current-state aligned

## 1. Context

เดิม spec ชุดนี้ตั้งเป้าไว้กว้างสำหรับ `#40`, `#42`, และ `#41` พร้อมกัน แต่สถานะปัจจุบันเปลี่ยนไป:

- `#40` มี implementation แล้วใน codebase ผ่าน action `bootstrap`
- ปัญหาเร่งด่วนของ ecosystem ตอนนี้อยู่ที่ project selection semantics ไม่เสถียร
- follow-up ที่สำคัญที่สุดคือ `#84`

ดังนั้น spec update นี้มีจุดประสงค์เพื่อกำหนด “ขอบเขตจริง” ของสิ่งที่ต้องรักษาและสิ่งที่ควรทำต่อ โดยไม่ย้อนกลับไปมอง `#40` เป็นงานที่ยังว่างทั้งหมด

## 2. Current Contract Baseline

### 2.1 Existing Behavior That Must Be Preserved

Luma ปัจจุบันต้องยังคงรองรับ:

- headless action `bootstrap`
- การเลือก issue แบบระบุหมายเลข issue
- การ bootstrap branch
- การ transition state ไป `coding`
- การทำงานแบบ JSON stdout contract เมื่อใช้ `--json`

### 2.2 Current Known Contract Gaps

สิ่งที่ยังไม่ถือว่า fully aligned:

- response ของ `bootstrap` ยังไม่ให้ structured payload ที่ชัดเจนพอสำหรับ external callers
- ยังไม่ชัดว่าการเลือก issue ของ headless path บังคับ selection constraints เท่ากับ interactive path
- project resolution สำหรับ headless actions ยังพึ่ง numeric `--project` มากเกินไป

## 3. Scope of the Next Work

### 3.1 In Scope

งานถัดไปที่ควรทำภายใต้ `#84` และต้อง compatible กับ implementation จาก `#40`:

- รองรับ stable selector สำหรับ headless actions เช่น:
  - `repo`
  - `path`
  - `slug`
  - หรือ durable identity ที่เทียบเท่า
- กำหนด precedence ของ project resolution ให้ deterministic
- ให้ machine-readable response echo resolved target กลับมาแบบ explicit
- ทำให้ `bootstrap` และ headless actions อื่นใช้ resolver เดียวกัน

### 3.2 Out of Scope

สำหรับรอบนี้ ไม่ควร drift ไปทำ:

- first-class issue creation เต็มรูปแบบของ `#42`
- resumable guided workflow เต็มรูปแบบของ `#41`
- transcript / telemetry polish ที่ไม่จำเป็นต่อ selector correctness

## 4. Functional Requirements

### FR-1 Stable Selector Input

headless caller ต้องสามารถระบุ target project โดยไม่ต้องพึ่ง numeric key อย่างเดียว

ตัวอย่าง selector ที่ยอมรับได้:

- `repo`
- `path`
- `slug`
- legacy `--project` numeric key ในฐานะ fallback

### FR-2 Deterministic Resolution Precedence

ระบบต้องกำหนด precedence ชัดเจนระหว่าง:

1. explicit stable selector
2. explicit legacy `--project`
3. cwd / dynamic detection
4. stored last project

### FR-3 Explicit Resolved Target in Machine-readable Output

headless JSON response ต้องระบุ target ที่ระบบ resolve ได้จริง เช่น:

- project key ที่ใช้
- repo ที่ resolve ได้
- path ที่ใช้จริง
- slug หรือ canonical identifier ที่เทียบได้

### FR-4 Compatibility with Existing Bootstrap Action

action `bootstrap` ที่ถูกใช้ปิด `#40` ไปแล้ว ต้องสามารถทำงานผ่าน selector resolver เดียวกันได้โดยไม่ regress:

- branch bootstrap
- state transition
- current JSON success/error contract

## 5. Non-Functional Requirements

- ต้องคง backward compatibility กับ legacy numeric path เท่าที่ practical
- ต้องไม่ทำให้ interactive menu flow regress
- ต้องทำให้ external caller audit downstream target ได้ง่ายขึ้น

## 6. Acceptance Criteria

- headless Luma actions รองรับ stable selector ที่ไม่ fragile กว่า numeric-only contract
- machine-readable response ระบุ resolved target ชัดเจน
- action `bootstrap` ใช้ resolver เดียวกับ actions อื่นได้
- legacy numeric path ยังใช้ต่อได้อย่างตั้งใจในฐานะ fallback
- มี tests ครอบคลุม selector resolution และ bootstrap compatibility

## 7. Deferred Items

สิ่งต่อไปนี้ยังไม่ควรถูกนับเป็น requirement ของรอบ `#84`:

- rich structured payload เต็มรูปแบบเพื่อปิดทุก gap เดิมของ `#40`
- first-class issue creation parity ของ `#42`
- resumable guided workflow parity ของ `#41`

ถ้าหลังทำ `#84` แล้วพบว่า `bootstrap` ยังมี gap เฉพาะตัวอยู่ ให้แตก follow-up issue ใหม่แยกต่างหาก

## 8. Related

- [Luma #40](https://github.com/oatrice/Luma/issues/40)
- [Luma #84](https://github.com/oatrice/Luma/issues/84)
- [Zenith #36](https://github.com/oatrice/Zenith/issues/36)
