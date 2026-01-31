# SBE (Specification by Example) Feature Implementation

เพิ่มฟีเจอร์ให้ Luma สามารถ **สร้างและอ่าน** Specification by Example (SBE) specs ในรูปแบบ Markdown โดย integrate เข้ากับ pre-coding workflow

---

## Proposed Changes

### Core Module

#### [NEW] [sbe.py](file:///Users/oatrice/Software-projects/Luma/luma_core/sbe.py)

Core SBE logic module:

```python
# Key Functions:
def generate_sbe_from_issue(issue_data: dict, output_dir: str) -> str
def parse_sbe_spec(filepath: str) -> dict  
def validate_sbe_spec(spec: dict) -> bool
```

---

### SBE Agent

#### [NEW] [sbe_agent.py](file:///Users/oatrice/Software-projects/Luma/luma_core/agents/sbe_agent.py)

AI-powered SBE generator:

```python
def sbe_agent(state: AgentState) -> dict
    """
    1. รับ Issue data จาก state
    2. เรียก LLM เพื่อสร้าง SBE specs
    3. บันทึกเป็น Markdown ใน specs/ folder
    """
```

**Output Format (Markdown):**
```markdown
# SBE: [Feature Name]

## Feature: [Feature Title]

### Scenario: [Scenario Name]

**Given** [precondition]
**When** [action]  
**Then** [expected outcome]

### Examples

| Input | Expected |
|-------|----------|
| ...   | ...      |
```

---

### Template

#### [NEW] [sbe_template.md](file:///Users/oatrice/Software-projects/Luma/docs/templates/sbe_template.md)

Template file สำหรับ SBE specification format

---

### Integration

#### [MODIFY] [actions.py](file:///Users/oatrice/Software-projects/Luma/luma_core/actions.py)

เพิ่ม function ใหม่:
```python
def action_generate_sbe(state: LumaState, project: dict):
    """Generate SBE specs for current issue"""
```

---

#### [MODIFY] [main.py](file:///Users/oatrice/Software-projects/Luma/main.py)

เพิ่ม menu option ใหม่:
```python
MENU_ACTIONS = {
    ...
    "S": {"label": "📋 Generate SBE Specs", "valid_phases": [WorkflowPhase.CODING, WorkflowPhase.SELECTING]},
}
```

---

### Tests

#### [NEW] [test_sbe.py](file:///Users/oatrice/Software-projects/Luma/tests/test_sbe.py)

Unit tests สำหรับ core SBE functions:
- `test_parse_sbe_spec()`
- `test_validate_sbe_spec()`
- `test_generate_sbe_creates_file()`

---

## Verification Plan

### Automated Tests

```bash
# Run unit tests
cd /Users/oatrice/Software-projects/Luma
python -m pytest tests/test_sbe.py -v
```

### Manual Verification

1. **Start Luma CLI:**
   ```bash
   cd /Users/oatrice/Software-projects/Luma
   python main.py
   ```

2. **Select an Issue** (Menu option 2)

3. **Generate SBE** (Menu option S)

4. **ตรวจสอบ Output:**
   - ไฟล์ SBE ถูกสร้างใน `docs/features/xxx/specs/sbe_*.md`
   - Format ถูกต้องตาม template (Given/When/Then + Examples table)

---

> [!NOTE]
> เริ่มพัฒนาตาม TDD: Red → Green → Refactor
> จะเริ่มจากการเขียน failing tests ก่อน แล้วค่อย implement code
