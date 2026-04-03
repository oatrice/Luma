# Specification: Portable Dotfiles Bootstrap for Shared AI Memory and Global Agents

> Status: Implemented
> Issue: [#39](https://github.com/oatrice/Luma/issues/39)
> Last Updated: 2026-04-03

## 1. Goal

สร้าง template repo สำหรับจัดเก็บ shared AI memory และ global vendor-specific agent files แบบ portable เพื่อให้:

- ย้ายเครื่องได้ง่าย
- ลด rule drift ระหว่าง Codex / Gemini
- review และ version files เหล่านี้ได้ผ่าน Git

## 2. Delivered Scope

feature นี้ส่งมอบ “template repo scaffold” ภายใต้ [docs/templates/dotfiles-repo](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo) ไม่ใช่การ provision external repository อัตโนมัติ

ไฟล์ที่อยู่ใน scope:

- `README.md`
- `AGENTS.md`
- `.gitignore`
- `manifest.json`
- `scripts/_shared.py`
- `scripts/install.py`
- `scripts/capture.py`
- `home/.ai-shared-memory.md`
- `home/.codex/AGENTS.md`
- `home/.gemini/GEMINI.md`

## 3. Functional Requirements

- ต้องมี template สำหรับ `~/.ai-shared-memory.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`
- `scripts/install.py` ต้องติดตั้งไฟล์จาก template repo ลง home directory ได้
- default install mode ต้องเป็น symlink
- `scripts/install.py --copy` ต้อง copy เป็นไฟล์ปกติแทน symlink ได้
- ถ้ามีไฟล์เดิมอยู่และไม่ใช่ managed link เดิม ต้อง backup ก่อน overwrite
- `scripts/capture.py` ต้องดึงไฟล์จากเครื่องกลับเข้า template repo ได้
- vendor-specific files ต้องอ้าง shared memory ผ่าน `~/.ai-shared-memory.md`

## 4. Non-Functional Requirements

- Portable: ห้ามพึ่ง absolute path แบบผูกกับ user เดียว
- Additive-only: feature นี้ต้องไม่กระทบ runtime workflow เดิมของ Luma
- Maintainable: mapping source/target ต้องไม่กระจาย hardcode หลายจุด

## 5. Specification by Example

### Scenario A: Install แบบ symlink

Given มี template repo อยู่แล้วภายใต้ `docs/templates/dotfiles-repo`  
When รัน:

```bash
python3 scripts/install.py --repo-root "$PWD"
```

Then

- `~/.ai-shared-memory.md` ถูกสร้างเป็น symlink ไปยัง `home/.ai-shared-memory.md`
- `~/.codex/AGENTS.md` ถูกสร้างเป็น symlink ไปยัง `home/.codex/AGENTS.md`
- `~/.gemini/GEMINI.md` ถูกสร้างเป็น symlink ไปยัง `home/.gemini/GEMINI.md`

### Scenario B: Install แบบ copy พร้อม backup

Given มีไฟล์เดิมอยู่ใน home directory  
When รัน:

```bash
python3 scripts/install.py --copy --repo-root "$PWD"
```

Then

- ไฟล์เดิมถูกย้ายเป็น `.bak` หรือ `.bak.N`
- ไฟล์ใหม่ถูก copy จาก source
- target file ไม่เป็น symlink

### Scenario C: Capture กลับเข้า repo

Given ผู้ใช้แก้ `~/.ai-shared-memory.md` หรือ global agent files บนเครื่อง  
When รัน:

```bash
python3 scripts/capture.py --repo-root "$PWD"
```

Then

- การเปลี่ยนแปลงถูก copy กลับมาที่ `home/...` ใน template repo

### Scenario D: Portable shared-memory reference

Given เปิดดู `home/.codex/AGENTS.md` หรือ `home/.gemini/GEMINI.md`  
Then

- ต้องพบ `~/.ai-shared-memory.md`
- ต้องไม่พบ `/Users/oatrice/.ai-shared-memory.md`

## 6. Out of Scope

- สร้าง GitHub repo ใหม่อัตโนมัติ
- sync เข้า dotfiles repo จริงผ่าน Git command อัตโนมัติ
- เปลี่ยน Luma runtime ให้ใช้ global files แทน repo-local files
- เพิ่ม headless actions สำหรับ workflow อื่น

## 7. Verification Contract

Automated:

- [tests/test_dotfiles_repo_template.py](/Users/oatrice/Software-projects/Luma/tests/test_dotfiles_repo_template.py)

Manual:

- symlink install
- copy install พร้อม backup
- capture กลับเข้า repo
- ตรวจ portable references ใน vendor files
