# Implementation Plan: Issue #35

> สถานะ: Completed
> เอกสารนี้อัปเดตให้ตรงกับ implementation ปัจจุบันแล้ว

## 1. Architecture Summary

solution จริงแบ่งเป็น 2 แกน:

1. **Compact feature directory naming**
   - รวม logic ตั้งชื่อไว้ที่ `luma_core/feature_dirs.py`
   - ใช้กับ `Analyst`, `Spec`, และ `SBE`
2. **Circular fallback rotation**
   - อยู่ใน `luma_core/llm.py`
   - อิง saved fallback index จาก config ต่อ working directory

ไม่มีการเพิ่ม field ใหม่ใน `LumaState` และไม่มีการแก้ schema ของ state manager

---

## 2. สิ่งที่ทำจริง

### Step 1: Centralize Feature Directory Naming

ไฟล์ที่แก้:

- `luma_core/feature_dirs.py`

สิ่งที่ทำ:

- เพิ่ม `sanitize_slug()`
- เพิ่ม Thai-to-ASCII transliteration
- เพิ่ม slug normalization
- เพิ่ม compact rules: สูงสุด 8 tokens, สูงสุด 64 bytes
- เพิ่ม hash suffix ยาว 8 ตัวอักษรเมื่อ slug ถูกย่อ
- เพิ่ม final byte-safe truncation สำหรับ basename limit 255 bytes

### Step 2: Wire All Planning Artifact Agents to the Same Helper

ไฟล์ที่แก้:

- `luma_core/agents/analyst.py`
- `luma_core/agents/spec_agent.py`
- `luma_core/agents/sbe_agent.py`

สิ่งที่ทำ:

- เปลี่ยนจากการ sanitize ชื่อในแต่ละไฟล์เอง
- ให้ทุก agent ใช้ `build_feature_dirname(...)`
- ทำให้ `analysis.md`, `spec.md`, และ `sbe.md` ไปอยู่ใน feature directory ที่ resolve แบบเดียวกัน

### Step 3: Fix Circular Fallback Rotation

ไฟล์ที่แก้:

- `luma_core/llm.py`

สิ่งที่ทำ:

- อ่าน saved index จาก `config.get_fallback_info(current_path)`
- สร้าง `ordered_indices` แบบเริ่มจาก saved index แล้ว wrap กลับต้นลิสต์
- ลองแต่ละ model ไม่เกิน 1 ครั้งต่อ request
- save index ใหม่เมื่อมี model สำเร็จ

### Step 4: Add Regression Coverage

ไฟล์ test ที่เพิ่ม/แก้จริง:

- `tests/test_feature_dir_naming.py`
- `tests/test_llm_fallback_rotation.py`

ไฟล์ regression ที่ใช้ตรวจร่วม:

- `tests/test_llm_gemini_cli.py`
- `tests/test_llm_codex_cli.py`

---

## 3. สิ่งที่ไม่ได้ทำ

รายการต่อไปนี้เคยถูกระบุในแผนรุ่นก่อน แต่ไม่ใช่ implementation จริง:

- ไม่ได้สร้าง `tests/test_feature_dirs.py`
- ไม่ได้สร้าง `tests/test_llm_fallback.py`
- ไม่ได้สร้าง `tests/test_guided_planning_multi_issue.py`
- ไม่ได้สร้าง `tests/test_guided_planning_fallback.py`
- ไม่ได้แก้ `state_manager.py`
- ไม่ได้เพิ่ม `active_llm_fallback_position` ใน state schema
- ไม่ได้สร้าง helper ชื่อ `get_safe_planning_workspace_name`

helper จริงที่ใช้คือ `build_feature_dirname(...)`

---

## 4. Verification Plan และผลลัพธ์

### Automated Verification

- [x] `tests/test_feature_dir_naming.py`
- [x] `tests/test_llm_fallback_rotation.py`
- [x] `tests/test_llm_gemini_cli.py`
- [x] `tests/test_llm_codex_cli.py`

ผลล่าสุดที่ยืนยันไว้:

```text
19 passed, 2 warnings
```

### Manual Verification

- [x] ตรวจ output ชื่อโฟลเดอร์ยาวมากแล้วเหลือประมาณ 83 bytes
- [x] ตรวจว่าชื่อยังมี prefix `issue-13-14-15-8`
- [x] ตรวจว่า Thai title ถูกแปลงเป็น ASCII slug
- [x] ตรวจว่า `Analyst`, `Spec`, และ `SBE` ใช้ helper เดียวกัน
- [x] ตรวจว่า fallback wrap ตามลำดับจาก saved index ได้จริง

---

## 5. ตัวอย่างผลลัพธ์จริง

### Compact dirname

```text
9_issue-13-14-15-8_luma-integration-extract-machine-readable-json-mixed-st-978b51fc
```

### Thai slug

```text
prabprungkarsrangofledorsamhrabhlay-issue
```
