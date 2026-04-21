# SBE (Specification by Example) Template

> 📅 Created: 2026-04-21
> 🔗 Issue: https://github.com/oatrice/Luma/issues/78, https://github.com/oatrice/Luma/issues/79

---

## Feature: Worktree-family resolution for headless `code_review` and Luma project selection

ฟีเจอร์นี้ทำให้ Luma แยกความต่างระหว่าง repo ที่อยู่ใน git/worktree family เดียวกับ active `cwd` ออกจาก repo ภายนอกได้อย่างถูกต้อง ส่งผลให้ headless `code_review` คืน path ของแต่ละ repo ได้ตรงความจริง และการเลือก project `Luma` จาก Luma worktree สามารถ map กลับไปยัง canonical GitHub Project board (`Project #5`) ได้อย่างสม่ำเสมอ

### Scenario: Preserve external repo paths in headless multi-repo review - Happy Path

**Given** Luma ถูกรันจาก `/Users/oatrice/Software-projects/Luma-worktrees/luma1`
**When** มีการเรียก headless `code_review` โดย selected repos มีทั้ง Luma และ JarWise repos
**Then** repos ที่อยู่นอก git family ของ Luma ต้องคง `path` เดิมของตัวเองในผลลัพธ์ JSON และไม่ถูก rewrite กลับมาเป็น path ของ Luma

#### Examples

| active_cwd | selected_repo | expected_result_path | expected_status |
|------------|---------------|----------------------|-----------------|
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `JarWise-Root` | `/Users/oatrice/Software-projects/JarWise` | `clean` |
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `JarWise-Web` | `/Users/oatrice/Software-projects/JarWise/Web` | `clean` |
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `JarWise-Backend` | `/Users/oatrice/Software-projects/JarWise/backend` | `reviewed` |
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `JarWise-Android` | `/Users/oatrice/Software-projects/JarWise/Android` | `clean` |

---

### Scenario: Remap same repo family to the active worktree and canonical board - Edge Case / Error Handling

**Given** current path อยู่ใน worktree family ของ `oatrice/Luma`
**When** ระบบ resolve project identity หรือแสดง header metadata สำหรับ Luma
**Then** path ของ Luma ต้อง map ไป active worktree, project key ต้อง resolve กลับ `12`, และ header ต้องแสดง `GH Proj: Project #5`

#### Examples

| current_path | selected_project | expected_project_key | expected_board |
|--------------|------------------|----------------------|----------------|
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `Luma` | `12` | `Project #5` |
| `/Users/oatrice/Software-projects/Luma-worktrees/luma2` | `Luma` | `12` | `Project #5` |
| `/Users/oatrice/Software-projects/Luma` | `Luma` | `12` | `Project #5` |
| `/private/var/folders/.../Luma-worktrees/luma1` | `Luma` | `12` | `Project #5` |

---

### Scenario: Avoid false remap or false project detection for unrelated paths - Boundary Conditions

**Given** current path หรือ configured target ไม่ได้อยู่ใน git family เดียวกับ Luma
**When** ระบบพยายาม resolve target path หรือ project key
**Then** ต้องไม่เกิดการ map ผิดไปที่ Luma worktree และต้องคืนค่า configured path เดิมหรือ `None` ตามบริบท

#### Examples

| current_path | configured_target | expected_resolved_target | expected_project_key |
|--------------|-------------------|--------------------------|----------------------|
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `/Users/oatrice/Software-projects/Cerebro` | `/Users/oatrice/Software-projects/Cerebro` | `None` |
| `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `/Users/oatrice/Software-projects/JarWise` | `/Users/oatrice/Software-projects/JarWise` | `None` |
| `/tmp/non-git-folder` | `/Users/oatrice/Software-projects/JarWise` | `/Users/oatrice/Software-projects/JarWise` | `None` |
| `/Users/oatrice/Software-projects/AnotherRepo` | `/Users/oatrice/Software-projects/Luma` | `/Users/oatrice/Software-projects/Luma` | `None` |

---

## Notes

- Known repo `oatrice/Luma` ต้องใช้ canonical GitHub Project metadata (`Project #5`) แม้ config ก่อนหน้าจะ drift ไปค่าอื่น
- Same-repo worktree remap ยังเป็น behavior ที่ต้องรักษาไว้ แต่ต้องจำกัดเฉพาะ git family เดียวกันเท่านั้น
- ตัวอย่าง path ในตารางใช้ค่าจริงจาก issue เพื่อให้เทียบกับ diagnostics และ machine-readable JSON ได้โดยตรง
