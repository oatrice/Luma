# Implementation Plan: CLI Contract: Stable headless project selection by repo, path, or slug

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View
- **Modified Components**:
  - `main.py`: ขยาย `--project` resolution, กำหนด precedence, และเพิ่ม `resolved_target` ใน success/error payload
  - `luma_core/config.py`: เพิ่ม helper สำหรับ normalize selector, match by repo/slug/path, และคืน canonical project metadata
  - `luma_core/actions/issue_actions.py`: audit `bootstrap` compatibility ถ้าต้องแตะ action-specific behavior ระหว่างย้ายมาใช้ resolver เดียวกัน
  - `README.md`: อธิบาย headless contract ใหม่ให้ external callers ใช้งานได้
  - `docs/features/25_issue-84_cli-contract-support-stable-headless-project-selection-c8d4bcc1/*.md`: sync เอกสาร feature ให้ตรงกับ implementation
- **New Components**:
  - ไม่จำเป็นต้องสร้าง module ใหม่ถ้า helper สามารถอยู่ใน `main.py` และ `luma_core/config.py` ได้อย่างอ่านง่าย
  - หาก logic โตเกินพอดี ค่อยแยก helper ขนาดเล็กสำหรับ project selector normalization ในรอบ refactor
- **Dependencies**:
  - Python stdlib: `os`, `json`, `subprocess`
  - Existing registry: `.luma/projects.json`
  - Existing canonical metadata: `CANONICAL_KANBAN_BY_REPO` ใน `luma_core/config.py`

### Data Model Changes
```python
from typing import Optional, TypedDict, Any


class ResolvedTarget(TypedDict, total=False):
    project_key: Optional[str]
    repo: Optional[str]
    path: str
    slug: Optional[str]
    selector_type: str
    selector_input: str


class HeadlessPayload(TypedDict, total=False):
    status: str
    action: str
    project: str
    resolved_target: ResolvedTarget
    result: Any
    error: str
```

---

## 2. Step-by-Step Implementation

### Step 1: RED - Add failing tests for selector resolution and payload shape
- **Files**:
  - Modify `tests/test_main_headless_cli.py`
  - Modify `tests/test_main_global_config.py`
  - Modify `tests/test_headless_contract_stability.py`
  - Modify `tests/test_headless_bootstrap.py`
- **Docs**:
  - Use `spec.md` และ `sbe.md` เป็น source of truth สำหรับ test cases
- **Code**:
  - เพิ่ม tests สำหรับ `--project` แบบ repo/path/slug
  - เพิ่ม tests สำหรับ precedence ระหว่าง explicit selector, stored project, และ cwd inference
  - เพิ่ม tests ที่ยืนยันว่า JSON response มี `resolved_target`
  - เพิ่ม tests ที่ยืนยันว่า ambiguous selector fail loudly
- **Verification**:
  - Tests ใหม่ต้อง fail บน code ปัจจุบัน เพราะยังไม่มี repo/slug resolution และยังไม่มี `resolved_target`

### Step 2: GREEN - Generalize `--project` resolution without breaking numeric support
- **Files**:
  - Modify `main.py`
  - Modify `luma_core/config.py`
  - Optional: modify `.luma/projects.json` ถ้าต้องเพิ่ม/normalize metadata เพื่อให้ local repo resolution ชัดขึ้น
- **Docs**:
  - Update `analysis.md`/`spec.md` หากระหว่าง implementation พบข้อจำกัดใหม่ที่ต้องบันทึก
- **Code**:
  - สร้าง normalization flow สำหรับค่าของ `--project`:
    1. existing directory path
    2. exact numeric project key
    3. exact repo match
    4. unique slug match
    5. explicit error
  - เพิ่ม helper คืน canonical project object และ resolved metadata แบบเดียวกันทุก path
  - คุม precedence ให้ explicit selector ชนะ stored project/cwd inference เสมอ
- **Verification**:
  - Unit tests จาก Step 1 ผ่านในส่วน resolution logic

