# Implementation Plan: Headless CLI Expansion & First-Class Issue Management

> **Refers to**: [Spec: Headless CLI Expansion & First-Class Issue Management](./spec.md)
> **Status**: Draft
> **Owner**: Senior Software Architect

## 1. Architecture & Design
แผนงานนี้มุ่งเน้นการย้าย Logic สำคัญออกจาก Interactive Loop ของ `main.py` ไปยัง Modular Actions ใน `luma_core/actions/` เพื่อให้สามารถเรียกใช้ได้ทั้งจาก UI และ Headless Mode ผ่าน JSON Contract

### Component View
- **Modified Components**:
    - `main.py`: เพิ่มการรองรับ Argument `--action` และ `--params` สำหรับ Headless mode
    - `luma_core/state_manager.py`: เพิ่มความสามารถในการจัดการ Workflow Checkpoints สำหรับการ Resume
    - `luma_core/github_client.py`: เพิ่ม Method สำหรับการสร้าง Issue พร้อม Template `## Related`
- **New Components**:
    - `luma_core/actions/create_issue.py`: Action สำหรับการสร้าง GitHub Issue (First-class)
    - `luma_core/actions/select_issue.py`: Action สำหรับการเลือก Issue และ Bootstrap branch (Refactored จากเดิมที่อยู่ใน `main.py`)
- **Dependencies**: 
    - `gh` CLI: ต้องติดตั้งและ Auth เรียบร้อย

### Data Model Changes
```python
# เพิ่มสถานะใน LumaState เพื่อรองรับ Checkpoints
class LumaState:
    phase: str  # idle, selecting, coding, reviewing, etc.
    current_issue_id: Optional[int]
    current_branch: Optional[str]
    checkpoint_data: Dict[str, Any]  # ข้อมูลชั่วคราวระหว่างรัน Workflow
    last_headless_action: Optional[str]
```

---

## 2. Step-by-Step Implementation

### Step 1: First-Class Issue Creation (#42)
สร้างโครงสร้างพื้นฐานสำหรับการสร้าง Issue ใหม่ที่รองรับทั้ง Interactive และ Headless
- **Docs**: อัปเดต `README.md` เกี่ยวกับคำสั่ง `create_issue`
- **Code**: 
    - สร้าง `luma_core/actions/create_issue.py` โดยมี `run_interactive()` และ `run_headless()`
    - เพิ่ม `GitHubClient.create_issue(title, body, labels)` ใน `luma_core/github_client.py`
    - บังคับใส่ `## Related` ใน Body หากไม่มีให้ใช้ Default template
- **Tests**: `tests/test_action_create_issue.py` (Verify JSON output และการสร้าง Issue จริงผ่าน Mock GitHub Client)

### Step 2: Headless Issue Selection & Bootstrap (#40)
ย้าย Logic การเลือก Issue จาก Kanban และการสร้าง Branch มาอยู่ใน Modular Action
- **Docs**: อัปเดต CLI help สำหรับ `select_issue --id <id>`
- **Code**:
    - สร้าง `luma_core/actions/select_issue.py`
    - ย้าย Logic การสร้าง Branch naming convention (`feat/ISSUE_NUMBER-summary`) มาไว้ที่นี่
    - อัปเดต `LumaState` ทันทีหลังจาก Bootstrap สำเร็จเป็นสถานะ `coding`
- **Tests**: `tests/test_action_select_issue.py` (Red -> Green -> Refactor)
    - **Red**: เรียก `select_issue` แบบ headless แล้วเช็คว่า branch ถูกสร้างและ state เปลี่ยนหรือไม่
    - **Green**: Implement logic ใน action และเชื่อมต่อกับ `main.py`

### Step 3: Resumable Headless Guided Workflow (#41)
ทำให้ "Auto Full Workflow" สามารถรันผ่าน Headless และบันทึกสถานะได้
- **Docs**: เอกสารอธิบายการใช้ `--resume` flag
- **Code**:
    - ปรับปรุง `luma_core/workflow.py` หรือ Action ที่เกี่ยวข้องให้รองรับการอ่าน `checkpoint_data`
    - ใน Headless mode ทุกครั้งที่จบ Phase ให้ Print JSON state ปัจจุบันออกมาเพื่อให้ภายนอกเก็บไว้
- **Tests**: `tests/test_action_guided_workflow_resume.py`
    - จำลองสถานะ `coding` ในไฟล์ state แล้วเรียก `auto_workflow` เพื่อดูว่าข้ามไป `reviewing` หรือไม่

### Step 4: Headless CLI Contract Expansion in `main.py`
ขยาย `main.py` ให้เป็น Router ที่สมบูรณ์สำหรับ Headless actions
- **Code**:
    - เพิ่ม CLI arguments: `--action`, `--id`, `--title`, `--body`, `--resume`
    - ใช้ `RedirectStdout` (หรือ Wrapper) เพื่อให้แน่ใจว่า Action output มีเพียง JSON เท่านั้น
- **Tests**: `tests/test_main_headless_cli.py` (Integration test รัน subprocess `python main.py --headless ...`)

---

## 3. Verification Plan

### Automated Tests
- [ ] **Unit Tests**:
    - `pytest tests/test_action_create_issue.py`
    - `pytest tests/test_action_select_issue.py`
- [ ] **Integration Tests**:
    - ทดสอบการรันแบบ Headless และใช้ `json.loads()` ตรวจสอบ STDOUT
    - ทดสอบ State consistency ใน `.luma_state.json` หลังจบแต่ละ Action

### Manual Verification
- [ ] **Interactive Test**: รัน `python main.py` แล้วเลือกเมนู "Create Issue" ใหม่ (เมนู 4) และ "Select Issue" (เมนู 2)
- [ ] **Headless Test**: 
    - `python main.py --headless --action select_issue --id 123`
    - `python main.py --headless --action create_issue --title "Test Issue" --body "Details ## Related: #1"`
    - `python main.py --headless --action auto_workflow --resume` (เมื่อมีสถานะค้างอยู่)

---
> **Note**: การจัดการกับ `input()` ในโหมด Headless จะใช้การ Check `sys.stdin.isatty()` หากไม่ใช่ TTY และโค้ดพยายามเรียก Input จะต้อง Raise Error หรือใช้ Default Value ทันทีเพื่อป้องกันโปรแกรมค้าง (Hanging)