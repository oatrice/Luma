# Manual Verification: Issue #84 Stable Headless Project Selection

> **Scope**: Verify the `#84` headless selector contract with side-effect-free probes first
> **Issues**: [#84](https://github.com/oatrice/Luma/issues/84), [#85](https://github.com/oatrice/Luma/issues/85), [#86](https://github.com/oatrice/Luma/issues/86), [#87](https://github.com/oatrice/Luma/issues/87), [#88](https://github.com/oatrice/Luma/issues/88)
> **Date**: 2026-04-24

---

## หมายเหตุการตีความผล

- ชุด verify นี้ใช้ `--action invalid_action` ในหลายกรณีเพื่อ probe เฉพาะ selector contract โดยหลีกเลี่ยง side effects
- ดังนั้น `status: "error"` และข้อความ `Action 'invalid_action' not found.` ถือว่า **ปกติ** ถ้า `resolved_target` และ selector semantics ถูกต้อง
- warning จาก `urllib3` และ `google.api_core` เป็น environment noise และ **ไม่ใช่** contract failure

---

## Verification Matrix

| Step | Scenario | Command | Expected Result | Actual Result | Verdict | Issue |
|------|----------|---------|-----------------|---------------|---------|-------|
| 1 | Prefixed key selector parse และ resolve ได้ | `python3 main.py --auto --action invalid_action --json --project key:12` | JSON parse ได้, `project="key:12"`, `resolved_target.selector_type="key"`, `project_key="12"` | ได้ `resolved_target` เป็น key `12`, repo `oatrice/Luma`, slug `luma`, `resolution_source="local_registry"` | PASS | `#84` |
| 2 | Legacy bare numeric ยังรองรับ | `python3 main.py --auto --action invalid_action --json --project 12` | JSON parse ได้, `project="12"`, `resolved_target.project_key="12"` | ได้ `resolved_target` เป็น key `12`, repo `oatrice/Luma`, slug `luma`, `resolution_source="local_registry"` | PASS | `#84`, baseline `#40` |
| 3 | Repo selector แบบ unique ใช้งานได้ | `python3 main.py --auto --action invalid_action --json --project repo:oatrice/Zenith` | JSON parse ได้, `resolved_target.repo="oatrice/Zenith"`, `project_key="15"`, `slug="zenith"` | resolve ไป Zenith ถูกต้องที่ path `/Users/oatrice/Software-projects/Zenith` | PASS | `#84`, related `oatrice/Zenith#36` |
| 4 | Slug selector แบบ unique ใช้งานได้ | `python3 main.py --auto --action invalid_action --json --project slug:zenith` | JSON parse ได้, `resolved_target.slug="zenith"`, `project_key="15"` | resolve ไป Zenith ถูกต้องด้วย `selector_type="slug"` | PASS | `#84`, related `oatrice/Zenith#36` |
| 5A | Path selector แบบ invalid ต้อง fail loudly | `python3 main.py --auto --action invalid_action --json --project path:/absolute/path/to/repo` | exit category เป็น selector error, `resolved_target=null`, `error_code="project_selector_invalid"` | ได้ `project_selector_invalid` พร้อม reason ว่า path ต้องชี้ไปยัง existing directory | PASS | `#84` |
| 5B | Path selector แบบ existing path และอยู่ใน registry ต้อง resolve เป็น local registry target | `python3 main.py --auto --action invalid_action --json --project path:/Users/oatrice/Software-projects/Zenith` | JSON parse ได้, `selector_type="path"`, `project_key="15"`, `repo="oatrice/Zenith"`, `resolution_source="local_registry"` | resolve ไป Zenith ถูกต้องด้วย `project_key="15"` และ `resolution_source="local_registry"` | PASS | `#84`, related `oatrice/Zenith#36` |
| 6 | Repo selector ambiguous ต้อง fail loudly | `python3 main.py --auto --action code_review --json --project repo:oatrice/Cerebro` | exit code `2`, `resolved_target=null`, `error_code="project_selector_ambiguous"`, มี `candidates` | ได้ ambiguous error พร้อม candidates `13` และ `14` | PASS | `#84`, defer disambiguation follow-up ไป `#85` |
| 7 | Slug selector not found ต้อง fail loudly | `python3 main.py --auto --action code_review --json --project slug:notfound` | exit code `2`, `resolved_target=null`, `error_code="project_selector_not_found"` | ได้ not-found error พร้อม `reason="No local project matched the selector."` | PASS | `#84` |

---

## Bootstrap Retest Update

| Step | Scenario | Command | Expected Result | Actual Result | Verdict | Issue |
|------|----------|---------|-----------------|---------------|---------|-------|
| 8 | Bootstrap แบบ legacy numeric ยังทำงานหลังแก้ branch fallback | `python3 main.py --auto --action bootstrap --issue 84 --json --project 12` | success JSON, `resolved_target.project_key="12"`, branch name ต้อง valid แม้ prompt export เปิดอยู่ | สร้าง branch `feat/84-cli-contract-support-stable-he` สำเร็จ, JSON success, `resolved_target` ถูกต้อง | PASS | `#84`, baseline `#40` |
| 9 | Bootstrap แบบ stable repo selector ยังทำงานหลังแก้ branch fallback | `python3 main.py --auto --action bootstrap --issue 36 --json --project repo:oatrice/Zenith` | success JSON, `resolved_target.repo="oatrice/Zenith"`, branch name ต้อง valid | สร้าง branch `feat/36-verify-zenith-specific-routing` สำเร็จ, JSON success, `resolved_target` ถูกต้อง | PASS | `#84`, related `oatrice/Zenith#36` |
| 10 | Repo selector not found ต้อง fail แบบ machine-readable | `python3 main.py --auto --action code_review --json --project repo:oatrice/UnknownRepo` | `resolved_target=null`, `error_code="project_selector_not_found"` | ได้ JSON error พร้อม `error_code="project_selector_not_found"` | PASS | `#84` |
| 11 | Invalid path selector ต้อง fail แบบ machine-readable | `python3 main.py --auto --action code_review --json --project path:/tmp/not-a-repo` | `resolved_target=null`, `error_code="project_selector_invalid"` | ได้ JSON error พร้อม `error_code="project_selector_invalid"` | PASS | `#84` |
| 12 | Direct path outside registry ต้อง resolve เป็น `direct_path` | `python3 main.py --auto --action invalid_action --json --project path:/tmp/luma-direct-path-verify` | `resolved_target.project_key=null`, `resolved_target.path="/tmp/luma-direct-path-verify"`, `resolution_source="direct_path"` | ได้ JSON parseable, `resolved_target` เป็น `direct_path` และ `project_key=null` ตรงตามคาด | PASS | `#84` |
| 13 | Explicit selector ต้องชนะ cwd / current worktree context | `python3 main.py --auto --action invalid_action --json --project repo:oatrice/Zenith` จาก Luma worktree | แม้อยู่ใน Luma worktree, `resolved_target` ต้องชี้ Zenith | ได้ `resolved_target.repo="oatrice/Zenith"` และ `path="/Users/oatrice/Software-projects/Zenith"` | PASS | `#84` |
| 14 | JSON-only stdout ต้องยัง parse ได้เมื่อ action มี stderr log | `python3 main.py --auto --action code_review --json --project repo:oatrice/Zenith > /tmp/luma-s9.stdout.json 2> /tmp/luma-s9.stderr.log` | `stdout` parse เป็น JSON ได้ และ diagnostic/log ไปอยู่ใน `stderr` | `python3 -m json.tool /tmp/luma-s9.stdout.json` ผ่าน (`JSON_OK`) และ `stderr` มี warnings/debug/PROMPT EXPORTED logs | PASS | `#84` |
| 15 | Bootstrap ambiguous selector ต้อง fail ก่อน side effects | `python3 main.py --auto --action bootstrap --issue 84 --json --project repo:oatrice/Cerebro > /tmp/luma-s12.stdout.json 2> /tmp/luma-s12.stderr.log` | exit code `2`, `resolved_target=null`, `error_code="project_selector_ambiguous"`, และ branch ก่อน/หลังไม่เปลี่ยน | ได้ exit code `2`, JSON error พร้อม candidates และ `diff` branch ก่อน/หลังไม่มีความต่าง | PASS | `#84`, defer disambiguation follow-up ไป `#85` |
| 16 | Explicit selector ต้องชนะ stored-project conflict | inject `.luma_global.json` ให้ cwd `/Users/oatrice/Software-projects/Luma-worktrees/luma1` ชี้ stored project `13`, แล้วรัน `python3 main.py --auto --action invalid_action --json` และ `python3 main.py --auto --action invalid_action --json --project repo:oatrice/Zenith` | probe แรกต้อง resolve ไป stored project `13`; probe ที่สองต้อง override ไป Zenith | ได้ probe แรก `resolved_target.project_key="13"` พร้อม `resolution_source="stored_project"` และ probe ที่สอง `resolved_target.repo="oatrice/Zenith"` พร้อม `resolution_source="local_registry"`; restore `.luma_global.json` กลับเรียบร้อย | PASS | `#84` |

---

## Coverage Mapping

| Coverage Area | Covered By | Notes |
|---------------|------------|-------|
| Stable single-selector contract (`key:`, `repo:`, `path:`, `slug:`) | Steps 1-5B, 12 | Acceptance หลักของ `#84` |
| Legacy numeric compatibility | Step 2 | ใช้ `12` แบบเดิมได้ต่อ |
| Explicit machine-readable `resolved_target` | Steps 1-5B, 8-15 | ต้องมีแม้ top-level action จะ fail เพราะ `invalid_action` |
| Ambiguity / not-found failure without silent fallback | Steps 6-7, 10-11, 15 | Acceptance หลักของ `#84` |
| Bootstrap compatibility with shared resolver | Steps 8-9 | ยืนยันว่า numeric และ stable selector ใช้ resolver เดียวกันได้ |
| Prompt-export-safe branch fallback in bootstrap | Steps 8-9 | branch name ไม่หลุดเป็น `[PROMPT EXPORTED] ...` อีกแล้ว |
| Need for compound selector disambiguation | Step 6 | เป็นช่องว่างที่ตั้งใจ defer ไป `#85` |
| Orchestration metadata envelope (`correlation_id`, `contract_version`, etc.) | Not covered in this round | อยู่นอก scope implementation รอบนี้ ไป `#86` |
| Bootstrap parity audit beyond shared resolver | Partially covered | branch bootstrap ผ่านแล้ว แต่ parity audit เชิงลึกยังเป็นงานของ `#87` |
| Explicit selector precedence over cwd/worktree context | Step 13 | ยืนยันว่า explicit repo selector ชนะ current Luma worktree context |
| Explicit selector precedence over stored-project conflict | Step 16 | ยืนยันว่า explicit repo selector ชนะ stored project ที่ inject ให้ชนจริง |
| JSON-only stdout compatibility for external callers | Step 14 | stdout parseable JSON, logs/warnings อยู่ใน stderr |
| Worktree execution path vs canonical `resolved_target.path` semantics | Observed during Step 8 and Step 13 | เปิด follow-up issue แยก เพราะยังต้องตัดสิน contract semantics ให้ชัด |

---

## Original 12-Scenario Status

| Original Scenario | Current Status | Evidence in This File | Notes |
|-------------------|----------------|------------------------|-------|
| 1. Prefixed selector parse ได้ | Tested | Step 1 | ผ่าน |
| 2. Legacy numeric ยังไม่พัง | Tested | Step 2 | ผ่าน |
| 3. Repo selector แบบ unique ใช้งานได้ | Tested | Step 3 | ผ่าน |
| 4. Slug selector แบบ unique ใช้งานได้ | Tested | Step 4 | ผ่าน |
| 5. Path selector แบบ direct target ใช้งานได้ | Tested | Steps 5A, 5B, 12 | ครอบคลุมทั้ง invalid path, existing path ใน registry, และ existing path นอก registry |
| 6. Repo selector ambiguous ต้อง fail loud | Tested | Step 6 | ผ่าน |
| 7. Slug/Repo not found ต้อง fail loud | Tested | Steps 7, 10, 11 | ครอบคลุมทั้ง slug not found, repo not found, invalid path |
| 8. Explicit selector ชนะ stored project / cwd | Tested | Steps 13, 16 | ครอบคลุมทั้ง current worktree/cwd context และ stored-project conflict แบบ injected |
| 9. JSON ต้องยัง parse ได้แม้มี stderr log | Tested | Step 14 | manual verify ผ่านด้วย `json.tool` และ stderr log capture |
| 10. Bootstrap แบบ legacy numeric ยังใช้ได้ | Tested | Step 8 | ผ่าน |
| 11. Bootstrap แบบ stable selector ใช้ resolver เดียวกัน | Tested | Step 9 | ผ่าน |
| 12. Bootstrap ต้องไม่ fallback เมื่อ selector ambiguous | Tested | Step 15 | exit code `2`, JSON error, และ branch ก่อน/หลังไม่เปลี่ยน |

---

## สรุปผลรอบนี้

- Steps 1-16 ผ่านครบตาม oracle ของ `#84`
- จุดที่เคยตีความว่า fail ในรอบแรกเกิดจากใช้ `invalid_action` เป็น probe แล้วคาดหวัง top-level success แทนที่จะดู correctness ของ `resolved_target`
- Path selector ต้องแยกดู 2 กรณี:
  - invalid path ต้อง fail แบบ machine-readable
  - existing path ต้อง resolve ตาม registry หรือ direct path ตามที่ path นั้น match ได้จริง
- Bootstrap retest ยืนยันว่าเมื่อเปิด prompt export อยู่ ระบบ fallback ไป branch name ที่ valid ได้แล้ว
- มี observation เพิ่มเติม 1 จุด: ใน Luma worktree case, git operation รันใน worktree path จริง แต่ `resolved_target.path` ใน JSON ยังเป็น canonical repo path จาก registry จึงเปิด follow-up issue [`#88`](https://github.com/oatrice/Luma/issues/88) เพื่อ clarify semantics นี้
- ถ้า map กลับไปที่ original plan 12 scenarios ตอนนี้ manual verify ครบแล้ว
- สิ่งที่ยังเหลือในเชิงออกแบบไม่ใช่ “verify gap” แต่เป็น “design/contract decision gap” เรื่องความหมายของ `resolved_target.path` ใน worktree case ซึ่งติดตามต่อใน [`#88`](https://github.com/oatrice/Luma/issues/88)

---

## Recommended Next Manual Verification

1. Decide whether `resolved_target.path` should mean canonical registry path or actual execution path when worktrees are involved
2. Audit deeper bootstrap parity with interactive selection constraints under [`#87`](https://github.com/oatrice/Luma/issues/87)
