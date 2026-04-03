# SBE (Specification by Example) Template

> 📅 Created: 2026-04-03
> 🔗 Issue: https://github.com/oatrice/Luma/issues/39

---

## Feature: Portable Dotfiles Bootstrap for AI Configuration

Enables users to manage shared AI memory and global agent configurations in a portable repository, simplifying setup on new machines and preventing configuration drift across different environments.

### Scenario: New Machine Bootstrap Installation - Happy Path

**Given** A new machine with no existing AI configuration files (`~/.ai-shared-memory.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`).
**When** The user clones the `dotfiles-repo` and executes the bootstrap installation script.
**Then** The specified AI configuration files are created in the user's home directory, populated with content from the `dotfiles-repo`, and vendor-specific rules referencing these files are correctly configured.

#### Examples

| Clone URL                | Install Script | Repo File Path        | Home Dir File Path         | Repo Content Snippet      | Home Dir File State                               |
| :----------------------- | :------------- | :-------------------- | :------------------------- | :------------------------ | :------------------------------------------------ |
| `git@github.com:user/dotfiles.git` | `install.sh`   | `ai-shared-memory.md` | `~/.ai-shared-memory.md`   | `AI Shared Memory Start`  | File created and populated.                       |
| `git@github.com:user/dotfiles.git` | `install.sh`   | `codex/AGENTS.md`     | `~/.codex/AGENTS.md`       | `Codex Agent Global Rules`| File created and populated.                       |
| `git@github.com:user/dotfiles.git` | `install.sh`   | `gemini/GEMINI.md`    | `~/.gemini/GEMINI.md`      | `Gemini Global Agent Rules`| File created and populated.                       |
| `git@github.com:user/dotfiles.git` | `install.sh`   | `codex/AGENTS.md`     | `~/.codex/AGENTS.md`       | `cross-vendor-rules: true`| `cross-vendor-rules` setting is active in home file. |
| `git@github.com:user/dotfiles.git` | `install.sh`   | `gemini/GEMINI.md`    | `~/.gemini/GEMINI.md`      | `release: 2026.04.03`     | `release` version is `2026.04.03` in home file.   |

---

### Scenario: Capturing Local Changes Back to the Repository

**Given** The `dotfiles-repo` is initialized and the AI configuration files exist in the home directory.
**When** The user modifies `~/.ai-shared-memory.md` with new notes and runs the capture script.
**Then** The changes made to `~/.ai-shared-memory.md` are synchronized back into the `dotfiles-repo`'s corresponding file.

#### Examples

| Capture Script | Home Dir File Path  | Repo File Path      | Local Change Description                  | Repository Update Status |
| :------------- | :------------------ | :------------------ | :---------------------------------------- | :----------------------- |
| `capture.sh`   | `~/.ai-shared-memory.md` | `ai-shared-memory.md` | Added new AI session notes for Project Luma | Successful               |
| `capture.sh`   | `~/.codex/AGENTS.md`    | `codex/AGENTS.md`   | Updated agent priority list               | Successful               |
| `capture.sh`   | `~/.gemini/GEMINI.md`   | `gemini/GEMINI.md`  | Adjusted global prompt settings           | Successful               |

---

### Scenario: Handling Existing Files During Bootstrap Installation - Error/Conflict Handling

**Given** A machine where a custom `~/.gemini/GEMINI.md` file already exists with conflicting rules.
**When** The user runs the bootstrap installation script from the `dotfiles-repo`.
**Then** The script prompts the user to choose between overwriting the existing file, merging changes, or skipping the update for `~/.gemini/GEMINI.md`, ensuring no data loss and respecting user intent.

#### Examples

| Existing Home File Path | Repo File Content       | User Choice | Final Home File State                                  |
| :---------------------- | :---------------------- | :---------- | :----------------------------------------------------- |
| `~/.gemini/GEMINI.md`   | `{"global_rules": "new_rules"}` | `overwrite` | `~/.gemini/GEMINI.md` replaced by repo version.        |
| `~/.gemini/GEMINI.md`   | `{"global_rules": "new_rules"}` | `skip`      | `~/.gemini/GEMINI.md` remains unchanged.               |
| `~/.gemini/GEMINI.md`   | `{"global_rules": "new_rules"}` | `merge`     | `~/.gemini/GEMINI.md` contains combined changes.       |
| `~/.codex/AGENTS.md`    | `{"rebase_strategy": "auto"}`| `skip`      | `~/.codex/AGENTS.md` remains unchanged.                |

---

### Scenario: Cross-Vendor Rule Preservation and Path Portability

**Given** The `dotfiles-repo` contains AI configuration files with portable paths and cross-vendor rules.
**When** The bootstrap installation script is executed on a new machine.
**Then** The installed configuration files correctly reference other configurations using portable `~` or `$HOME` paths, and cross-vendor compatibility rules are maintained.

#### Examples

| Home Dir Config File | Referenced File in Repo | Rule Type               | Expected Outcome                                         |
| :------------------- | :---------------------- | :---------------------- | :------------------------------------------------------- |
| `AGENTS.md`          | `ai-shared-memory.md`   | Shared Path Reference   | `~/.ai-shared-memory.md` is correctly referenced by `AGENTS.md`. |
| `GEMINI.md`          | `codex/AGENTS.md`       | Shared Path Reference   | `~/.codex/AGENTS.md` is correctly referenced by `GEMINI.md`. |
| `AGENTS.md`          | `cross-vendor-rules: true`| Cross-Vendor Compatibility | `cross-vendor-rules` setting is active and effective.    |
| `GEMINI.md`          | `release: 2026.04.03`   | Release Versioning      | `release` version is `2026.04.03` in `GEMINI.md`.        |

---

## Notes

- The repository structure for `dotfiles-repo` is assumed to contain `ai-shared-memory.md`, `codex/AGENTS.md`, and `gemini/GEMINI.md` at the top level or within logical subdirectories that map directly to the home directory structure.
- `install.sh` and `capture.sh` are assumed script names for bootstrapping and synchronization.
- User interaction for conflict resolution is handled by the `install.sh` script.