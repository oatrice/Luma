# Analysis: Issue #35 Guided Planning Reliability for Multi-Issue Runs

> วันที่อัปเดตความถูกต้อง: 2026-04-03
> สถานะเอกสาร: Synced with implementation

---

## 📌 Feature Information

| รายการ | รายละเอียด |
|--------|-----------|
| Feature Name | Guided planning can fail on multi-issue runs due to overlong feature dirs and sticky LLM fallback |
| Issue Number | #35 |
| Issue URL | [oatrice/Luma#35](https://github.com/oatrice/Luma/issues/35) |
| Repository หลัก | `Luma` |
| Cross-Repo Impact | `Zenith` เป็น consumer ที่โดน Planning phase failure โดยตรง |
| สถานะปัจจุบัน | ✅ Implemented |

---

## 1. สรุปปัญหา

Guided Planning ของ Luma เคยล้มได้จาก 2 สาเหตุหลักที่เกิดใน multi-issue flow เดียวกัน:

1. `Analyst` และ `Spec` ใช้ชื่อ issue รวมมาตั้งชื่อโฟลเดอร์ใต้ `docs/features/` แบบตรง ๆ ทำให้ basename ยาวเกินข้อจำกัดของ filesystem และเกิด `OSError: [Errno 63] File name too long`
2. `FallbackModel` เริ่มจาก saved fallback index ที่บันทึกไว้ แต่ถ้า model ที่เริ่มต้นล้ม มันจะลองเฉพาะ tail ของลิสต์เดิมและไม่ wrap กลับไป model ต้น ๆ ทำให้ Planning fail ก่อนเวลา แม้ยังมี model อื่นพร้อมใช้งาน

ระหว่าง implementation มีการ refine requirement เพิ่มอีกหนึ่งข้อเพื่อให้ artifact name ใช้งานจริงง่ายขึ้น:

- ชื่อโฟลเดอร์ไม่ควรแค่ “ไม่พัง” แต่ควร “กระชับและอ่านได้”
- ถ้า title มีภาษาไทย ต้องถูกแปลงเป็น ASCII/Latin ก่อนนำไปทำ slug

---

## 2. สิ่งที่ถูก implement จริง

### 2.1 Compact Feature Directory Naming

โค้ดปัจจุบันใช้ helper กลางใน `luma_core/feature_dirs.py` แทนการประกอบชื่อโฟลเดอร์แบบ ad hoc ในแต่ละ agent

behavior จริง:

- คง prefix รูปแบบ `N_issue-<issue-number>_`
- normalize title ก่อน
- transliterate อักขระไทยเป็น Latin/ASCII แบบ deterministic
- แปลงสัญลักษณ์อย่าง `&` เป็นคำเชื่อมที่เหมาะกับ slug
- compact descriptive slug ให้เหลือสูงสุด `8` tokens และไม่เกิน `64` bytes
- ถ้า descriptive slug ถูก compact/truncate จะเติม hash suffix ยาว `8` ตัวอักษรเพื่อกันชื่อชน
- ถ้าชื่อโฟลเดอร์ทั้งก้อนยังเกิน `255` bytes จะ truncate รอบสุดท้ายแบบ byte-safe โดยยังคง hash suffix เดิมไว้

ตัวอย่าง output จริงจาก helper:

```text
9_issue-13-14-15-8_luma-integration-extract-machine-readable-json-mixed-st-978b51fc
```

ความยาวจริงของ dirname ตัวอย่างข้างบนคือ `83` bytes

ตัวอย่าง slug จาก title ไทย:

```text
Input:  ปรับปรุงการสร้างโฟลเดอร์สำหรับหลาย issue
Output: prabprungkarsrangofledorsamhrabhlay-issue
```

### 2.2 Agent Consistency

ตอนนี้ `Analyst`, `Spec`, และ `SBE` ใช้ helper naming ชุดเดียวกันทั้งหมด

ผลที่ได้:

- phase ต่าง ๆ ไม่สร้างโฟลเดอร์คนละชื่อจาก issue set เดียวกัน
- path lookup จาก `issue-<number>` ยังใช้ได้
- โฟลเดอร์ใหม่สั้นลงกว่ารุ่นแรกที่ปล่อยให้ slug โตไปจนชน filesystem limit

### 2.3 Circular Fallback

`FallbackModel` ใน `luma_core/llm.py` ถูกแก้ให้:

- อ่าน saved index ผ่าน `config.get_fallback_info(current_path)`
- เริ่มลอง model จาก index ที่บันทึกไว้
- สร้างลำดับลองแบบ circular
- ลองแต่ละ model ไม่เกิน 1 ครั้งต่อ request
- บันทึก index ใหม่ผ่าน `config.save_fallback_index(i, current_path)` เมื่อมี model สำเร็จ

สิ่งที่ไม่ได้ implement:

- ไม่มี field ใหม่ชื่อ `active_llm_fallback_position` ใน `LumaState`
- ไม่มี schema migration ใน `state_manager.py`
- ไม่ได้ย้าย fallback state ไปเก็บใน state file ของ workflow

---

## 3. ขอบเขตที่กระทบจริง

ไฟล์ที่เกี่ยวข้องจริง:

- `luma_core/feature_dirs.py`
- `luma_core/agents/analyst.py`
- `luma_core/agents/spec_agent.py`
- `luma_core/agents/sbe_agent.py`
- `luma_core/llm.py`
- `tests/test_feature_dir_naming.py`
- `tests/test_llm_fallback_rotation.py`

ไฟล์ที่ไม่ใช่ส่วนของ solution นี้โดยตรง:

- `luma_core/state_manager.py`
- workflow-level schema migration สำหรับ fallback position
- test files ชื่อ `tests/test_feature_dirs.py`, `tests/test_llm_fallback.py`, `tests/test_guided_planning_multi_issue.py`, `tests/test_guided_planning_fallback.py`

---

## 4. Acceptance Criteria Status

- [x] Multi-issue planning ไม่ล้มเพราะ basename ยาวเกิน
- [x] `Analyst` และ `Spec` ใช้ naming strategy เดียวกัน
- [x] `SBE` ถูกผูกเข้ากับ naming strategy เดียวกันด้วย
- [x] fallback chain เริ่มจาก saved index และ wrap กลับต้นลิสต์ได้
- [x] แต่ละ model ถูกลองไม่เกิน 1 ครั้งต่อ request
- [x] มี regression tests สำหรับ naming และ fallback rotation
- [x] ชื่อโฟลเดอร์กระชับขึ้นและ title ภาษาไทยถูกแปลงเป็น ASCII ก่อนทำ slug

---

## 5. ความเสี่ยงคงค้าง

- Thai transliteration เป็น deterministic ASCII conversion ไม่ใช่ semantic English translation แบบภาษาธรรมชาติ
- external script ที่เคยคาดหวัง descriptive slug แบบยาวเต็ม title อาจต้องเปลี่ยนมาพึ่ง `issue-<number>` prefix หรือ lookup logic ที่ยืดหยุ่นกว่า
- ถ้า model ทุกตัวใน chain ล้มเหลวพร้อมกัน Planning ก็ยัง fail ได้ตามจริง แต่จะ fail หลังจากลองครบหนึ่งรอบแล้วเท่านั้น

---

## 6. หลักฐานการยืนยัน

ชุดทดสอบที่ใช้ยืนยัน behavior จริง:

- `tests/test_feature_dir_naming.py`
- `tests/test_llm_fallback_rotation.py`
- `tests/test_llm_gemini_cli.py`
- `tests/test_llm_codex_cli.py`

ผลที่ยืนยันล่าสุดใน live repo:

```text
19 passed, 2 warnings
```
