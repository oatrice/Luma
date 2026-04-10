# Development Workflow Guide

> คู่มือการพัฒนา Luma สำหรับ Developers และ AI Agents

---

## 🚀 Quick Start

```bash
# 1. Clone และเข้าไปใน project
cd /path/to/Luma

# 2. Install dependencies
pip install -r requirements.txt
pip install pytest ruff  # dev tools

# 3. Install Git hooks
bash scripts/install-hooks.sh

# 4. ตั้งค่า environment
cp .env.example .env
# แก้ไข .env ใส่ API keys ที่จำเป็น

# 5. Run tests
python -m pytest tests/ -v
```

---

## 🔄 Git Hooks

Project นี้มี Git hooks สำหรับตรวจสอบ code quality อัตโนมัติ

### Pre-commit Hook

รันอัตโนมัติเมื่อ `git commit`:
- ✅ Ruff linting (ignore E501,F401)
- ✅ Pytest บน staged files

```bash
# ติดตั้ง hooks
bash scripts/install-hooks.sh

# Skip hooks (ถ้าจำเป็น)
git commit --no-verify -m "message"
```

### Pre-push Hook

รันอัตโนมัติเมื่อ `git push`:
- ✅ Ruff linting
- ✅ Full test suite (`pytest tests/ -v`)
- ✅ Version consistency check (VERSION vs CHANGELOG.md)

```bash
# Skip hooks (ถ้าจำเป็น)
git push --no-verify
```

### Scripts ที่เกี่ยวข้อง

| Script | Purpose |
|--------|---------|
| `scripts/pre-commit` | Hook script สำหรับ commit |
| `scripts/pre-push` | Hook script สำหรับ push |
| `scripts/install-hooks.sh` | ติดตั้ง hooks ใน `.git/hooks/` |

---

## 🧪 Testing

### Run All Tests

```bash
python -m pytest tests/ -v
```

### Run Specific Test

```bash
python -m pytest tests/test_feature_23_header_enhancement.py -v
```

### Run with Coverage

```bash
python -m pytest tests/ --cov=luma_core --cov-report=html
```

---

## 🔧 Code Quality

### Linting with Ruff

```bash
# Check
ruff check . --ignore E501,F401

# Auto-fix
ruff check . --ignore E501,F401 --fix
```

Ignored rules:
- `E501`: Line too long
- `F401`: Unused imports

---

## 📋 Development Checklist

ก่อน commit ควรตรวจสอบ:

- [ ] Tests pass (`pytest tests/ -x`)
- [ ] No linting errors (`ruff check .`)
- [ ] Version ตรงกัน (VERSION, CHANGELOG.md)
- [ ] เอกสารอัปเดตแล้ว (ถ้าจำเป็น)

---

## 🐛 Troubleshooting

### Hook ไม่ทำงาน

```bash
# ตรวจสอบว่า hooks ถูกติดตั้ง
ls -la .git/hooks/pre-commit
ls -la .git/hooks/pre-push

# Re-install
bash scripts/install-hooks.sh
```

### Tests fail บางอัน

```bash
# Run แบบ stop at first failure
python -m pytest tests/ -x -v

# Run เฉพาะ test ที่ fail
python -m pytest tests/test_specific.py::test_name -v
```

### Worktree issues

```bash
# สำหรับ git worktree, hooks อยู่ที่ main repo
# ต้องรัน install-hooks.sh ในแต่ละ worktree
```

---

## 📚 Related Docs

- [Constitution](constitution.md) - Project rules และ standards
- [AI_GUIDE](AI_GUIDE.md) - AI behavior guidelines
- [manual_verification_guide](manual_verification_guide.md) - Manual testing

---

*Last updated: 2026-04-10*
