```markdown
# Implementation Plan: Enhanced Git Worktree Support for Issue Selection and Code Review

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Approved

## 1. Architecture & Design
*High-level technical approach.*

### Component View
- **Modified Components**:
    - `luma_core/tools.py`: ฟังก์ชันที่เกี่ยวข้องกับการดำเนินการ Git และการระบุพาธ
    - `luma_core/config.py`: `DEFAULT_TARGET_DIR` (อาจถูกลบหรือทำให้เป็น Dynamic)
    - `luma_core/workflow.py` (หรือไฟล์แอคชันที่เกี่ยวข้อง): `_start_issues()`, `_start_issues_headless()`, `action_code_review()`
    - ยูทิลิตี้การสร้างไฟล์ภายใน `luma_core/` (เช่น `report_generator.py`, `doc_updates.py` หรือที่ที่ `spec.md`, `plan.md`, `sbe.md`, `code_review.md`, `draft_code_review.md` ถูกบันทึก)
- **New Components**: ฟังก์ชันตัวช่วยใหม่สำหรับการระบุ project root/worktree path ที่แข็งแกร่ง ฟังก์ชันนี้อาจอยู่ใน `luma_core/tools.py` หรือไฟล์ยูทิลิตี้ใหม่เช่น `luma_core/path_utils.py` หากความซับซ้อนสมควรมีไฟล์ใหม่
- **Dependencies**: เครื่องมือบรรทัดคำสั่ง `git`, โมดูล `os` สำหรับการจัดการพาธ

### Data Model Changes
```python
# ไม่มีการเปลี่ยนแปลงโมเดลข้อมูลที่คาดว่าจะเกิดขึ้นสำหรับฟีเจอร์นี้
# แม้ว่าลายเซ็นของฟังก์ชันภายในจะถูกแก้ไขเพื่อรับ 'target_dir' ก็ตาม
```

---

## 2. Step-by-Step Implementation

### Step 1: Implement Robust Project/Worktree Root Resolution (การนำการระบุ Project/Worktree Root ที่แข็งแกร่งมาใช้)
- **คำอธิบาย**: สร้างฟังก์ชันยูทิลิตี้ใหม่ (เช่น `resolve_project_root_or_worktree()`) ที่รับพารามิเตอร์ directory เริ่มต้น (optional) และส่งคืนพาธแบบ Absolute ไปยัง Git project root หรือ worktree root ที่ใช้งานอยู่ได้อย่างน่าเชื่อถือ ฟังก์ชันนี้ควรให้ความสำคัญกับ worktree root หากมีและแตกต่างจาก main project root โดยจะใช้ `git rev-parse --show-toplevel` และ `git rev-parse --show-superproject-working-tree` เพื่อกำหนดพาธที่ถูกต้อง
- **ไฟล์ที่เกี่ยวข้อง**:
    - `luma_core/tools.py`: เพิ่มฟังก์ชัน `resolve_project_root_or_worktree()`
    - อาจเป็น `luma_core/config.py`: อัปเดตวิธีการสร้าง `DEFAULT_TARGET_DIR` หากยังคงจำเป็น โดยใช้ฟังก์ชัน resolution ใหม่นี้
- **การทดสอบ**: เพิ่ม unit tests สำหรับ `resolve_project_root_or_worktree()` ซึ่งครอบคลุมสถานการณ์ main repo, worktree และ directory ที่ไม่ใช่ Git

### Step 2: Refactor `luma_core/tools.py` Functions to Accept `target_dir` (ปรับโครงสร้างฟังก์ชัน `luma_core/tools.py` ให้รับ `target_dir`)
- **คำอธิบาย**: แก้ไข `get_git_changed_files()`, `suggest_version_from_git()`, `generate_branch_suggestions()` และฟังก์ชัน Git อื่นๆ ใน `luma_core/tools.py` เพื่อรับพารามิเตอร์ `target_dir` แบบ optional คำสั่ง Git ทั้งหมดที่ดำเนินการภายในฟังก์ชันเหล่านี้จะต้องใช้ `target_dir` นี้ผ่านอาร์กิวเมนต์ `cwd` ของ `subprocess.run()`
- **ไฟล์ที่เกี่ยวข้อง**:
    - `luma_core/tools.py`: แก้ไขลายเซ็นฟังก์ชันและการดำเนินการคำสั่ง Git ภายใน
- **การทดสอบ**: อัปเดตการทดสอบที่มีอยู่สำหรับฟังก์ชันเหล่านี้เพื่อให้แน่ใจว่าทำงานได้อย่างถูกต้องทั้งแบบมีและไม่มีพารามิเตอร์ `target_dir` เพิ่มการทดสอบใหม่สำหรับบริบท worktree โดยเฉพาะ

### Step 3: Update `_start_issues()` and `_start_issues_headless()` (อัปเดต `_start_issues()` และ `_start_issues_headless()`)
- **คำอธิบาย**: ในฟังก์ชันที่รับผิดชอบการเลือก Issue (`_start_issues()` และ `_start_issues_headless()`) ให้เรียกใช้ `resolve_project_root_or_worktree()` ก่อนเพื่อรับพาธ project/worktree ปัจจุบัน จากนั้นส่งพาธที่ระบุนี้เป็น `target_dir` ไปยังการดำเนินการ Git ทั้งหมด (การสร้าง branch, การ checkout) และการเรียกใช้การสร้างไฟล์
- **ไฟล์ที่เกี่ยวข้อง**:
    - `luma_core/workflow.py` (หรือไฟล์ action ที่เกี่ยวข้อง): แก้ไข `_start_issues()` และ `_start_issues_headless()`
- **การทดสอบ**: เพิ่ม integration tests เพื่อตรวจสอบว่าการดำเนินการเลือก Issue (การสร้าง branch, การ checkout) เกิดขึ้นใน worktree ที่ถูกต้อง และไฟล์ที่สร้างขึ้นถูกบันทึกลงใน directory `docs/features/` ที่ถูกต้องภายใน worktree

### Step 4: Update `action_code_review()` and Related File Generation (อัปเดต `action_code_review()` และการสร้างไฟล์ที่เกี่ยวข้อง)
- **คำอธิบาย**: ใน `action_code_review()` ให้ระบุ project/worktree root ส่งพาธนี้ไปยัง `get_git_changed_files()` และตรวจสอบให้แน่ใจว่า `code_review.md` และ `draft_code_review.md` ถูกบันทึกลงใน directory `docs/features/` ที่สัมพันธ์กับพาธที่ระบุ ซึ่งอาจเกี่ยวข้องกับการอัปเดตฟังก์ชันยูทิลิตี้การบันทึกไฟล์ที่ `action_code_review()` เรียกใช้
- **ไฟล์ที่เกี่ยวข้อง**:
    - `luma_core/actions/action_code_review.py` (หรือไฟล์ที่คล้ายกัน): แก้ไข `action_code_review()`
    - `luma_core/report_generator.py` (หรือยูทิลิตี้การสร้างไฟล์): อัปเดตพาธสำหรับการบันทึกเอกสารรีวิว
- **การทดสอบ**: เพิ่ม integration tests เพื่อยืนยันว่าการ Code Review วิเคราะห์การเปลี่ยนแปลงใน worktree ได้อย่างถูกต้อง และบันทึกเอกสารรีวิวลงใน directory `docs/features/` ของ worktree

### Step 5: Consolidate File Generation Paths (รวมพาธการสร้างไฟล์)
- **คำอธิบาย**: ตรวจสอบให้แน่ใจว่าการสร้างไฟล์ทั้งหมด (`spec.md`, `plan.md`, `sbe.md`, `code_review.md`, `draft_code_review.md`) ใช้ project/worktree root ที่ระบุเป็นฐานสำหรับ directory `docs/features/` อย่างสอดคล้องกัน สร้างฟังก์ชันตัวช่วย หากจำเป็น เพื่อสร้างพาธเป้าหมายแบบเต็มสำหรับ `docs/features/<issue_dir>/<filename.md>`
- **ไฟล์ที่เกี่ยวข้อง**:
    - `luma_core/doc_updates.py` (หรือที่ที่ `spec.md`, `plan.md`, `sbe.md` ถูกบันทึก)
    - `luma_core/report_generator.py` (หรือที่ที่ `code_review.md`, `draft_code_review.md` ถูกบันทึก)
- **การทดสอบ**: Unit tests สำหรับฟังก์ชันตัวช่วยการสร้างพาธ และ end-to-end tests สำหรับการสร้างไฟล์ทั้งหมดภายใน worktrees

### Step 6: Ensure Backward Compatibility and Regression Testing (ตรวจสอบความเข้ากันได้ย้อนหลังและการทดสอบ Regression)
- **คำอธิบาย**: ตรวจสอบว่าการเปลี่ยนแปลงไม่ส่งผลกระทบในทางลบต่อโปรเจกต์ที่ไม่ได้ใช้ Git worktrees ซึ่งหมายความว่าพฤติกรรมเริ่มต้น (เมื่อไม่พบ worktree) ควรระบุไปยัง main repository's root ได้อย่างถูกต้อง
- **ไฟล์ที่เกี่ยวข้อง**: ไฟล์ที่แก้ไขทั้งหมด
- **การทดสอบ**: รันชุดการทดสอบที่มีอยู่; เพิ่ม regression tests สำหรับสถานการณ์ที่ไม่ใช่ worktree หากการทดสอบที่มีอยู่ไม่เพียงพอ

---

## 3. Verification Plan
*How will we verify success?*

> [!IMPORTANT]
> **Android Build Policy**: MUST use scripts in `Android/scripts/` (e.g., `build_android.sh`) instead of direct `./gradlew` to ensure correct JDK version (Java 21).

### Automated Tests
- [x] Unit Tests: สำหรับ `resolve_project_root_or_worktree()` ครอบคลุมการตั้งค่า Git ต่างๆ (main repo, worktree, non-Git)
- [x] Unit Tests: สำหรับฟังก์ชัน `luma_core/tools.py` ทั้งแบบมีและไม่มี `target_dir` (เช่น `get_git_changed_files()`)
- [x] Integration Tests:
    - `tests/test_issue_selection_worktree.py`: ตรวจสอบการสร้าง branch และการสร้างไฟล์ (`spec.md`, `plan.md`, `sbe.md`) เกิดขึ้นใน worktree และพาธที่ถูกต้อง
    - `tests/test_code_review_worktree.py`: ตรวจสอบว่าการ Code Review ระบุการเปลี่ยนแปลงที่เฉพาะเจาะจงกับ worktree และบันทึก `code_review.md` ใน directory `docs/features/` ของ worktree
    - Regression tests เพื่อให้แน่ใจว่าฟังก์ชันการทำงานที่ไม่ใช่ worktree ยังคงอยู่

### Manual Verification
- [x] **Scenario 1: Issue Selection from a Worktree (การเลือก Issue จาก Worktree)**
    1.  สร้าง Git repository (เช่น `~/repo/main`)
    2.  สร้าง worktree: `cd ~/repo/main && git worktree add ../worktrees/feature-x feature-x-branch`
    3.  นำทางไปยัง worktree: `cd ~/repo/worktrees/feature-x`
    4.  เปิด Luma CLI จาก `~/repo/worktrees/feature-x`
    5.  เลือก `[2] 📥 Select Issue (from Kanban)` และเลือก Issue
    6.  ตรวจสอบว่า branch ใหม่ (เช่น `feature-123`) ถูกสร้างและ checkout *ภายใน `~/repo/worktrees/feature-x`*
    7.  ตรวจสอบว่า `spec.md`, `plan.md`, และ `sbe.md` ถูกสร้างใน `~/repo/worktrees/feature-x/docs/features/issue-123/`
    8.  ตรวจสอบว่าการรัน `git status` ใน `~/repo/main` ไม่แสดงการเปลี่ยนแปลงที่เกี่ยวข้องกับ branch `feature-123` หรือไฟล์ที่สร้างขึ้น

- [x] **Scenario 2: Code Review in a Worktree (การ Code Review ใน Worktree)**
    1.  ทำตามขั้นตอน 1-3 จาก Scenario 1
    2.  ทำการเปลี่ยนแปลงโค้ดบางอย่างใน `~/repo/worktrees/feature-x` (เช่น แก้ไข `main.py`)
    3.  Stage การเปลี่ยนแปลง: `git add .`
    4.  เปิด Luma CLI จาก `~/repo/worktrees/feature-x`
    5.  เริ่มการดำเนินการ Code Review
    6.  ตรวจสอบว่ารายงาน Code Review ระบุการเปลี่ยนแปลงที่ทำขึ้น *ภายใน `~/repo/worktrees/feature-x`* ได้อย่างถูกต้อง
    7.  ตรวจสอบว่า `code_review.md` (และ `draft_code_review.md` หากมี) ถูกบันทึกใน `~/repo/worktrees/feature-x/docs/features/feature-x-branch/` (หรือ directory ฟีเจอร์ที่เฉพาะเจาะจงกับ worktree ที่คล้ายกัน)
    8.  ตรวจสอบว่าการรัน `git status` ใน `~/repo/main` ไม่แสดงการเปลี่ยนแปลงที่เกี่ยวข้องกับการ Code Review

- [x] **Scenario 3: Normal Operation (No Worktree) (การทำงานปกติ (ไม่มี Worktree))**
    1.  เปิด Luma CLI จาก main repository (`~/repo/main`) โดยไม่มี worktrees ที่ใช้งานอยู่
    2.  ทำการเลือก Issue และ Code Review
    3.  ตรวจสอบว่าการดำเนินการทั้งหมดและการสร้างไฟล์ทำงานเหมือนเดิมก่อนการเปลี่ยนแปลง โดยใช้พาธของ main repository ได้อย่างถูกต้อง
```