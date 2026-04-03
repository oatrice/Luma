# SBE (Specification by Example) Template

> 📅 Created: 2026-04-03
> 🔗 Issue: https://github.com/oatrice/Luma/issues/35

---

## Feature: Guided Planning สำหรับ multi-issue run ที่สร้าง feature directory ได้อย่างปลอดภัยและหมุน fallback model ครบทั้ง chain

Guided Planning ต้องรองรับการวางแผนหลาย issues ในรอบเดียวโดยไม่ล้มในเฟส Planning แม้ชื่อรวมของ issues จะยาวมาก และแม้ `FALLBACK_ACTIVE_INDEX` จะชี้ไปยังโมเดลท้ายรายการที่ล้มชั่วคราว ระบบต้องสร้าง `docs/features/...` ด้วย basename ที่ปลอดภัยต่อ filesystem ผ่าน helper กลางเดียวกันใน `Analyst` และ `Spec` และต้องลอง fallback model แบบวนรอบจนกว่าจะสำเร็จหรือทดลองครบทุกโมเดลหนึ่งครั้ง

### Scenario: การวางแผนหลาย issues สำเร็จต่อเนื่องแม้ basename ยาวและโมเดลเริ่มต้นล้มชั่วคราว - Happy Path

**Given** Zenith เริ่ม Guided Feature Workflow ด้วยหลาย issues และ `Analyst` กับ `Spec` ใช้ helper เดียวกันในการสร้าง `docs/features/...` พร้อมมี fallback models ที่กำหนดลำดับไว้  
**When** Planning Phase รันโดย `FALLBACK_ACTIVE_INDEX` ชี้ไปยังโมเดลที่ล้มชั่วคราวระหว่าง `Spec` หรือ `SBE`  
**Then** ระบบต้องสร้าง feature directory ที่ปลอดภัย, ใช้ path เดียวกันตลอด `Analyst -> Spec -> SBE -> Architect`, และ retry โมเดลตามลำดับแบบวนรอบจนมีโมเดลหนึ่งสำเร็จโดยไม่ต้องกู้มือ

#### Examples

| Issue set | Candidate basename bytes | Saved index | Transient failure | Expected result |
|-----------|--------------------------|-------------|-------------------|-----------------|
| `#13-14-15-8` | `272` | `2` | `gemini-2.5-pro timeout` | สร้าง safe directory สำเร็จ, retry เป็น `gemini-2.5-pro -> gpt-4.1-mini`, และ handoff ถึง `Architect` |
| `#13-14` | `79` | `1` | `claude-3-5-sonnet abort` | ใช้ basename เดิมโดยไม่ truncate, retry เป็น `claude-3-5-sonnet -> gpt-4.1`, และ handoff ถึง `Architect` |
| `#13-15-8` | `108` | `2` | `gemini-2.5-pro 502` | สร้าง directory ได้ทันที, retry เป็น `gemini-2.5-pro -> o3-mini`, และ `SBE` ได้รับ path เดียวกับ `Spec` |
| `#13-14-15-8-35` | `225` | `1` | `gpt-4.1 429` | ใช้ basename เดิม, retry เป็น `gpt-4.1 -> claude-3-5-sonnet`, และ Planning Phase จบครบ handoff |

---

### Scenario: helper กลางต้องคุมขนาด basename ตาม byte limit และไม่โยน File name too long - Edge Case / Error Handling

**Given** ชื่อรวมของหลาย issues ถูกแปลงเป็น candidate basename สำหรับ `docs/features/...` โดย helper กลางที่ `Analyst` และ `Spec` เรียกใช้ร่วมกัน  
**When** helper ตรวจสอบความยาว basename ตามจำนวน bytes ก่อนสร้าง directory  
**Then** basename ที่ยาวไม่เกิน `255` bytes ต้องถูกใช้ต่อได้ตรงๆ, basename ที่ยาวเกิน `255` bytes ต้องถูก truncate และต่อ deterministic short hash suffix, และต้องไม่เกิด `OSError: [Errno 63] File name too long`

#### Examples

| Candidate basename bytes | Agent | Expected basename behavior |
|--------------------------|-------|----------------------------|
| `79` | `Analyst` | ใช้ basename เดิม, ไม่เติม hash suffix, สร้าง directory ได้ |
| `225` | `Spec` | ใช้ basename เดิม, ไม่เติม hash suffix, สร้าง directory ได้ |
| `255` | `Analyst` | ใช้ basename เดิมพอดี limit, ไม่เติม hash suffix, สร้าง directory ได้ |
| `256` | `Spec` | truncate basename, เติม deterministic short hash suffix, และสร้าง directory ได้ |
| `272` | `Analyst` | truncate basename, เติม deterministic short hash suffix, และสร้าง directory ได้ |

---

### Scenario: fallback ต้องวนครบหนึ่งรอบและจบด้วย error เดียวเมื่อทุกโมเดลล้ม - Boundary Conditions (Optional)

**Given** `Spec` หรือ `SBE` มี fallback model chain ที่บันทึก `FALLBACK_ACTIVE_INDEX` ไว้จากรอบก่อน  
**When** โมเดลทุกตัวใน chain ล้มเหลวต่อเนื่องใน request ปัจจุบัน  
**Then** ระบบต้องลองแต่ละโมเดลไม่เกินหนึ่งครั้งตามลำดับแบบวนรอบจาก saved index, ต้องไม่ข้ามโมเดลต้นรายการ, ต้องไม่วนไม่รู้จบ, และต้องรายงาน failure ที่รวมลำดับการลองทั้งหมดไว้สำหรับ manual recovery

#### Examples

| Configured models | Saved index | Failure sequence | Expected outcome |
|-------------------|-------------|------------------|------------------|
| `[gpt-4.1-mini, claude-3-5-sonnet, gemini-2.5-pro]` | `2` | `gemini timeout; gpt-4.1-mini 429; claude abort` | ล้มเหลวหลัง `3` ครั้งตามลำดับ `2 -> 0 -> 1` โดยไม่มีการลองซ้ำ |
| `[gpt-4.1, claude-3-5-sonnet]` | `1` | `claude timeout; gpt-4.1 500` | ล้มเหลวหลัง `2` ครั้งตามลำดับ `1 -> 0` และไม่ข้าม `gpt-4.1` |
| `[o3-mini]` | `0` | `o3-mini 503` | ล้มเหลวหลัง `1` ครั้งเท่านั้นและไม่ wrap ซ้ำ |
| `[gpt-4.1-mini, gpt-4.1, claude-3-5-sonnet, gemini-2.5-pro]` | `3` | `gemini 502; gpt-4.1-mini timeout; gpt-4.1 429; claude abort` | ล้มเหลวหลัง `4` ครั้งตามลำดับ `3 -> 0 -> 1 -> 2` พร้อมหลักฐานลำดับการลองครบทั้ง chain |

---

## Notes

- จำกัด basename ที่ `255` bytes เพื่อให้สอดคล้องกับ filesystem ทั่วไปที่ใช้ใน workflow นี้
- `Analyst` และ `Spec` ต้องได้ basename เดียวกันจาก input issue set เดียวกัน
- การ wrap fallback ใช้ได้ทั้งใน `Spec` และ `SBE` และต้องเคารพค่า `FALLBACK_ACTIVE_INDEX` ล่าสุด