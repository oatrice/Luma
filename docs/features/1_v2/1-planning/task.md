# Task: Luma Workflow Guardian Upgrade

> 📅 Created: 2025-01-19
> 🎯 Status: Planning

---

## Phase 0: Setup (v2-guardian branch)

- [x] 0.1 สร้าง branch `v2-guardian`
- [x] 0.2 สร้างโฟลเดอร์ `v1_legacy/`, `schemas/`, `tests/`
- [x] 0.3 ย้ายไฟล์เดิมไป `v1_legacy/`
- [/] 0.4 สร้าง `README.v2.md`

---

## Phase 1: State Management

- [/] 1.1 สร้าง `luma_core/state_manager.py`
  - [ ] LumaState dataclass
  - [ ] save_state() function
  - [ ] load_state() function
  - [ ] Phase enum (idle, selecting, coding, preflight, pr_pending)
- [ ] 1.2 State transition logic
  - [ ] transition_to() method
  - [ ] validate_transition() method
- [ ] 1.3 Unit tests for state manager

---

## Phase 2: GitHub Project Integration

- [ ] 2.1 สร้าง `luma_core/github_project.py`
- [ ] 2.2 fetch_kanban_cards() via gh CLI
  - [ ] Parse JSON output
  - [ ] Filter by status (Todo/In Progress/Done)
- [ ] 2.3 move_card_to_status()
  - [ ] GraphQL mutation via gh api
- [ ] 2.4 get_current_in_progress_task()
- [ ] 2.5 Sync with Luma state on actions
  - [ ] On issue select → move to In Progress
  - [ ] On PR create → move to In Review

---

## Phase 3: Pre-flight Checker

- [ ] 3.1 สร้าง `luma_core/preflight_checker.py`
- [ ] 3.2 Implement check types:
  - [ ] file_modified - ตรวจสอบว่าไฟล์ถูกแก้ไข
  - [ ] file_exists - ตรวจสอบว่าไฟล์มีอยู่
  - [ ] version_updated - ตรวจสอบ version ถูก bump
  - [ ] command - รัน command และ check exit code
- [ ] 3.3 Load rules from `.luma_rules.json`
- [ ] 3.4 Integrate with Create PR flow
  - [ ] Block if required checks fail
  - [ ] Show warning for optional checks

---

## Phase 4: Context Summarizer

- [ ] 4.1 สร้าง `luma_core/context_summarizer.py`
- [ ] 4.2 Parse rules from markdown files
  - [ ] Extract MUST/SHOULD/DON'T rules
  - [ ] Extract project-specific reminders
- [ ] 4.3 summarize_rules() function
- [ ] 4.4 Display on issue selection
- [ ] 4.5 (Optional) AI-powered summarization

---

## Phase 5: UI Upgrade

- [ ] 5.1 Redesign main menu in `main.py`
  - [ ] State-aware header
  - [ ] Active task display
  - [ ] Next step recommendation
- [ ] 5.2 Progress indicator
- [ ] 5.3 Color-coded status

---

## Phase 6: Project Configuration

- [ ] 6.1 Create `.luma_rules.json` schema
- [ ] 6.2 Create config for JarWise-Root
- [ ] 6.3 Create config for JarWise-Web
- [ ] 6.4 Create config for JarWise-Android
- [ ] 6.5 Rules loader utility

---

## ✅ Definition of Done

- [ ] State tracking ทำงาน (save/load JSON)
- [ ] GitHub Project sync ทำงาน
- [ ] Pre-flight checks block PR ถ้าไม่ผ่าน
- [ ] Context summary แสดงเมื่อเลือก Issue
- [ ] UI แสดง Active Task
- [ ] มี `.luma_rules.json` สำหรับ JarWise projects
- [ ] Tests pass
