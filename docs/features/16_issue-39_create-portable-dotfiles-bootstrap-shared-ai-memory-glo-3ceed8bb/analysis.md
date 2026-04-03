# Analysis: Portable Dotfiles Bootstrap for Shared AI Memory and Global Agents

## ข้อมูลพื้นฐาน

| รายการ | รายละเอียด |
|---|---|
| Issue | [#39](https://github.com/oatrice/Luma/issues/39) |
| วันที่ | 2026-04-03 |
| สถานะ | Implemented |
| ขอบเขต | Dotfiles bootstrap template, install/capture scripts, portable global-agent references |

## ปัญหาที่ต้องแก้

ตอนนี้ shared AI memory และ global agent instructions ถูกเก็บเป็นไฟล์ machine-local เช่น `~/.ai-shared-memory.md`, `~/.codex/AGENTS.md`, และ `~/.gemini/GEMINI.md` ทำให้มี 3 ปัญหาหลัก:

1. ย้ายเครื่องแล้วย้าย context ตามได้ยาก
2. rules ระหว่าง Codex / Gemini / vendor อื่น drift ได้ง่าย
3. ไม่มี source of truth ที่ commit/review ได้เหมือน code ปกติ

## สิ่งที่ implement จริง

รอบนี้ไม่ได้สร้าง Git repo ภายนอกให้อัตโนมัติ แต่สร้าง “template repo scaffold” ไว้ใน Luma ที่ [docs/templates/dotfiles-repo](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo) เพื่อใช้เป็นต้นแบบสำหรับย้ายไป repo จริงในภายหลัง

องค์ประกอบหลักที่เพิ่ม:

- `home/.ai-shared-memory.md`
- `home/.codex/AGENTS.md`
- `home/.gemini/GEMINI.md`
- `manifest.json`
- `scripts/_shared.py`
- `scripts/install.py`
- `scripts/capture.py`
- `README.md`
- `AGENTS.md`

## การตัดสินใจเชิงออกแบบ

### 1. ใช้ manifest เป็น source of truth สำหรับ mapping

ไฟล์ [manifest.json](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo/manifest.json) เป็นตัวบอกว่าไฟล์ใดใน template repo ต้องไปอยู่ตรงไหนใน home directory ทำให้ `install.py` และ `capture.py` ใช้ mapping ชุดเดียวกัน ลดการ hardcode ซ้ำ

### 2. install ใช้ symlink เป็น default

`scripts/install.py` ติดตั้งแบบ symlink เป็น default เพื่อให้ repo template เป็น source of truth เดียว ถ้าต้องการไฟล์จริงค่อยใช้ `--copy`

### 3. backup ก่อน overwrite เฉพาะกรณี target ไม่ได้เป็น managed link เดิม

ถ้า target เป็นไฟล์ปกติหรือ symlink ที่ไม่ตรง source เดิม ระบบจะ backup ก่อน แล้วค่อย copy/link ทับ เพื่อลดความเสี่ยงข้อมูลหาย

### 4. vendor files ต้องอ้าง shared memory แบบ portable

ทั้ง [home/.codex/AGENTS.md](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo/home/.codex/AGENTS.md) และ [home/.gemini/GEMINI.md](/Users/oatrice/Software-projects/Luma/docs/templates/dotfiles-repo/home/.gemini/GEMINI.md) ถูกแก้ให้ชี้ไปที่ `~/.ai-shared-memory.md` แทน absolute path แบบ `/Users/oatrice/...`

## สิ่งที่ตั้งใจไม่ทำในรอบนี้

- ไม่สร้าง GitHub repo ใหม่ให้อัตโนมัติ
- ไม่เพิ่ม logic ใน Luma runtime ให้โหลด global dotfiles เหล่านี้มาแทน repo-local `AGENTS.md`/`GEMINI.md`
- ไม่จัดเก็บ secrets หรือ `.env` ลงใน template repo
- ไม่ขยาย headless contract เพื่อจัดการ issue selection / guided workflow / issue creation

เรื่องเหล่านี้ถูกแยกเป็น follow-up แล้ว:

- [#40](https://github.com/oatrice/Luma/issues/40) headless Select Issue
- [#41](https://github.com/oatrice/Luma/issues/41) machine-readable guided workflow
- [#42](https://github.com/oatrice/Luma/issues/42) first-class issue creation
- [#43](https://github.com/oatrice/Luma/issues/43) Telegram step-progress updates
- [#44](https://github.com/oatrice/Luma/issues/44) doc-quality validation for generated planning artifacts

## ผลกระทบต่อระบบ

ผลกระทบหลักอยู่ที่ asset ใหม่ใน `docs/templates/dotfiles-repo/` และ test coverage ใหม่ใน [tests/test_dotfiles_repo_template.py](/Users/oatrice/Software-projects/Luma/tests/test_dotfiles_repo_template.py)

รอบนี้ไม่ได้แก้ runtime path resolution ของ Luma core เพราะ feature นี้เป็นการเตรียม “portable source of truth” สำหรับไฟล์ global ข้ามเครื่อง ไม่ใช่การเปลี่ยน project-context loading ภายใน repo

## ความเสี่ยงที่ยังเหลือ

1. ผู้ใช้อาจสับสนระหว่าง “template repo ใน Luma” กับ “dotfiles repo จริงที่ clone ใช้งานข้ามเครื่อง”
2. ถ้าแก้ไฟล์ผ่าน symlink ตรง ๆ แล้วไม่รู้ตัว อาจเท่ากับแก้ source file ใน repo template ไปด้วย
3. ถ้ามี vendor ใหม่เพิ่มในอนาคต ต้องแก้ `manifest.json` และ scripts ให้พร้อมกัน

## วิธีลดความเสี่ยง

- ระบุใน README ชัดว่า template นี้ต้องถูก clone/copy ไปเป็น repo จริง
- ใช้ `--copy` เมื่อต้องการไฟล์ local ที่แยกจาก source of truth
- ใช้ test บังคับให้โครง template และ portable references ครบ

## สรุป

implementation ปัจจุบันแก้ pain point เรื่อง portability และ cross-vendor drift ได้ในระดับ “พร้อมใช้งานเป็น starter kit” และพร้อมแตกไปเป็น dotfiles repo จริงบนเครื่องใหม่ โดยไม่กระทบ interactive workflow เดิมของ Luma
