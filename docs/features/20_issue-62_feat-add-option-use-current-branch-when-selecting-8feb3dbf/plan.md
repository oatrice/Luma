# Implementation Plan

## Phase 1: Detect Current Branch
- [x] เพิ่ม code อ่าน branch ปัจจุบันด้วย `git branch --show-current`
- [x] เก็บค่าไว้ในตัวแปร `current_branch`

## Phase 2: Update UI
- [x] แสดงตัวเลือก `[0]` พร้อมชื่อ branch ปัจจุบัน
- [x] เปลี่ยน prompt จาก `[1-3]` เป็น `[0-3]`

## Phase 3: Handle Selection
- [x] Handle case `choice == "0"`
- [x] Set `use_current_branch = True`
- [x] Fallback กรณี detect ไม่ได้

## Phase 4: Skip Branch Creation
- [x] เพิ่ม condition `if use_current_branch`
- [x] ข้าม `git checkout -b` เมื่อใช้ branch ปัจจุบัน
- [x] แสดงข้อความยืนยันแทน

## Files Modified
| File | Changes |
|------|---------|
| `luma_core/actions/utils.py` | เพิ่ม logic ตรวจสอบและ handle current branch |

## Testing
- [ ] Test เลือก option 0 บน existing branch
- [ ] Test เลือก option 1-3 เพื่อสร้าง branch ใหม่
- [ ] Test ใส่ custom branch name
- [ ] Test กรณี detect branch ไม่ได้
