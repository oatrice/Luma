# Implementation Plan: Fix worktree-family resolution for headless `code_review` and Luma project selection

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View

- **Modified Components**
  - `luma_core/tools.py`
  - `luma_core/actions/quality_actions.py`
  - `luma_core/config.py`
  - `tests/test_worktree_detection.py`
  - `tests/test_action_code_review.py`
  - `tests/test_config.py`
- **Optional Touchpoints (read-only validation)**
  - `luma_core/ui.py`
  - `tests/test_main_global_config.py`
- **Core Design Rule**
  - แยกชัดเจนระหว่าง "same git family" กับ "unrelated repo"
  - ใช้ canonical GitHub Project metadata เฉพาะ known repos เท่านั้น

### Data Model Changes

ไม่มี data model ใหม่ แต่มี behavioral contract ใหม่ 2 ชุดที่ต้องถือเป็น source of truth

1. `code_review` headless result:
   - `projects[].path` ต้องสะท้อน repo ที่ถูก inspect จริง
2. project selection / header metadata:
   - path ใน worktree family ของ Luma ต้อง resolve กลับ project key `12`
   - `oatrice/Luma` ต้องใช้ canonical kanban number `5`

---

## 2. Step-by-Step Implementation

### Step 1: Failing Test (RED) สำหรับ headless `code_review` path preservation
- **Files**
  - `tests/test_action_code_review.py`
  - `tests/test_worktree_detection.py`
- **Work**
  - เพิ่ม test ที่จำลองการรันจาก Luma worktree แต่ selected repos เป็น `Luma`, `JarWise-Root`, `JarWise-Web`
  - assert ว่า repo ภายนอกยังคง `path` ของตัวเองใน JSON payload
  - assert ว่า same-repo worktree ยัง remap ไป active worktree path ได้
- **Verification**
  - `python3 -m pytest -q tests/test_action_code_review.py::test_action_code_review_headless_preserves_external_repo_paths_from_worktree_context`
  - `python3 -m pytest -q tests/test_worktree_detection.py::TestResolveProjectTargetDir::test_preserves_unrelated_git_repo_when_running_from_other_worktree`

### Step 2: Passing Code (GREEN) สำหรับ worktree-family aware repo path resolution
- **Files**
  - `luma_core/tools.py`
  - `luma_core/actions/quality_actions.py`
- **Work**
  - เพิ่ม helper สำหรับเทียบ git common-dir
  - ปรับ `resolve_project_target_dir()` ให้ redirect ไป active worktree เฉพาะเมื่อ `cwd` และ `project_path` อยู่ใน git family เดียวกัน
  - ปรับ diagnostics ของ `code_review` ให้บอกเหตุผลของ remap อย่างชัดเจน
- **Verification**
  - รัน tests จาก Step 1 ซ้ำ
  - ยืนยันว่า payload ของ `Luma` ชี้ไป active worktree แต่ `JarWise-*` ไม่โดน rewrite

### Step 3: Failing Test (RED) สำหรับ canonical project identity และ wrong board drift
- **Files**
  - `tests/test_config.py`
- **Work**
  - เพิ่ม test สำหรับ known repo ที่ drift ไป kanban number/id ผิด ต้องถูก normalize กลับค่ากลาง
  - เพิ่ม test สำหรับ path ใน worktree family ของ Luma ที่ต้อง detect กลับ project key `12`
- **Verification**
  - `python3 -m pytest -q tests/test_config.py::test_config_normalizes_known_custom_project_kanban`
  - `python3 -m pytest -q tests/test_config.py::test_detect_project_key_for_path_resolves_matching_worktree_family`

### Step 4: Passing Code (GREEN) สำหรับ canonical metadata และ worktree-family project detection
- **Files**
  - `luma_core/config.py`
- **Work**
  - ปรับ `normalize_project_entry()` ให้ known repos ไม่ drift ไป kanban metadata ที่ผิด
  - ปรับ `detect_project_key_for_path()` ให้ fallback ไปจับคู่จาก git family ได้ เมื่อ path ไม่ได้ match จาก prefix ตรง ๆ
- **Verification**
  - รัน tests จาก Step 3 ให้ผ่าน
  - ตรวจสอบว่า behavior ของ unknown/custom repos ยัง preserve ค่าเดิมเมื่อไม่มี canonical mapping

### Step 5: Refactored Code (REFACTOR) เพื่อลด duplicated logic และกัน regression
- **Files**
  - `luma_core/tools.py`
  - `luma_core/config.py`
  - tests ที่เกี่ยวข้อง
- **Work**
  - ทำให้ helper เกี่ยวกับ git family อ่านง่ายและมีหน้าที่ชัด
  - ลด magic behavior ที่อาศัย `cwd` แบบ implicit โดยไม่เช็ก repo family
  - เก็บ wording ของ diagnostics ให้สื่อว่า remap เกิดจาก same git family ไม่ใช่ fallback แบบ global
- **Verification**
  - code review ภายในไฟล์ที่แก้
  - targeted regression test suite

### Step 6: Full Verification
- **Files**
  - ไม่มีไฟล์ใหม่ เน้นการ verify
- **Work**
  - รันชุด tests ที่ครอบทั้ง worktree path resolution, code review worktree behavior, และ config normalization
  - เตรียม manual verification สำหรับ issue #78 และ #79
- **Verification**
  - `python3 -m pytest -q tests/test_worktree_detection.py tests/test_worktree_path_resolution.py tests/test_code_review_worktree.py tests/test_action_code_review.py tests/test_config.py`

---

## 3. Verification Plan
*How will we verify success?*

### Automated Tests

- `tests/test_worktree_detection.py`
  - unrelated repo ต้องไม่ถูก rewrite ไป active worktree
  - same git family ต้อง remap ไป active worktree ได้
- `tests/test_action_code_review.py`
  - headless multi-repo payload ต้อง preserve external repo paths
- `tests/test_config.py`
  - known repo drift ต้องถูก normalize กลับ canonical kanban metadata
  - Luma worktree path ต้อง detect กลับ project key `12`
- Regression suite
  - `tests/test_worktree_path_resolution.py`
  - `tests/test_code_review_worktree.py`

### Manual Verification

- **Issue #78**
  1. รัน Luma จาก Luma worktree
  2. trigger headless `code_review` สำหรับ multi-repo target ที่มี JarWise
  3. ตรวจว่า diagnostics remap เฉพาะ repo ใน family เดียวกับ Luma
  4. ตรวจว่า JSON `projects[].path` ของ JarWise ชี้ path จริงของ JarWise

- **Issue #79**
  1. รัน Luma จาก Luma worktree
  2. เลือก project `12` (`Luma`)
  3. กลับมาหน้า header
  4. ตรวจว่า header แสดง `GH Proj: Project #5`

- **Non-worktree Regression**
  1. รัน Luma จาก main repo ปกติ
  2. ใช้งาน `code_review` และ project selection
  3. ตรวจว่าพฤติกรรมเดิมยังทำงานได้โดยไม่บังคับ remap เกินเหตุ
