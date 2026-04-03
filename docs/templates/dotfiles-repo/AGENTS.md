# AI Dotfiles Repo Rules

- Keep `README.md` in English.
- Keep shared rules in `home/.ai-shared-memory.md`.
- Keep vendor-specific files in `home/.codex/AGENTS.md` and `home/.gemini/GEMINI.md` aligned with the shared memory.
- Use portable home-directory references such as `~/.ai-shared-memory.md` instead of user-specific absolute paths.
- When adding a new assistant, update `manifest.json`, `scripts/install.py`, and `scripts/capture.py` together.
- Never commit secrets, API keys, tokens, or machine-local `.env` data.