### Step 3: GREEN - Add explicit `resolved_target` to the machine-readable contract
- **Files**:
  - Modify `main.py`
  - Modify `tests/test_main_headless_cli.py`
  - Modify `tests/test_headless_contract_stability.py`
- **Docs**:
  - Update `README.md`
- **Code**:
  - ปรับ `build_success_payload(...)` และ `build_error_payload(...)` ให้แนบ `resolved_target`
  - Preserve field `project` เดิมในฐานะ requested selector / compatibility echo
  - ทำให้ error path ที่ resolve ไม่ได้ยังคงเป็น machine-readable JSON
- **Verification**:
  - Subprocess-style tests ยัง parse stdout ได้
  - Payload มี `resolved_target` ทั้ง success และ selector-resolution failure cases ตามที่ spec กำหนด

### Step 4: GREEN - Apply the same resolver to `bootstrap` and audit parity
- **Files**:
  - Modify `main.py`
  - Modify `luma_core/actions/issue_actions.py` เฉพาะเมื่อจำเป็นต่อ compatibility
  - Modify `tests/test_headless_bootstrap.py`
- **Docs**:
  - Update `sbe.md` ถ้ามี decision เพิ่มเติมเรื่อง expected bootstrap behavior
- **Code**:
  - ทำให้ `bootstrap` รับ project object ที่มาจาก resolver เดียวกับ headless action อื่น
  - ตรวจว่า branch bootstrap, state transition, และ existing issue lookup ยังไม่ regress
  - ถ้าพบ gap เรื่อง interactive selection parity ให้บันทึกเป็น follow-up แทนการ inflate scope
- **Verification**:
  - `tests/test_headless_bootstrap.py` ผ่าน
  - Manual check ยืนยันว่า numeric bootstrap เดิมยังทำงาน

### Step 5: REFACTOR - Consolidate helper naming, document the contract, and keep scope tight
- **Files**:
  - Modify `main.py`
  - Modify `luma_core/config.py`
  - Modify `README.md`
  - Modify feature docs ในโฟลเดอร์นี้
- **Docs**:
  - บันทึกชัดเจนว่า `#84` แก้ selector correctness และ explicit resolved-target reporting เท่านั้น
- **Code**:
  - ลด duplication ระหว่าง interactive/headless project lookup เท่าที่ทำได้โดยไม่เปลี่ยน behavior เกิน scope
  - เก็บ naming ให้สื่อว่า `project` คือ requested selector และ `resolved_target` คือ target จริง
- **Verification**:
  - Tests ทั้งหมดที่เกี่ยวข้องยังผ่านหลัง refactor
  - ไม่มีงาน `#43/#44` หลุดเข้ามาใน diff

---

## 3. Verification Plan
*How will we verify success?*

> [!IMPORTANT]
> **Android Build Policy**: MUST use scripts in `Android/scripts/` (e.g., `build_android.sh`) instead of direct `./gradlew` to ensure correct JDK version (Java 21).

### Automated Tests
- [ ] Unit Tests: `python3 -m pytest tests/test_main_headless_cli.py tests/test_main_global_config.py tests/test_headless_contract_stability.py tests/test_headless_bootstrap.py -q`
- [ ] Integration Tests: add subprocess coverage that verifies `stdout` remains parseable JSON after adding `resolved_target`
- [ ] Regression Tests: verify explicit selector precedence and ambiguous-selector failure paths

### Manual Verification
- [ ] Run a headless action with `--project 12` and confirm legacy numeric behavior still works
- [ ] Run a headless action with `--project /Users/oatrice/Software-projects/Cerebro` and confirm `resolved_target.path` matches that exact path
- [ ] Run a headless action with `--project oatrice/Luma` and confirm `resolved_target.repo` echoes `oatrice/Luma`
- [ ] Run a headless action with `--project backend` and confirm Luma returns a machine-readable ambiguity error instead of silently choosing a repo
- [ ] Run `bootstrap` with both numeric and stable selectors and confirm branch/state behavior still works while `resolved_target` is included
