# LLM Fallback Chain & Model Selection

## Settings Menu (`O: ⚙️ Settings`)

```
Current Configuration:
  [1] LLM Provider:      gemini_cli
  [2] Agent CLI:         gemini_cli
  [3] Gemini CLI Model:  gemini-3-flash-preview
  [4] 🔙 Back
```

| ตัวเลือก | คืออะไร | ใช้ตอนไหน |
|----------|--------|----------|
| **[1] LLM Provider** | เลือก provider สำหรับ **Agent ภายใน Luma** (Analyst, Reviewer, Spec, Architect) ที่ใช้ LangChain เรียก LLM | สลับระหว่าง `gemini` (API), `openrouter`, `gemini_cli` (subprocess) |
| **[2] Agent CLI** | เลือก **CLI tool ภายนอก** ที่ Luma delegate task ไปให้ทำงาน (เช่น auto-coding) | สลับระหว่าง `gemini_cli` กับ `opencode` |
| **[3] Gemini CLI Model** | เลือก **model ที่ gemini CLI จะใช้** ผ่าน flag `-m` | สลับ model เมื่อติดลิมิต หรือต้องการ model ที่เร็ว/แรงกว่า |

> **ความแตกต่างสำคัญ**: [1] คือ provider ที่ Luma Agent ใช้เรียก LLM ผ่าน LangChain, [2] คือ CLI ภายนอกที่ Luma delegate task ให้, [3] คือ model ที่ gemini CLI ใช้จริงเวลารัน

---

## 1. Gemini CLI Model Selection (`.luma_global.json`)

ฟีเจอร์สลับ model ที่ใช้กับ `gemini` CLI — ค่าถูกจดจำข้ามเซสชัน

| Model | หมายเหตุ |
|-------|---------|
| `gemini-3-flash-preview` | ค่าเริ่มต้น, เร็ว |
| `gemini-3-pro-preview` | แรงสุด, ติดลิมิตง่าย |
| `gemini-2.5-pro` | stable |
| `gemini-2.5-flash` | เร็ว, quota สูง |
| `gemini-2.5-flash-lite` | เบาสุด |

```json
// .luma_global.json
{ "GEMINI_CLI_MODEL": "gemini-3-flash-preview" }
```

### Manual Verify: Gemini CLI Model

1. รัน `python3 main.py` → กด `O` (Settings)
2. กด `[3]` เลือก model ใหม่ เช่น `gemini-2.5-flash`
3. กด `[4]` กลับ → ตรวจ `.luma_global.json` ว่ามี `"GEMINI_CLI_MODEL": "gemini-2.5-flash"`
4. ปิดแล้วเปิด Luma ใหม่ → กด `O` อีกครั้ง → ค่าควรยังเป็น `gemini-2.5-flash` (จดจำข้ามเซสชัน)

---

## 2. LLM Fallback Chain (`.luma_dev.json`)

ระบบ auto-fallback ใน `luma_core/llm.py` — เมื่อ model fail ระบบสลับไปตัวถัดไปอัตโนมัติ  
**Index ที่สำเร็จล่าสุด** ถูกจำไว้ใน `.luma_dev.json` (ต่อโปรเจกต์)

### Fallback Chain Index → Model Mapping

เมื่อ `LLM_PROVIDER = "gemini_cli"` และ primary model มี `"pro"` ในชื่อ:

| Index | Provider | Model | หมายเหตุ |
|-------|----------|-------|---------|
| 0 | gemini_cli | `gemini-2.5-pro` (หรือ GEMINI_CODE_MODEL) | Primary |
| 1 | gemini_cli | `gemini-2.0-flash` | Internal fallback |
| 2 | gemini_cli | `gemini-2.5-flash-lite` | Lightweight fallback |
| 3 | gemini_cli | `auto` | CLI auto-select |
| 4 | gemini_cli | `gemini-2` | Alias |
| 5 | gemini_cli | `gemini-3` | Alias |
| 6 | openrouter | (default model) | Cross-provider (ถ้ามี API key) |
| 7 | gemini API | (default model) | Cross-provider (ถ้ามี API key) |

> **หมายเหตุ:** Index 6-7 จะมีหรือไม่ ขึ้นอยู่กับว่ามี `OPENROUTER_API_KEY` / `GOOGLE_API_KEY` ใน `.env`

### Auto-Recovery

- ถ้า fallback ถูกใช้นานกว่า **1 ชั่วโมง** → ระบบจะลอง primary model ใหม่อัตโนมัติ
- ถ้า **ทุก model fail** → reset กลับไป index 0

```json
// .luma_dev.json (ต่อโปรเจกต์)
{
  "FALLBACK_ACTIVE_INDEX": 2,
  "FALLBACK_LAST_RESET": 1741789200.0
}
```

### Manual Verify: Fallback Index

1. ลบ `.luma_dev.json` ในโปรเจกต์เป้าหมาย (ถ้ามี)
2. รัน Luma → เลือก Issue → ใช้ฟีเจอร์ที่เรียก LLM (เช่น Code Review)
3. ตรวจ `.luma_dev.json` → ควรมี `FALLBACK_ACTIVE_INDEX` เป็น 0 (primary สำเร็จ)
4. ถ้า primary model ติดลิมิต → index จะเพิ่มขึ้นอัตโนมัติ (เช่น 1, 2)

### Source Code

- Chain builder: `luma_core/llm.py` → `get_llm()`
- Fallback logic: `luma_core/llm.py` → `FallbackModel._generate()`
- Config load/save: `luma_core/config.py` → `get_fallback_info()` / `save_fallback_index()`

