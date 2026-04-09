# Implementation Plan: Remove code_review_prompt.txt & Fix worktree path resolution

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View
- **Modified Components**:
    - `luma_core/actions/quality_actions.py`: จะถูกแก้ไขเพื่อหยุดการสร้างไฟล์ `code_review_prompt.txt` และใช้ฟังก์ชันแก้ไข path ใหม่สำหรับ output ไฟล์เช่น `code_review.md`
    - `luma_core/tools.py`: จะมีการเพิ่มหรือปรับปรุงฟังก์ชันสำหรับตรวจจับ Git worktree และ resolve project root path ที่ถูกต้อง
- **New Components**:
    - อาจมีการเพิ่มฟังก์ชันย่อยใน `luma_core/tools.py` สำหรับจัดการ Git worktree detection โดยเฉพาะ
- **Dependencies**:
    - `git` CLI (ผ่าน `subprocess` หรือ `GitPython` หากมีอยู่และเหมาะสม) เพื่อตรวจจับ root ของ worktree/repository
    - `os`, `pathlib` สำหรับการจัดการ path
- **Data Model Changes**: None

---

## 2. Step-by-Step Implementation

### Step 1: หยุดการสร้างไฟล์ `code_review_prompt.txt`
- **Docs**: อัปเดตไฟล์ `docs/AI_GUIDE.md` หรือเอกสารที่เกี่ยวข้องหากมีการกล่าวถึง `code_review_prompt.txt`
- **Code**:
    - แก้ไข `luma_core/actions/quality_actions.py`: ค้นหาส่วนของโค้ดที่รับผิดชอบในการเขียนไฟล์ `code_review_prompt.txt` ลงดิสก์ และลบออก
- **Tests**:
    - เพิ่ม Unit Test ใน `tests/test_action_code_review.py` เพื่อยืนยันว่าไฟล์ `code_review_prompt.txt` ไม่ถูกสร้างขึ้นในระหว่างกระบวนการ Code Review

### Step 2: พัฒนา Worktree Path Resolution
- **Docs**: หากมีการสร้างฟังก์ชัน utility ใหม่ใน `luma_core/tools.py` ควรมี docstring อธิบายการทำงาน
- **Code**:
    - แก้ไข/เพิ่มใน `luma_core/tools.py`: สร้างฟังก์ชันใหม่ (เช่น `resolve_project_target_dir`) ที่สามารถ:
        1. ตรวจสอบว่า PWD (Current Working Directory) อยู่ใน Git repository หรือ worktree หรือไม่
        2. หากอยู่ใน worktree, ให้คืนค่า root path ของ worktree นั้น
        3. หากอยู่ใน main repository แต่ไม่ใช่ worktree, ให้คืนค่า root path ของ main repository นั้น
        4. หากอยู่นอก Git repository, ให้ fallback ไปใช้ `os.getcwd()` หรือ path ที่กำหนดไว้ใน config หากมี
        5. ควรใช้ `git rev-parse --show-toplevel` หรือ `git rev-parse --show-superproject-working-tree` (ถ้าจำเป็น) เพื่อหา root ของ worktree/repo
- **Tests**:
    - เพิ่ม Unit Test ใน `tests/test_tools.py` (หรือสร้าง `tests/test_worktree_resolution.py` หากจำเป็น) เพื่อครอบคลุมกรณีดังนี้:
        - รันใน main repository
        - รันใน worktree
        - รันใน directory ย่อยของ main repository/worktree
        - รันนอก Git repository

### Step 3: ปรับใช้ Worktree Path Resolution ใน `quality_actions.py`
- **Docs**: อัปเดต docstring หรือ comment ใน `quality_actions.py` หากมีการเปลี่ยนแปลงที่สำคัญ
- **Code**:
    - แก้ไข `luma_core/actions/quality_actions.py`: แทนที่การเรียกใช้ path resolution เดิมสำหรับการเขียน output ไฟล์ (เช่น `code_review.md`) ด้วยฟังก์ชัน `resolve_project_target_dir` ที่สร้างขึ้นใน Step 2
- **Tests**:
    - เพิ่ม/ปรับปรุง Unit Test ใน `tests/test_action_code_review.py` เพื่อยืนยันว่าไฟล์ `code_review.md` ถูกเขียนไปยัง path ที่ถูกต้อง เมื่อรันจาก main repository และจาก worktree

---

## 3. Verification Plan
*How will we verify success?*

> [!IMPORTANT]
> **Android Build Policy**: MUST use scripts in `Android/scripts/` (e.g., `build_android.sh`) instead of direct `./gradlew` to ensure correct JDK version (Java 21).

### Automated Tests
- [ ] Unit Tests:
    - `tests/test_action_code_review.py`: ตรวจสอบว่า `code_review_prompt.txt` ไม่ถูกสร้าง และ `code_review.md` ถูกสร้างใน worktree/main repo ที่ถูกต้อง
    - `tests/test_tools.py` (หรือไฟล์ใหม่สำหรับ worktree resolution): ตรวจสอบ `resolve_project_target_dir()` ทำงานได้ถูกต้องในสถานการณ์ต่างๆ (main repo, worktree, sub-directory, non-git)
- [ ] Integration Tests: ไม่มี Integration Test ที่มีอยู่โดยตรงสำหรับเรื่องนี้ แต่การรัน test suite ทั้งหมดควรผ่านเพื่อให้แน่ใจว่าไม่มี regression

### Manual Verification
- [ ] **Scenario 1: Clutter Reduction**
    - รันคำสั่ง Code Review (เช่น `luma code-review --issue <issue_id>`)
    - ตรวจสอบว่าไม่มีไฟล์ `code_review_prompt.txt` ถูกสร้างขึ้นใน project directory
- [ ] **Scenario 2: Worktree Output Path**
    - สร้าง Git worktree จาก repository ปัจจุบัน (เช่น `git worktree add ../my-feature-worktree main`)
    - เข้าไปใน `../my-feature-worktree`
    - รันคำสั่ง Code Review จากใน worktree นั้น
    - ตรวจสอบว่าไฟล์ `code_review.md` ถูกสร้างขึ้นใน root directory ของ `../my-feature-worktree` ไม่ใช่ใน main repository
- [ ] **Scenario 3: Main Repository Output Path**
    - กลับไปที่ main repository
    - รันคำสั่ง Code Review จากใน main repository
    - ตรวจสอบว่าไฟล์ `code_review.md` ถูกสร้างขึ้นใน root directory ของ main repository นั้น
- [ ] **Scenario 4: Non-Git Directory (Fallback)**
    - สร้าง directory ใหม่นอก Git repository
    - Copy เฉพาะไฟล์ `main.py` และ `luma_core/` บางส่วนที่จำเป็นไปที่นั่น (เป็นการทดสอบแบบจำลอง)
    - รัน Luma CLI (ถ้าเป็นไปได้ในสภาพแวดล้อมจำลองนี้) และตรวจสอบว่า output files ถูกเขียนใน PWD หรือ path ที่กำหนดใน config (หากระบบมี fallback นี้)
- [ ] **Compatibility Check**: รัน action อื่นๆ ที่อาจเรียกใช้ path resolution เพื่อให้แน่ใจว่าไม่มีผลกระทบที่ไม่พึงประสงค์ (Regression)
    - ตัวอย่างเช่น: `luma create-pr-summary`, `luma generate-project-report-diff`