# Walkthrough: Portable Dotfiles Bootstrap for Shared AI Memory and Global Agents

## สิ่งที่ feature นี้ทำ

รอบนี้เราไม่ได้สร้าง external dotfiles repo ให้ทันที แต่สร้าง “repo template” ไว้ใน Luma ที่ [docs/templates/dotfiles-repo](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo)

แนวคิดคือ:

1. เก็บ shared memory และ global vendor rules ไว้ในรูปแบบที่ commit/review ได้
2. ใช้ `install.py` เพื่อลงไฟล์ไปยัง home directory ของเครื่องใหม่
3. ใช้ `capture.py` เพื่อดึง local edits กลับเข้า repo template

## โครงสร้างหลัก

```text
docs/templates/dotfiles-repo/
├── README.md
├── AGENTS.md
├── .gitignore
├── manifest.json
├── home/
│   ├── .ai-shared-memory.md
│   ├── .codex/AGENTS.md
│   └── .gemini/GEMINI.md
└── scripts/
    ├── _shared.py
    ├── install.py
    └── capture.py
```

## วิธีใช้งานบนเครื่องใหม่

### แบบ symlink

```bash
python3 scripts/install.py --repo-root "$PWD"
```

ผลลัพธ์:

- home target จะชี้กลับมาที่ source file ใน repo
- เหมาะกับกรณีที่ต้องการ source of truth เดียว

### แบบ copy

```bash
python3 scripts/install.py --copy --repo-root "$PWD"
```

ผลลัพธ์:

- ถ้ามีไฟล์เดิมอยู่ จะ backup ก่อน
- target เป็นไฟล์ปกติ ไม่ใช่ symlink

## วิธีดึงไฟล์จากเครื่องกลับเข้า repo

```bash
python3 scripts/capture.py --repo-root "$PWD"
```

ใช้ตอน:

- มีการแก้ `~/.ai-shared-memory.md`
- หรือแก้ global `AGENTS.md` / `GEMINI.md` บนเครื่อง
- แล้วต้องการ sync กลับเข้า source of truth

## Manual Verify ที่ใช้จริงในรอบนี้

### 1. Install แบบ symlink

- copy template ไป `/tmp/luma-dotfiles-manual/repo`
- รัน `install.py`
- ตรวจว่าได้ symlink ครบ 3 ไฟล์

### 2. Install แบบ copy พร้อม backup

- ลบ symlink เดิม
- สร้างไฟล์ปกติปลอมใน home target
- รัน `install.py --copy`
- ตรวจว่าได้ `.bak`
- ตรวจว่า content ใหม่ตรงกับ source

### 3. ผลที่ต้องยืนยัน

- portable references ใช้ `~/.ai-shared-memory.md`
- ไม่มี absolute path แบบ `/Users/oatrice/...`
- source/target mapping ทำงานครบตาม manifest

## Follow-up ที่แยกออกไป

- [#40](https://github.com/oatrice/Luma/issues/40) headless Select Issue
- [#41](https://github.com/oatrice/Luma/issues/41) machine-readable guided workflow
- [#42](https://github.com/oatrice/Luma/issues/42) first-class issue creation
- [#43](https://github.com/oatrice/Luma/issues/43) Telegram step-progress updates
- [#44](https://github.com/oatrice/Luma/issues/44) doc-quality validation
