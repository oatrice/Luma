# Specification by Example Update: Bootstrap Compatibility and Stable Selector Follow-up

> อัปเดตล่าสุด: 2026-04-24
> ใช้สำหรับอธิบายพฤติกรรมที่ควรรักษาไว้จาก `#40` และพฤติกรรมใหม่ที่ต้องได้จาก `#84`

## Scenario 1: Existing Bootstrap Still Works with Legacy Numeric Project

**Given** ผู้เรียกยังใช้ legacy numeric `--project` ที่ระบบรองรับอยู่  
**When** เรียก headless action `bootstrap` พร้อม issue number ที่มีอยู่จริง  
**Then** Luma ต้องยัง bootstrap branch และ transition state ได้ตามเดิม

| Input | Expected Result |
|---|---|
| `--project 12 --action bootstrap --issue 40 --json` | success JSON |
| `result` | action สำเร็จ |
| side effects | state เปลี่ยนเป็น `coding`, branch ถูกสร้างหรือ switch |

## Scenario 2: Explicit Stable Selector Overrides Fragile Numeric Mapping

**Given** environment ที่ numeric project key มีโอกาส drift  
**When** external caller ส่ง stable selector เช่น repo/path/slug อย่าง explicit  
**Then** Luma ต้องใช้ explicit selector เป็น source of truth

| Requested Selector | Legacy Numeric | Expected Resolved Target |
|---|---|---|
| `repo:oatrice/Zenith` | `1` | `oatrice/Zenith` |
| `path:/Users/oatrice/Software-projects/Zenith` | `1` | `/Users/oatrice/Software-projects/Zenith` |
| `slug:zenith` | `1` | canonical Zenith target |

## Scenario 3: Machine-readable Output Echoes Resolved Target

**Given** headless action ใดก็ตามที่ใช้ project resolution  
**When** action สำเร็จและ caller ขอ JSON output  
**Then** response ต้องระบุ target ที่ resolve ได้จริงอย่างชัดเจน

| Action | Input | Expected JSON Fields |
|---|---|---|
| `bootstrap` | stable selector + issue | `status`, `action`, `resolved_target` |
| `code_review` | stable selector | `status`, `action`, `resolved_target` |

ตัวอย่าง field ขั้นต่ำ:

```json
{
  "status": "success",
  "action": "bootstrap",
  "resolved_target": {
    "project_key": "dynamic-or-canonical",
    "repo": "oatrice/Zenith",
    "path": "/Users/oatrice/Software-projects/Zenith",
    "slug": "zenith"
  }
}
```

## Scenario 4: Bootstrap Compatibility Does Not Require Reopening `#40`

**Given** `#40` ถูกปิดและมี implementation อยู่แล้ว  
**When** เริ่มทำ `#84` เพื่อแก้ stable selector contract  
**Then** งานควรถูกมองว่าเป็น compatibility / integration with existing bootstrap implementation ไม่ใช่การ “ทำ `#40` ใหม่”

| Situation | Expected Tracking Decision |
|---|---|
| selector contract ใหม่ แต่ bootstrap logic เดิมยังใช้ได้ | ทำภายใต้ `#84` |
| หลังทำ `#84` แล้ว bootstrap ยังมี payload gap เฉพาะตัว | เปิด follow-up issue ใหม่ |
| ไม่มี gap ใหม่ที่แยกได้ชัด | ไม่ต้อง reopen `#40` |

## Scenario 5: Interactive Constraint Parity Is Audited Explicitly

**Given** interactive `Select Issue` ใช้ `_get_selectable_cards(...)`  
**When** bootstrap headless path ถูก audit ระหว่างงาน `#84`  
**Then** ต้องตัดสินให้ชัดว่า parity ผ่านแล้วหรือยัง

| Headless Input | Interactive Status Rule | Expected Outcome |
|---|---|---|
| issue อยู่ใน allowed status | selectable | bootstrap success |
| issue อยู่นอก allowed status | not selectable | fail explicitly or document intentional difference |

## Notes

- เอกสารนี้ตั้งใจลด ambiguity ระหว่าง “ของที่มีอยู่แล้ว” กับ “ของที่ยังควรทำต่อ”
- `#84` ควรเป็น primary scope
- `#40` ควรถูกใช้เป็น existing implementation baseline
