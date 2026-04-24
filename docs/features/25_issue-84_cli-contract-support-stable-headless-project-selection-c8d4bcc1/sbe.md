# SBE (Specification by Example) Template

> 📅 Created: 2026-04-24
> 🔗 Issue: https://github.com/oatrice/Luma/issues/84

---

## Feature: Stable headless project selection and explicit resolved-target reporting

ฟีเจอร์นี้ทำให้ Luma headless contract รับค่า `--project` ที่เสถียรกว่า numeric key อย่างเดียว โดยรองรับ repo, path, slug หรือ equivalent durable selector ที่ resolve ได้อย่าง unique และคืน `resolved_target` กลับมาใน JSON response เพื่อให้ external callers ตรวจได้ว่า action รันกับ target ไหนจริง

### Scenario: Stable selector resolves the intended target - Happy Path

**Given** caller ส่ง explicit selector ผ่าน `--project`
**When** selector นั้น map ไปยัง local target ได้อย่าง unique
**Then** Luma ต้องรัน action กับ target นั้น และคืน `resolved_target` ที่ระบุ repo/path/key/slug ตามที่ resolve ได้จริง

#### Examples

| action | `--project` value | current cwd | expected resolved target |
|--------|-------------------|-------------|--------------------------|
| `code_review` | `repo:oatrice/Luma` | `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `repo=oatrice/Luma`, `project_key=12`, `slug=luma` |
| `code_review` | `path:/Users/oatrice/Software-projects/Cerebro` | `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | `repo=oatrice/Cerebro`, `project_key=13`, `slug=cerebro` |
| `bootstrap` | `slug:zenith` | `/Users/oatrice/Software-projects/Zenith` | `repo=oatrice/Zenith`, `project_key=15`, `slug=zenith` |
| `create_issue` | `path:/Users/oatrice/Software-projects/Luma` | `/Users/oatrice/Software-projects/Cerebro` | `repo=oatrice/Luma`, `project_key=12`, `slug=luma` |

---

### Scenario: Invalid or ambiguous selector fails loudly - Edge Case / Error Handling

**Given** caller ส่ง selector ที่ไม่ unique หรือไม่สามารถ map ไป local target ได้อย่างปลอดภัย
**When** Luma พยายาม resolve `--project`
**Then** ระบบต้องคืน machine-readable error และห้าม fallback ไป project อื่นแบบเงียบ ๆ

#### Examples

| `--project` value | expected error |
|-------------------|----------------|
| `repo:oatrice/Cerebro` | `Project selector 'repo:oatrice/Cerebro' is ambiguous.` |
| `repo:oatrice/UnknownRepo` | `Project selector 'repo:oatrice/UnknownRepo' did not match any local project.` |
| `path:/tmp/not-a-repo` | `Project selector 'path:/tmp/not-a-repo' is invalid.` |
| `slug:notfound` | `Project selector 'slug:notfound' did not match any local project.` |

---

### Scenario: Explicit selector precedence beats fragile context - Boundary Conditions

**Given** environment มี stored project หรือ cwd inference ที่อาจชี้ไปคนละ repo
**When** caller ส่ง explicit `--project`
**Then** explicit selector ต้องชนะ context อื่นเสมอ และถ้าไม่มี explicit selector จึงค่อยใช้ legacy fallback ตามลำดับ

#### Examples

| `--project` value | stored project | current cwd | expected precedence result |
|-------------------|----------------|-------------|----------------------------|
| `repo:oatrice/Zenith` | `1` | `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | resolve ไป `oatrice/Zenith` |
| `path:/Users/oatrice/Software-projects/Cerebro` | `12` | `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | resolve ไป `oatrice/Cerebro` |
| `12` | `1` | `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | resolve ไป key `12` |
| `not provided` | `13` | `/Users/oatrice/Software-projects/Luma-worktrees/luma1` | fallback ไป stored project `13` จนกว่าจะมี better explicit selector |

---

### Scenario: Bootstrap keeps legacy compatibility while reporting the resolved target - Boundary Conditions

**Given** `bootstrap` เป็น headless action เดิมที่ downstream automation ใช้อยู่แล้ว
**When** caller รัน `bootstrap` ด้วย numeric key หรือ stable selector
**Then** Luma ต้องยัง bootstrap branch/state ได้ตามเดิม และ JSON ต้องมี `resolved_target` เพื่อให้ caller audit target ได้

#### Examples

| command shape | expected |
|---------------|----------|
| `--auto --action bootstrap --issue 84 --project 12 --json` | success JSON, `resolved_target.project_key="12"` |
| `--auto --action bootstrap --issue 36 --project path:/Users/oatrice/Software-projects/Zenith --json` | success JSON, `resolved_target.repo="oatrice/Zenith"` |
| `--auto --action bootstrap --issue 36 --project repo:oatrice/Zenith --json` | success JSON พร้อม `resolved_target` หรือ explicit JSON error ถ้า local mapping ยังไม่พร้อม |
| `--auto --action bootstrap --issue 84 --project repo:oatrice/Cerebro --json` | JSON error, ไม่มี silent fallback ไป Cerebro root หรือ worktree |

---

## Notes

- `#84` ควรถูกมองเป็น standalone contract fix โดยใช้ implementation เดิมจาก `#40` เป็น baseline compatibility
- ถ้าหลังจากเพิ่ม `resolved_target` แล้วยังต้องการ rich bootstrap payload หรือ interactive parity เพิ่มเติม ให้เปิด follow-up issue แยก แทนการ inflate `#84`
- งาน `#43` (Telegram step-progress) และ `#44` (doc-quality validation) อยู่คนนละ concern และไม่ควรถูกรวมเข้ามาใน scope นี้
