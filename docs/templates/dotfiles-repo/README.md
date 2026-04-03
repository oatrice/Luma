# AI Dotfiles Bootstrap

This template is a portable dotfiles repository for cross-vendor AI memory and global agent instructions.

## What It Manages

- `home/.ai-shared-memory.md`
- `home/.codex/AGENTS.md`
- `home/.gemini/GEMINI.md`

## Layout

```text
dotfiles-repo/
├── AGENTS.md
├── README.md
├── manifest.json
├── home/
│   ├── .ai-shared-memory.md
│   ├── .codex/AGENTS.md
│   └── .gemini/GEMINI.md
└── scripts/
    ├── _shared.py
    ├── capture.py
    └── install.py
```

## Bootstrap on a New Machine

Clone this repository anywhere, then install the managed files into your home directory:

```bash
python3 scripts/install.py --repo-root "$PWD"
```

By default the installer creates symlinks so one repository stays the source of truth. Use `--copy` only if you explicitly want independent files on the machine.

## Capture Existing Machine Files

If the machine already has global AI files that you want to bring back into the repo:

```bash
python3 scripts/capture.py --repo-root "$PWD"
```

This copies `~/.ai-shared-memory.md`, `~/.codex/AGENTS.md`, and `~/.gemini/GEMINI.md` into the tracked `home/` folder.

## Recommended Workflow

1. Update the files inside `home/`.
2. Run `python3 scripts/install.py --repo-root "$PWD"` on each machine.
3. When a machine gets edited outside the repo, run `python3 scripts/capture.py --repo-root "$PWD"` before committing.

## Rules

- Keep vendor-specific files thin and point them to `~/.ai-shared-memory.md`.
- Keep paths portable with `~` or `$HOME`, not user-specific absolute paths.
- Never store secrets, API keys, or tokens in this repository.
