# Specification: Use Current Branch Option

## SBE (Specification by Example)

### Scenario 1: เลือกใช้ branch ปัจจุบัน
**Given** ผู้ใช้อยู่บน branch `feat/existing-work`  
**When** ผู้ใช้เลือก issue #62  
**And** เลือกตัวเลือก `[0] 🔀 ใช้ branch ปัจจุบัน`  
**Then** ระบบใช้ `feat/existing-work` ต่อโดยไม่สร้าง branch ใหม่

### Scenario 2: เลือกสร้าง branch ใหม่
**Given** ผู้ใช้อยู่บน branch `main`  
**When** ผู้ใช้เลือก issue #62  
**And** เลือกตัวเลือก `[1] feat/62-use-current-branch-on-select`  
**Then** ระบบสร้าง branch ใหม่และ checkout

## Technical Spec

### Input
- ผู้ใช้ป้อน `0`, `1`, `2`, `3` หรือชื่อ branch กำหนดเอง

### Output
- ข้อความยืนยันการใช้ branch ปัจจุบัน (กรณีเลือก 0)
- หรือข้อความยืนยันการสร้าง branch ใหม่ (กรณีเลือก 1-3)

### Error Handling
- หาก detect branch ปัจจุบันไม่ได้ → fallback ใช้ suggestion แรก
- หากใส่ตัวเลขผิด → ใช้ default suggestion

## UI/UX
```
🌿 Suggested branches:
  [0] 🔀 ใช้ branch ปัจจุบัน (feat/existing-branch)
  [1] feat/62-use-current-branch-on-select
  [2] feat/62-option-current-branch-select
  [3] feat/62-select-issue-use-current
Select [0-3] or type custom name: 0
✅ Using current branch 'feat/existing-branch' (no branch switch needed).
```
