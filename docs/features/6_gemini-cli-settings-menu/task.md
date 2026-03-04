# Task list

- [x] Write implementation plan and review with user
- [x] Create Settings menu in Luma UI (`main.py`, `actions.py`)
- [x] Persist LLM Provider selection (OpenRouter, Gemini API, Gemini CLI) to `.luma_global.json`
- [x] Modify `config.py` to read settings from `.luma_global.json` (falling back to `.env`)
- [x] Create `gemini_cli.py` to handle delegation to `gemini` CLI (similar to `opencode.py`)
- [x] Integrate new `gemini_cli` option where `opencode` is currently used (Settings UI done)
- [x] Refactor and verify (TDD Red -> Green -> Refactor)
