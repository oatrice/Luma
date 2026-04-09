# วิเคราะห์ทางเทคนิค: เพิ่มตัวเลือกใช้ branch ปัจจุบัน

## ภาพรวม
Issue #62 - เพิ่มตัวเลือก [0] ใช้ branch ปัจจุบัน เมื่อเลือก issue เพื่อให้สามารถทำงานบน branch เดิมได้โดยไม่ต้องสร้างใหม่

## ความต้องการ (Requirements)
- เมื่อผู้ใช้เลือก issue จาก Kanban ระบบแสดงตัวเลือก branch
- เพิ่มตัวเลือก [0] เพื่อใช้ branch ปัจจุบันที่อยู่แล้ว
- แสดงชื่อ branch ปัจจุบันในข้อความตัวเลือก
- ข้ามการสร้าง/switch branch หากเลือกใช้ branch ปัจจุบัน

## ไฟล์ที่มีผลกระทบ
- `luma_core/actions/utils.py` - ฟังก์ชัน `_start_issues()`

## การเปลี่ยนแปลงหลัก

### 1. ตรวจสอบ branch ปัจจุบัน
```python
result = subprocess.run(
    ["git", "branch", "--show-current"],
    cwd=project["path"],
    capture_output=True,
    text=True,
)
current_branch = result.stdout.strip()
```

### 2. แสดงตัวเลือก
```
🌿 Suggested branches:
  [0] 🔀 ใช้ branch ปัจจุบัน (feat/62-use-current-branch)
  [1] feat/62-use-current-branch-on-select
  [2] feat/62-option-current-branch-select
  [3] feat/62-select-issue-use-current
Select [0-3] or type custom name:
```

### 3. Handle ตัวเลือก [0]
```python
if choice == "0":
    if current_branch:
        branch_name = current_branch
        use_current_branch = True
```

### 4. ข้ามการสร้าง branch
```python
if use_current_branch:
    print(f"✅ Using current branch '{branch_name}' (no branch switch needed).")
else:
    # สร้าง branch ใหม่ตามปกติ
```

## ประโยชน์
- รองรับ workflow ที่ต้องการทำงานบน branch เดิม
- ลดเวลาในการสร้าง branch ใหม่เมื่อไม่จำเป็น
- คงความยืดหยุ่นในการทำงาน

## ความเสี่ยง
- ต่ำ - เป็น feature เสริมที่ไม่กระทบ flow เดิม
- ผู้ใช้ยังสามารถเลือกสร้าง branch ใหม่ได้ตามปกติ