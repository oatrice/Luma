# Walkthrough: Headless CLI Contract for External Callers (Issue #27)

## สรุป
Feature นี้เพิ่ม headless CLI contract ให้ `main.py` ของ Luma เพื่อให้ external callers เช่น Zenith เรียกใช้งานแบบ programmatic ได้ผ่าน flags `--auto`, `--action`, `--json`, และ `--project`

ผลลัพธ์ที่ได้คือ:
- เรียก action แบบไม่เข้า interactive menu ได้
- คืนผลลัพธ์เป็น JSON บน stdout สำหรับ success และ error
- ใช้ exit code ได้สม่ำเสมอสำหรับ external automation
- Zenith สามารถ verify เส้นทาง `Coder -> Luma -> OpenShell` ได้จริงแล้ว

## ไฟล์ที่เกี่ยวข้อง

| ไฟล์ | การเปลี่ยนแปลง |
|------|---------------|
| `main.py` | เพิ่ม headless argument parsing และ execution path |
| `luma_core/actions/quality_actions.py` | รองรับ action ที่เรียกจาก headless flow |
| `tests/test_main_headless_cli.py` | เพิ่ม tests สำหรับ headless CLI contract |
| `tests/test_action_code_review.py` | ยืนยันพฤติกรรมของ `code_review` action |
| `tests/test_reviewer_agent.py` | ยืนยันว่า reviewer ส่ง code changes เข้า manual verification prompt จริง |
| `luma_core/agents/reviewer.py` | แก้ prompt ของ test suggestions ให้ฝัง diff/context ของ changes จริง |

## พฤติกรรมที่ verify ได้แล้ว

### 1. Happy Path จาก Zenith

รันจาก repo Zenith:

```bash
python3 scripts/run_coder_luma_openshell_smoke.py \
  --luma-path ../Luma \
  --openshell-binary /Users/oatrice/Public/openshell/target/release/openshell \
  --project 1
```

ผลที่ยืนยันได้:
- `wrapper`: success
- `openshell`: success
- `coder_luma`: success
- JSON response กลับมาครบและ parse ได้

### 2. Headless Success Path ของ Luma

```bash
python3 main.py --auto --action code_review --json --project 1
```

ผลที่ยืนยันได้:
- action รันโดยไม่เข้า interactive menu
- process จบด้วย exit code `0`
- stdout เป็น JSON parseable
- response มีฟิลด์ `status`, `action`, `project`, `result`

### 3. Invalid Action Path

```bash
python3 main.py --auto --action invalid_action --json --project 1
```

ผลที่ยืนยันได้:
- process จบด้วย non-zero exit code
- stdout เป็น JSON parseable
- response error มี `status: "error"`
- `action` และ `project` ถูก echo กลับมาเพื่อให้ external caller trace ได้

### 4. Stdout / Stderr Separation

ตรวจด้วย subprocess แบบจับแยก stream:

```bash
python3 -c "import subprocess, json; cmd=['python3','../Luma/main.py','--auto','--action','code_review','--json','--project','1']; p=subprocess.run(cmd,capture_output=True,text=True); print('STDOUT>>>'); print(p.stdout); print('STDERR>>>'); print(p.stderr); print('RC>>>', p.returncode)"
```

ผลที่ยืนยันได้:
- stdout เป็น JSON ล้วน
- warning และ runtime logs ไปอยู่ stderr
- external wrapper อย่าง Zenith จึง parse stdout ได้ตรงไปตรงมา

### 5. Interactive Regression Check

```bash
python3 main.py --project 1
```

ผลที่ยืนยันได้:
- Luma ยังเข้า interactive mode ตามเดิม
- แปลว่า headless flow ใหม่ไม่ได้ทำให้ interactive workflow เดิมพัง

## Test Results

### Targeted Tests

```bash
python3 -m pytest -q tests/test_main_headless_cli.py tests/test_action_code_review.py tests/test_reviewer_agent.py
```

ผลลัพธ์ที่ verify ได้:

```text
12 passed, 2 warnings in 0.76s
```

### Reviewer Fix Verification

จุดที่แก้ใน `luma_core/agents/reviewer.py` คือเปลี่ยน prompt สำหรับ test suggestions ให้เป็น f-string เพื่อฝัง `changes` จริงลงไปใน manual verification prompt

ผลที่ verify ได้:
- `tests/test_reviewer_agent.py` ผ่าน
- `code_review.md` รอบใหม่มี manual verification steps ที่สอดคล้องกับ code changes มากขึ้น

## Manual Verification Scenarios

### Scenario A: External caller เรียก `code_review` สำเร็จ
1. รัน `python3 main.py --auto --action code_review --json --project 1`
2. ตรวจว่าไม่มี interactive prompt
3. ตรวจว่า stdout เป็น JSON success
4. ตรวจว่า exit code เป็น `0`

### Scenario B: External caller เรียก action ที่ไม่มีอยู่
1. รัน `python3 main.py --auto --action invalid_action --json --project 1`
2. ตรวจว่า stdout เป็น JSON error
3. ตรวจว่า exit code ไม่เป็น `0`
4. ตรวจว่า message อ่านรู้เรื่องและชี้ชัดว่า action ไม่พบ

### Scenario C: Zenith smoke verification
1. รัน smoke script จาก repo Zenith
2. ตรวจว่า `wrapper`, `openshell`, `coder_luma` ผ่านทั้งหมด
3. ตรวจว่า response ของ Luma ยัง parse ได้จากฝั่ง Zenith

### Scenario D: Interactive flow เดิมยังใช้ได้
1. รัน `python3 main.py --project 1`
2. ตรวจว่าหน้าจอ interactive menu ยังขึ้นตามปกติ
3. ออกจากโปรแกรมได้โดยไม่เกิด exception

## Known Notes

- ปัจจุบันยังมี warnings ของ Python 3.9 และ `urllib3`/`google.api_core` แสดงบน stderr
- warnings เหล่านี้ไม่ทำให้ headless JSON contract พัง เพราะ stdout ยังสะอาด
- `python3 -m pytest -q` ที่ root ของ repo อาจยังล้มตอน collection จากไฟล์ helper บางตัวเช่น `fix_test.py` และ `patch_test.py`
- สำหรับงานของ feature นี้ ให้ยึด targeted suite ใต้ `tests/` ที่เกี่ยวข้องเป็นหลัก

## สรุปสุดท้าย

Issue #27 ปิด pain point หลักของ external integration ได้แล้ว:
- Zenith เรียก Luma แบบ headless ได้จริง
- success และ error contract อยู่ใน JSON ที่ parse ได้
- interactive mode เดิมยังไม่แตก
- reviewer test suggestion ใช้ code changes จริงเป็น context แล้ว
