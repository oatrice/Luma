# Manual Verification Guide: Issue #90 - CLI Fix Invalid Selection When Adding Multiple Issues

## Prerequisites

- มี Luma environment พร้อม (Python 3.9+, GitHub CLI authenticated)
- มี GitHub project ที่มี Kanban และ issues ในสถานะ "Ready" หรือ "In Progress" อย่างน้อย 3-4 issues
- อยู่ใน CODING phase (หลังจาก select issue แล้ว)
- ใช้ real CLI หรือ headless mode สำหรับ testing

## Verification Scenarios

### 1. Scenario: Comma-separated Multiple Issues (Happy Path)

**Addresses:** Core issue #90 - แก้ปัญหา "Invalid selection" เมื่อพิมพ์ comma-separated เช่น "1,2,3"

**Steps:**
1. รัน Luma CLI และเลือก project
2. เลือก issue เพื่อเข้าสู่ CODING phase (ถ้ายังไม่ได้)
3. เลือก menu "Add Issue to Current Work Session"
4. เมื่อ prompt "Select issue(s) to add:" พิมพ์ "1,2,3"
5. Observe output

**Verify:**
- ✅ แสดง success messages: "✅ Added #X: Title" สำหรับแต่ละ issue
- ✅ แสดง "Active issues: #X, #Y, #Z" รวม 3 issues
- ✅ ไม่มี error message
- ✅ State อัพเดทถูกต้อง (check ด้วย `luma state` หรือ .luma_state.json)

### 2. Scenario: Space-separated Multiple Issues (Extended Support)

**Addresses:** Recommendation สำหรับ space-separated support เช่น "1 2 3"

**Steps:** เหมือน Scenario 1 แต่พิมพ์ "1 2 3" แทน "1,2,3"

**Verify:** เหมือน Scenario 1 - เพิ่ม issues ได้และแสดง messages ถูกต้อง

### 3. Scenario: Invalid Index Handling (Error Handling)

**Addresses:** จัดการ invalid inputs อย่างเหมาะสม

**Steps:**
1-4 เหมือน Scenario 1 แต่พิมพ์ "1,99" (สมมติมี issues แค่ 3-4 ตัว)

**Verify:**
- ✅ แสดง error "❌ Invalid index: 99"
- ✅ แต่เพิ่ม issue ที่ valid (1) ได้ และแสดง success message
- ✅ Active issues เพิ่มแค่ 1 ตัว

### 4. Scenario: Duplicate Prevention (Edge Case)

**Addresses:** ป้องกันการเพิ่ม duplicate issues

**Steps:**
1-2 เหมือน Scenario 1
3. เพิ่ม issue 1 ด้วย "1"
4. เลือก "Add Issue" อีกครั้ง และพิมพ์ "1,2"

**Verify:**
- ✅ แสดง warning "⚠️ #61 already active, skipping" สำหรับ issue 1
- ✅ เพิ่มแค่ issue 2 และแสดง success message
- ✅ Active issues รวม 2 ตัว (1 เดิม + 2 ใหม่)

### 5. Scenario: Single Issue Backward Compatibility (Regression Test)

**Addresses:** ตรวจสอบ backward compatibility

**Steps:** เหมือน Scenario 1 แต่พิมพ์ "1" (single digit)

**Verify:**
- ✅ เพิ่ม issue 1 ได้ปกติ
- ✅ แสดง success message "✅ Added #61: Title1"
- ✅ Active issues อัพเดทถูกต้อง

## Conclusion

หากทุก scenario pass, implementation ถือว่าตอบโจทย์ issue #90 ครบถ้วนแล้ว และพร้อมสำหรับ production.