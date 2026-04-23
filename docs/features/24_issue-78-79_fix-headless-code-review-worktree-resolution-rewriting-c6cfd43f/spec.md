# Specification: Fix worktree-family resolution for headless `code_review` and Luma project selection

> **Status**: Draft
> **Owner**: TBD
> **Dates**: Created: April 21, 2026 | Last Updated: April 21, 2026

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
Luma ยังมีพฤติกรรมไม่สอดคล้องกันเมื่อถูกรันจาก Luma worktree

สำหรับ issue [#78](https://github.com/oatrice/Luma/issues/78), headless `code_review` สามารถ rewrite path ของ external target repos กลับมาเป็น path ของ active Luma worktree ได้ ทำให้ machine-readable JSON รายงาน `path` ผิด และอาจประเมินสถานะของ repo จาก checkout ผิดตัว

สำหรับ issue [#79](https://github.com/oatrice/Luma/issues/79), การเลือก project `12` (`Luma`) จาก Luma worktree ยังอาจ resolve ไปยัง project context หรือ kanban metadata ที่ผิด ทำให้ header แสดง GitHub Project board ไม่ตรงกับ canonical board ของ `oatrice/Luma`

ทั้งสองอาการสะท้อนปัญหาคลาสเดียวกัน: ระบบยังแยก "same repo family" ออกจาก "unrelated repo" ได้ไม่แม่นพอ ทั้งใน path resolution และ project identity resolution

### Goal
ทำให้ Luma มี behavior ที่สม่ำเสมอเมื่อทำงานจาก worktree ดังนี้

- preserve target path ของ repos ที่อยู่นอก git/worktree family ของ active `cwd`
- remap ไป active worktree path ได้เฉพาะเมื่อ target อยู่ใน repo family เดียวกันจริง
- คืน machine-readable JSON ที่สะท้อน repo ที่ถูก inspect จริง
- resolve Luma worktree กลับไปยัง configured Luma project และ canonical GitHub Project board (`Project #5`) ได้อย่างถูกต้อง

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
As a **developer or external caller running Luma from a worktree**, I want Luma to **distinguish between the active repo family and unrelated target repositories**, so that **headless review results point at the correct repositories and the Luma UI shows the correct configured GitHub Project board for the current worktree**.

### Functional Requirements

- [ ] เมื่อ headless `code_review` ทำงานจาก Luma worktree และมี selected repos หลายตัว ระบบต้อง preserve configured `path` ของ repos ที่ไม่ใช่ git family เดียวกับ Luma
- [ ] เมื่อ target project อยู่ใน git family เดียวกับ active `cwd`, ระบบสามารถ remap ไปยัง active worktree path ได้
- [ ] Diagnostics ของ worktree remap ต้องอธิบายเหตุผลได้ว่าทำไม path จึงถูกเปลี่ยน
- [ ] Machine-readable JSON ของ `code_review` ต้องรายงาน `path` และ `status` ของแต่ละ project ตาม repo ที่ถูก inspect จริง
- [ ] เมื่อผู้ใช้เลือก project `12` (`Luma`) จาก Luma worktree, ระบบต้อง resolve กลับไปยัง configured Luma project key
- [ ] Header ของ Luma ต้องแสดง `GH Proj: Project #5` สำหรับ `oatrice/Luma`
- [ ] Known repos ที่มี canonical metadata ต้องไม่ drift ไป board อื่นจาก stale config
- [ ] Unknown repos หรือ custom repos ที่ไม่มี canonical mapping ต้องยังคงใช้ configured metadata เดิม

### Non-Functional Requirements

- [ ] **Predictability**: behavior ต้อง deterministic สำหรับ path เดียวกันและ config เดียวกัน
- [ ] **Backward Compatibility**: main-repo flows และ non-worktree flows ต้องไม่เสีย
- [ ] **Observability**: ข้อความ diagnostics ต้องช่วยอธิบายเหตุผลของ remap ได้โดยไม่ทำให้ external callers เข้าใจผิด

---

## 3. Specification by Example (SBE)
*Concrete examples of behavior.*

### Scenario: Headless code review preserves external target repositories
**Given** Luma ถูกรันจาก `/Users/oatrice/Software-projects/Luma-worktrees/luma1`
**When** มีการ review `JarWise-Root`, `JarWise-Web`, หรือ repo อื่นที่อยู่นอก git family ของ Luma
**Then** `projects[].path` ใน JSON ต้องตรงกับ configured target repo path ของแต่ละ repo และไม่ชี้กลับมาที่ Luma worktree

#### Examples
| Active CWD | Selected Repo | Expected Result Path |
|---|---|---|
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `JarWise-Root` | `/Users/oatrice/Software-projects/JarWise` |
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `JarWise-Web` | `/Users/oatrice/Software-projects/JarWise/Web` |
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `JarWise-Backend` | `/Users/oatrice/Software-projects/JarWise/backend` |

### Scenario: Luma worktree maps back to the configured Luma project
**Given** ผู้ใช้กำลังทำงานอยู่ใน Luma worktree
**When** ผู้ใช้เลือก project `12` (`Luma`) หรือระบบต้อง resolve project key จาก current path
**Then** path นั้นต้อง map กลับไปยัง configured Luma project และ header ต้องแสดง `GH Proj: Project #5`

#### Examples
| Current Path | Expected Project Key | Expected Header Board |
|---|---|---|
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `12` | `Project #5` |
| `/Users/oatrice/Software-projects/Luma-worktrees/luma2` | `12` | `Project #5` |
| `/Users/oatrice/Software-projects/Luma` | `12` | `Project #5` |

### Scenario: Same-family remap is allowed, false remap is not
**Given** ระบบต้องตัดสินใจว่าจะ remap path หรือไม่
**When** target project อยู่ใน git family เดียวกับ active `cwd`
**Then** ระบบอาจใช้ active worktree path ได้
**And** ถ้า target อยู่คนละ git family ระบบต้องคง configured path เดิมไว้

#### Examples
| Active CWD | Configured Target | Expected Effective Path |
|---|---|---|
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `/Users/oatrice/Software-projects/Luma` | `/Users/oatrice/Software-projects/Luma-worktrees/luma1` |
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `/Users/oatrice/Software-projects/JarWise` | `/Users/oatrice/Software-projects/JarWise` |
| `/Users/oatrice/Software-projects/Luma` | `/Users/oatrice/Software-projects/Luma` | `/Users/oatrice/Software-projects/Luma` |

---

## 4. Constraints & Risks
*What should we watch out for?*

- **Constraint**: ห้าม remap unrelated repos ไป active worktree เพียงเพราะ `cwd` ปัจจุบันอยู่ใน git repo
- **Constraint**: canonical override ต้องใช้กับ known repos เท่านั้น เพื่อไม่ไปลบล้าง custom metadata ของโปรเจกต์อื่น
- **Risk**: ถ้าแก้ path resolution แต่ไม่แก้ project key detection / canonical metadata พร้อมกัน issue #79 จะยังเกิดอยู่
- **Risk**: ถ้า override canonical metadata กว้างเกินไป อาจทำให้ custom project config ของ repo อื่นเสียพฤติกรรมเดิม
