# SBE: Guided Planning Reliability for Multi-Issue Runs

> 📅 Updated: 2026-04-03
> 🔗 Issue: https://github.com/oatrice/Luma/issues/35

---

## Feature

Guided Planning ต้องสร้าง feature directory ได้อย่างปลอดภัยและกระชับสำหรับ multi-issue run โดยคง prefix ที่ trace กลับไป issue number ได้, แปลง title ภาษาไทยให้เป็น ASCII ก่อนทำ slug, และต้องให้ `Analyst`, `Spec`, กับ `SBE` ใช้ helper naming เดียวกันทั้งหมด นอกจากนี้ fallback ของ LLM ต้องเริ่มจาก saved index แล้วหมุนครบทั้ง chain แบบ circular หาก model แรกที่ลองล้มเหลว

### Scenario: long multi-issue title yields a compact deterministic directory

**Given** มี multi-issue title ที่ยาวมาก  
**When** phase ใด phase หนึ่งใน Planning สร้าง feature directory  
**Then** ระบบต้องได้ dirname ที่ยัง trace issue number ได้, ไม่เกิน filesystem basename limit, และมี descriptive slug แบบ compact พร้อม hash suffix เมื่อมีการย่อชื่อ

#### Examples

| Issue number | Title shape | Expected result |
|--------------|-------------|-----------------|
| `13-14-15-8` | ยาวมากหลายประโยค | ได้ dirname รูปแบบ `9_issue-13-14-15-8_<compact-slug>-<8hex>` |
| `13-14` | สั้นพอประมาณ | ได้ dirname ที่ยังอ่านง่าย และอาจไม่ต้องย่อมาก |
| `35` | single issue title สั้น | ได้ dirname ที่ trace `issue-35` ได้โดยไม่ต้องยืดยาวเกินจำเป็น |

### Scenario: Thai title becomes ASCII slug before compaction

**Given** title มีภาษาไทยปนอยู่  
**When** ระบบ normalize title ไปเป็น slug  
**Then** slug ต้องเป็น ASCII-only และ deterministic

#### Examples

| Input title | Expected slug |
|-------------|---------------|
| `ปรับปรุงการสร้างโฟลเดอร์สำหรับหลาย issue` | `prabprungkarsrangofledorsamhrabhlay-issue` |
| `แก้ fallback model สำหรับ planning` | slug ASCII-only ที่ยังมีคำสำคัญจาก title |

### Scenario: Analyst, Spec, and SBE resolve the same directory

**Given** issue number เดียวกันและยังไม่มี planning artifact directory มาก่อน  
**When** `Analyst` สร้าง `analysis.md`, ต่อด้วย `Spec` และ `SBE`  
**Then** ทั้งสาม phase ต้องใช้ feature directory เดียวกัน

#### Examples

| Phase order | Expected behavior |
|-------------|-------------------|
| `Analyst -> Spec` | `spec.md` ถูกเขียนลง directory เดียวกับ `analysis.md` |
| `Analyst -> Spec -> SBE` | `sbe.md` ถูกเขียนลง directory เดียวกัน ไม่สร้าง sibling directory ใหม่ |

### Scenario: fallback wraps around from the saved index

**Given** saved fallback index ชี้ไปยังท้ายลิสต์ของ configured models  
**When** model ที่เริ่มต้นล้มเหลวแบบ transient  
**Then** ระบบต้อง wrap กลับไป model ต้นลิสต์และลองต่อให้ครบหนึ่งรอบก่อนสรุปว่า fail

#### Examples

| Model count | Saved index | Outcome | Expected traversal |
|-------------|-------------|---------|--------------------|
| `3` | `2` | model `0` succeeds | `2 -> 0` |
| `4` | `3` | model `1` succeeds | `3 -> 0 -> 1` |
| `1` | `0` | no success | `0` แล้ว fail ทันทีหลังลองครบหนึ่งรอบ |

---

## Notes

- helper จริงที่ใช้คือ `build_feature_dirname(...)`
- fallback state จริงถูกอ่าน/เขียนผ่าน config, ไม่ได้เก็บใน `LumaState`
- hash suffix มีไว้เพื่อลดโอกาสชื่อชนกันหลังจาก compact/truncate slug
