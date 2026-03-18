# Task: Smart Fallback Strategy + Rate Limit Detection

## Checklist

- [x] วิเคราะห์ codebase ปัจจุบัน (`llm.py`, `config.py`, `usage_tracker.py`)
- [x] สร้าง Implementation Plan
- [x] ตอบคำถาม 4 ข้อของ user (spread, prompt สำหรับ external AI, etc.)
- [x] 🟥 RED: เขียน failing tests สำหรับ error classification
- [x] 🟢 GREEN: Implement error classification
- [x] 🟥 RED: เขียน failing tests สำหรับ per-model timeout & rate limit bypass
- [x] 🟢 GREEN: Implement per-model timeout & rate limit bypass ใน `GeminiCLIModel`
- [x] 🟥 RED: เขียน failing tests สำหรับ usage_tracker logging
- [x] 🟢 GREEN: Implement usage_tracker logging (ใน `usage_tracker.py` + `llm.py` FallbackModel)
- [x] ✨ REFACTOR: ปรับปรุง `config.py` model chain
- [x] 🧪 Run all tests ให้ผ่าน
