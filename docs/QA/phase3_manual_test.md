# Phase 3: Pre-flight Checker - Manual Test Guide

เอกสารนี้อธิบายขั้นตอนการทดสอบฟีเจอร์ Pre-flight Checker แบบ Manual ผ่าน Luma CLI

## Prerequisites (สิ่งที่ต้องมีก่อนเริ่ม)

สร้างไฟล์ `.luma_rules.json` ที่ Root Folder ของโปรเจกต์ที่ต้องการทดสอบ (เช่น `Luma/` หรือ `JarWise/`) โดยใช้เนื้อหาทดสอบดังนี้:

```json
{
  "project": "Luma Test",
  "preflight_checks": [
    {
      "id": "check_readme",
      "name": "README Exists",
      "type": "file_exists",
      "path": "README.md",
      "required": true,
      "message": "Project must have a README.md file"
    },
    {
      "id": "check_version",
      "name": "Version Bumped",
      "type": "version_updated",
      "path": "package.json",
      "required": true,
      "message": "Version in package.json must be bumped"
    }
  ]
}
```

(หมายเหตุ: ถ้าโปรเจกต์ไม่มี `package.json` สามารถเปลี่ยน `path` เป็นไฟล์อื่นที่มีอยู่เพื่อทดสอบ `file_exists` ได้ แต่ `version_updated` ต้องใช้ไฟล์ที่มี field version)

---

## Test Scenario 1: Pre-flight Failed (กรณีไม่ผ่านกฎ)

**เป้าหมาย:** ทดสอบว่าระบบ Block การสร้าง PR เมื่อไม่ผ่านกฎที่ `required: true`

1.  **Start Luma**: รันคำสั่ง `python3 main.py`
2.  **Select Project**: เลือก Project ที่เราวางไฟล์ `.luma_rules.json` ไว้
3.  **Action**: เลือกเมนู **[2] Create PR**
4.  **Expectation (สิ่งที่ควรเกิด)**:
    -   ระบบเปลี่ยนสถานะเป็น `PREFLIGHT`
    -   แสดงรายการตรวจสอบ
    -   ❌ `Version Bumped` ควรจะ **Fail** (เพราะเรายังไม่ได้แก้ Version ในไฟล์)
    -   ระบบจะถาม: `❌ Some required checks failed. Proceed anyway? (y/n):`
5.  **Action**: ตอบ `n`
6.  **Result**: ระบบจะยกเลิกการสร้าง PR และสถานะกลับไปเป็น `CODING`

---

## Test Scenario 2: Pre-flight Check Passed (กรณีผ่านกฎ)

**เป้าหมาย:** ทดสอบการทำงานเมื่อกฎทุกข้อผ่าน

1.  **Modify File**: แก้ไขไฟล์ `package.json` (หรือไฟล์ที่กำหนดใน rules) เพื่อเปลี่ยนเลข Version
    ```json
    "version": "1.0.1" (เปลี่ยนเป็นเลขใหม่)
    ```
    *(ไม่ต้อง Commit ก็ได้ ระบบตรวจสอบ Change ใน Working Directory ได้)*
2.  **Start Luma**: รันคำสั่ง `python3 main.py`
3.  **Select Project**: เลือก Project เดิม
4.  **Action**: เลือกเมนู **[2] Create PR**
5.  **Expectation**:
    -   🛫 Running Pre-flight Checks...
    -   ✅ `README Exists`: OK
    -   ✅ `Version Bumped`: OK
    -   🚀 Pre-flight checks passed. Creating PR...
    -   ระบบเริ่มกระบวนการ Publisher Agent

---

## Test Scenario 3: Override Checks (กรณีบังคับผ่าน)

**เป้าหมาย:** ทดสอบปุ่ม Override เมื่อต้องการข้ามการตรวจสอบ

1.  **Revert Changes**: ยกเลิกการแก้ Version (เพื่อให้ Check Fail อีกครั้ง)
2.  **Action**: เลือกเมนู **[2] Create PR**
3.  **Result**: ❌ Check Fail
4.  **Action**: เมื่อระบบถาม `Proceed anyway? (y/n):` ให้ตอบ `y`
5.  **Expectation**:
    -   ⚠️ User chose to override checks.
    -   ระบบดำเนินการสร้าง PR ต่อแม้จะมีข้อผิดพลาด

---

## Clean Up
- ลบไฟล์ `.luma_rules.json` ออกหลังทดสอบเสร็จ (ถ้าไม่ต้องการใช้จริง)
