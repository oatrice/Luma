# Implementation Plan Update: From Historical #40 Packet to `#84` Integration

> อัปเดตล่าสุด: 2026-04-24
> จุดประสงค์: เปลี่ยนเอกสารนี้จากแผนแพ็ก `#40/#42/#41` แบบเดิม ให้เป็น plan ที่อิง current code reality

## 1. Planning Decision

รอบถัดไปไม่ควรเริ่มจากการ “ทำ `#40` ใหม่” เพราะ:

- `#40` ถูกปิดแล้ว
- มี implementation จริงใน codebase แล้ว
- downstream blocker ที่แท้จริงตอนนี้คือ project selection contract (`#84`)

ดังนั้นแผนที่เหมาะสมคือ:

1. ใช้ `#84` เป็น primary implementation scope
2. audit compatibility กับ implementation เดิมจาก `#40`
3. ถ้ายังมี gap เฉพาะของ `bootstrap` หลังจากนั้น ค่อยเปิด follow-up issue ใหม่

## 2. Phased Plan

### Phase 1: Resolver Baseline for `#84`

- ระบุว่าระบบจะรับ selector อะไรบ้าง
  - `repo`
  - `path`
  - `slug`
  - legacy `--project`
- แยก logic การ resolve target ให้เป็น shared resolver เดียว
- เขียน tests สำหรับ precedence และ fallback

ผลลัพธ์ที่ต้องได้:

- deterministic project resolution
- test matrix ที่บอกชัดว่า explicit selector ชนะ numeric fallback

### Phase 2: Machine-readable Resolved Target

- ปรับ JSON success payload ให้ echo target ที่ resolve ได้จริง
- ปรับ JSON error payload ให้บอก requested vs resolved context เท่าที่เหมาะสม
- เพิ่ม tests สำหรับ response contract

ผลลัพธ์ที่ต้องได้:

- external callers ตรวจสอบได้ว่า Luma target ไปที่ไหนจริง

### Phase 3: `#40` Compatibility Pass

- ทำให้ `bootstrap` ใช้ shared resolver เดียวกับ headless actions อื่น
- verify ว่า branch bootstrap และ state transition ไม่ regress
- ตรวจว่า worktree-aware behavior ยังผ่าน

ผลลัพธ์ที่ต้องได้:

- `bootstrap` ยังคงทำงานได้
- numeric contract เดิมยังใช้งานได้แบบ backward-compatible
- stable selector contract ใหม่ถูก consume ได้จริง

### Deferred Phase: Follow-up Only If Needed

ค่อยแตก issue ใหม่หลัง `#84` ถ้ายังพบ gap ต่อไปนี้:

- `bootstrap` ยังคืน payload ที่บางเกินไปสำหรับ external orchestration
- `bootstrap` ยังไม่ parity กับ interactive selection constraints
- action naming / contract surface ยังชวนสับสน

## 3. Test Strategy

### Automated Tests

- unit tests สำหรับ selector resolution
- integration tests สำหรับ headless JSON response
- compatibility tests สำหรับ `bootstrap`
- regression tests สำหรับ legacy numeric `--project`

### Manual Verification

- เรียก headless action ด้วย stable selector ที่ชี้ Zenith ได้ชัด
- ตรวจว่าระบบไม่ resolve ไปโปรเจกต์อื่นแบบเงียบๆ
- ตรวจว่า `bootstrap` ยังสร้าง branch และ update state ตามเดิม

## 4. What Not to Batch Right Now

ไม่ควรรวมใน PR เดียวกับ `#84`:

- `#41` guided workflow parity เต็มตัว
- `#42` first-class issue creation cleanup
- telemetry / transcript polish

## 5. Decision Rule for Issue Tracking

### ไม่ควร reopen `#40` ตอนนี้ ถ้า:

- งานที่กำลังจะทำเป็น selector contract ใหม่ภายใต้ `#84`
- implementation เดิมของ `#40` ยังใช้เป็นฐานต่อได้

### ควรเปิด follow-up issue ใหม่ ถ้า:

- หลังทำ `#84` แล้ว ยังมี gap ที่เฉพาะกับ `bootstrap`
- gap นั้นไม่ใช่ core ของ stable selector แต่เป็น contract / parity debt ที่แยกรีวิวได้เอง

## 6. Related

- [Luma #40](https://github.com/oatrice/Luma/issues/40)
- [Luma #84](https://github.com/oatrice/Luma/issues/84)
- [Zenith #36](https://github.com/oatrice/Zenith/issues/36)
