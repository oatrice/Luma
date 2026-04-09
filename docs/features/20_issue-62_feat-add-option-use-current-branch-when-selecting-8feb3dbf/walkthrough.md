# คู่มือการใช้งาน: ตัวเลือกใช้ Branch ปัจจุบัน

## วิธีใช้งาน

### ขั้นตอนที่ 1: เลือก Issue
```bash
python3 main.py
# เลือก: 2 (Select Issue from Kanban)
```

### ขั้นตอนที่ 2: เลือก Issue ที่ต้องการ
```
--- 📋 Select Issue to Work On ---
  [1] ✅  #62: feat: Add option to use current branch...
Select issue(s): 1
```

### ขั้นตอนที่ 3: เลือก Branch
```
🌿 Suggested branches:
  [0] 🔀 ใช้ branch ปัจจุบัน (feat/existing-work)
  [1] feat/62-use-current-branch-on-select
  [2] feat/62-option-current-branch-select
  [3] feat/62-select-issue-use-current
Select [0-3] or type custom name: 0
```

### ผลลัพธ์
```
✅ Started: #62
   🎯 #62: feat: Add option to use current branch when select
🌿 Branch: feat/existing-work
✅ Using current branch 'feat/existing-work' (no branch switch needed).
🔄 Syncing Kanban status...
```

## เมื่อไหร่ควรใช้

### ✅ ควรใช้ option [0]
- คุณอยู่บน feature branch ที่กำลังทำงานอยู่แล้ว
- ต้องการเพิ่มงาน (issue) เข้าไปใน branch เดิม
- ต้องการทดสอบหรือแก้ไขเพิ่มเติมบน branch เดิม

### ❌ ไม่ควรใช้ option [0]
- คุณอยู่บน `main` หรือ `master` (ควรสร้าง feature branch ใหม่)
- ต้องการเริ่มงานใหม่โดยสิ้นเชิง
- Issue ไม่เกี่ยวข้องกับงานบน branch ปัจจุบัน

## Tips
- ตัวเลือก `[0]` จะแสดงชื่อ branch ปัจจุบันในวงเล็บ เช่น `(feat/my-work)`
- หาก detect branch ไม่ได้ จะ fallback ไปใช้ suggestion แรกโดยอัตโนมัติ
- ยังสามารถพิมพ์ชื่อ branch เองได้เหมือนเดิม
