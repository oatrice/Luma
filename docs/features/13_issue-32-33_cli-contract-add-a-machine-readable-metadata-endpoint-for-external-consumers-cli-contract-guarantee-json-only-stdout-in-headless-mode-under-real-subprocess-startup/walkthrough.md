# Walkthrough: CLI Metadata Endpoint และ JSON-only stdout contract

## สรุปสิ่งที่ implement

งาน batch นี้เพิ่ม contract สำหรับ external consumer ให้ Luma ใช้งานแบบเชื่อถือได้มากขึ้นใน 2 ด้าน:

1. เพิ่ม metadata endpoint แบบ machine-readable ผ่าน `--meta --json`
2. ทำให้ headless `--json` mode ใช้ `stdout` เป็นช่อง machine-readable อย่างเดียว แม้ใน real subprocess startup

implementation จริงอยู่หลัก ๆ ใน `main.py` โดย reuse helper เดิมจาก `luma_core.tools` สำหรับ version และ git info

## Contract ที่ได้จริง

### Metadata mode

คำสั่ง:

```bash
python3 main.py --meta --json
```

ผลลัพธ์บน `stdout`:

```json
{
  "status": "success",
  "mode": "metadata",
  "result": {
    "version": "1.6.0",
    "git_commit": "7346548185cd82dd8bea308f65015a256bc50646",
    "dirty": true,
    "contract_version": "2.0",
    "supported_actions": ["code_review"],
    "python_version": "3.9.6"
  }
}
```

### Headless JSON mode

คำสั่งตัวอย่าง:

```bash
python3 main.py --auto --action invalid_action --json --project 12
```

ผลลัพธ์ที่คาดหวัง:

- `stdout` เป็น JSON parse ได้เสมอ
- `stderr` อาจมี warnings หรือ diagnostics ได้
- exit code ต้องสะท้อนผลลัพธ์จริงของ command

## Manual Verify Scenarios

### Scenario 1: Metadata success path

รัน:

```bash
python3 main.py --meta --json
```

ตรวจว่า:

- `stdout` parse เป็น JSON ได้
- payload มี `status=success`
- มี fields ครบ: `version`, `git_commit`, `dirty`, `contract_version`, `supported_actions`, `python_version`
- `version` ควรตรงกับไฟล์ `VERSION`

### Scenario 2: Metadata invalid combination

รัน:

```bash
python3 main.py --meta --json --action code_review
```

ตรวจว่า:

- exit code เป็น `2`
- `stdout` เป็น JSON error payload
- message คือ `--meta cannot be combined with --action or --auto.`

### Scenario 3: Real subprocess startup does not corrupt stdout

รัน:

```bash
python3 - <<'PY'
import json
import subprocess
import sys

cmd = [
    sys.executable,
    "main.py",
    "--auto",
    "--action",
    "invalid_action",
    "--json",
    "--project",
    "12",
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("returncode:", res.returncode)
print("stdout:", res.stdout)
print("stderr:", res.stderr)
json.loads(res.stdout)
print("stdout JSON parse: OK")
PY
```

ตรวจว่า:

- `json.loads(res.stdout)` ผ่าน
- ไม่มีข้อความ human-readable ปนก่อน JSON ใน `stdout`
- `stderr` จะมี warning ได้ แต่ต้องไม่กระทบ `stdout`

### Scenario 4: Interactive mode regression check

รัน:

```bash
python3 main.py
```

ตรวจว่า:

- เมนู interactive ยังขึ้นตามปกติ
- เลือกออกจากโปรแกรมได้ตามปกติ
- ไม่มีการบังคับเข้า headless mode โดยไม่ได้ใส่ flags

## Automated Verification ที่รันแล้ว

รันคำสั่งนี้แล้วผ่าน:

```bash
python3 -m pytest tests/test_main_headless_cli.py tests/test_main_global_config.py tests/test_main_refresh_state.py tests/test_action_code_review.py -q
```

ผลลัพธ์:

- `19 passed`

## หมายเหตุ

- warning จาก Python environment หรือ third-party libraries ยังอาจไปที่ `stderr` ได้ ซึ่งเป็นพฤติกรรมที่ยอมรับได้ใน contract นี้
- จุดสำคัญคือ `stdout` ของ machine-readable mode ต้อง parse ได้เสมอและไม่มี human-readable text ปน
