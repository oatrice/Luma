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
- [x] 1.1 สร้าง `luma_core/state_manager.py`
  - [x] LumaState dataclass
  - [x] save_state() function
  - [x] load_state() function
  - [x] Phase enum (idle, selecting, coding, preflight, pr_pending)
- [x] 1.2 State transition logic
  - [x] transition_to() method
  - [x] validate_transition() method
- [x] 1.3 Unit tests for state manager

---

## Phase 2: GitHub Project Integration

- [x] 2.1 สร้าง `luma_core/github_project.py`
- [x] 2.2 fetch_kanban_cards() via gh CLI
  - [x] Parse JSON output
  - [x] Filter by status (Todo/In Progress/Done)
- [x] 2.3 move_card_to_status()
  - [x] GraphQL mutation via gh api
- [x] 2.4 get_current_in_progress_task()
- [x] 2.5 Sync with Luma state on actions
  - [x] On issue select → move to In Progress
  - [x] On PR create → move to In Review

---

## Phase 3: Pre-flight Checker

- [x] 3.1 สร้าง `luma_core/preflight_checker.py`
- [x] 3.2 Implement check types:
  - [x] file_modified - ตรวจสอบว่าไฟล์ถูกแก้ไข
  - [x] file_exists - ตรวจสอบว่าไฟล์มีอยู่
  - [x] version_updated - ตรวจสอบ version ถูก bump
  - [x] command - รัน command และ check exit code
- [x] 3.3 Load rules from `.luma_rules.json`
- [x] 3.4 Integrate with Create PR flow
  - [x] Block if required checks fail
  - [x] Show warning for optional checks

---

## Phase 4: Context Summarizer

- [x] 4.1 สร้าง `luma_core/context_summarizer.py`
- [x] 4.2 Parse rules from markdown files
  - [x] Extract MUST/SHOULD/DON'T rules
  - [x] Extract project-specific reminders
- [x] 4.3 summarize_rules() function
- [x] 4.4 Display on issue selection
- [ ] 4.5 (Optional) AI-powered summarization

---

## Phase 5: UI Upgrade

- [x] 5.1 Redesign main menu in `main.py`
  - [x] State-aware header
  - [x] Active task display
  - [x] Next step recommendation
- [x] 5.2 Progress indicator (Emoji based)
- [x] 5.3 Color-coded status

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
- [x] UI แสดง Active Task
- [ ] มี `.luma_rules.json` สำหรับ JarWise projects
- [ ] Tests pass
