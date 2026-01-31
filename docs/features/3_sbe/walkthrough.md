# SBE Feature Implementation Walkthrough

## Summary

เพิ่มฟีเจอร์ **SBE (Specification by Example)** ให้ Luma v1.1.0

---

## Changes Made

### New Files

| File | Description |
|------|-------------|
| `luma_core/sbe.py` | Core module: `Scenario`, `SBESpec` dataclasses, parse/validate/generate |
| `luma_core/agents/sbe_agent.py` | AI-powered SBE generator using LLM |
| `docs/templates/sbe_template.md` | Template สำหรับ SBE format |
| `tests/test_sbe.py` | Unit tests (9 tests) |

### Modified Files

| File | Changes |
|------|---------|
| `luma_core/actions.py` | Added `action_generate_sbe()` |
| `main.py` | Added menu option "S" |
| `README.md` | Version 1.1.0, added SBE to docs |
| `CHANGELOG.md` | Added 1.1.0 entry |
| `VERSION` | Bumped to 1.1.0 |

---

## Test Results

```
✅ 9/9 passed (0.01s)
```

---

## Usage

1. รัน `python main.py`
2. Select Issue (Option 2)
3. กด **S** เพื่อ Generate SBE Specs
4. Output: `docs/features/xxx/specs/sbe_issue-N.md`
