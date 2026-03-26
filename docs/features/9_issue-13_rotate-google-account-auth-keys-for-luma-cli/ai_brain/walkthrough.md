# Walkthrough: Hybrid Credential Rotation (Issue #13)

## สรุป
ระบบ Hybrid Credential Rotation สำหรับ Luma CLI — ช่วยให้หมุนเวียน Google API Keys และ Gemini CLI OAuth Profiles โดยอัตโนมัติเมื่อเจอ Rate Limit (429)

## ไฟล์ที่เปลี่ยนแปลง

| ไฟล์ | การเปลี่ยนแปลง |
|------|---------------|
| `luma_core/credential_manager.py` | **[NEW]** Core rotation logic |
| `luma_core/config.py` | เพิ่ม `GOOGLE_API_KEYS` และ `GEMINI_CLI_PROFILES` |
| `luma_core/llm.py` | Integrate CredentialManager เข้า `GeminiCLIModel._generate()` |
| `tests/test_credential_manager.py` | **[NEW]** Unit tests (TDD Red → Green) |

## TDD Cycle

### 🟥 RED → เขียน 17 tests ก่อนมี implementation
```
ModuleNotFoundError: No module named 'luma_core.credential_manager'
```

### 🟢 GREEN → สร้าง `credential_manager.py`
```
17 passed in 1.12s
```

### ✨ REFACTOR → Integrate เข้า llm.py + guard `Optional[CredentialManager]`
```
27 passed in 2.04s
```

## วิธีตั้งค่า (`.env`)

```bash
# API Keys จากต่างบัญชี Google (แชร์โควต้าถ้าอยู่ Project เดียวกัน!)
GOOGLE_API_KEY=AIzaSy...          # legacy key (ยังรองรับ)
GOOGLE_API_KEYS=key_A,key_B,key_C  # หลายคีย์จากต่างบัญชี

# OAuth Profiles (โฟลเดอร์ใน ~/.luma/profiles/)
GEMINI_CLI_PROFILES=account_1,account_2
```

> [!IMPORTANT]
> API Keys จาก Google Account / GCP Project เดียวกัน **แชร์โควต้ากัน** — ต้องใช้คีย์จากต่างบัญชีเท่านั้นจึงจะได้ประโยชน์

## วิธีตั้ง OAuth Profile

```bash
# Login บัญชีที่ 1 แยกโปรไฟล์
mkdir -p ~/.luma/profiles/account_1
env HOME=~/.luma/profiles/account_1 gemini  # จะเปิด browser ให้ login

# Login บัญชีที่ 2
mkdir -p ~/.luma/profiles/account_2
env HOME=~/.luma/profiles/account_2 gemini
```

## พฤติกรรมของระบบ

```
Pool: [key_A (API_KEY), key_B (API_KEY), account_1 (OAUTH_PROFILE)]

Round 1: key_A → OK ✅
Round 2: key_A → 429 ❌ → mark cooldown 5min → switch → key_B → OK ✅
Round 3: key_B → 429 ❌ → switch → account_1 → OK ✅
Round 4: key_A ยังติด Cooldown → account_1 → ...
Round N: ทุกตัวติด Cooldown → แจ้งผู้ใช้ให้เพิ่ม key ใหม่
```
