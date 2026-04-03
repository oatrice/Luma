# Specification: Create portable dotfiles bootstrap for shared AI memory and global agents

> **Status**: Draft
> **Owner**:
> **Dates**: Created: April 3, 2026 | Last Updated: April 3, 2026

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
Our shared AI memory and global agent instructions currently live as machine-local files such as `~/.ai-shared-memory.md`, `~/.codex/AGENTS.md`, and `~/.gemini/GEMINI.md`. That makes them easy to lose when moving to a new machine, and it also makes cross-vendor rule drift more likely over time.

### Goal
To establish a portable dotfiles bootstrap repository structure that can be cloned on a new machine and installed into the home directory with a small script. This will ensure consistency, prevent data loss, and simplify management of cross-vendor rules.

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
As a **developer or AI agent user**, I want to **set up my AI configuration files on a new machine using a bootstrap process and synchronize local changes back to a repository**, so that **my AI environment is consistently configured across machines, my critical configuration data is safe from loss, and managing vendor-specific rules is simplified.**

### Functional Requirements
- [ ] A portable dotfiles repository template is created for `~/.ai-shared-memory.md`, `~/.codex/AGENTS.md`, and `~/.gemini/GEMINI.md`.
- [ ] An installation script is provided to set up these files in the user's home directory using portable paths (`~` or `$HOME`).
- [ ] Vendor-specific agent files correctly reference the shared memory via portable home-directory paths.
- [ ] A capture script is provided to sync machine-local changes back into the tracked dotfiles repository.
- [ ] The setup process (bootstrap and capture) is clearly documented for reuse.
- [ ] Cross-vendor rules for rebase conflict handling and release versioning are preserved.

### Non-Functional Requirements
- [ ] **Ease of Use**: The bootstrap and capture scripts are intuitive and require minimal user intervention.
- [ ] **Portability**: Configurations and scripts function correctly across different user home directories and common development environments.
- [ ] **Maintainability**: The dotfiles structure and scripts are easy to update and manage.
- [ ] **Security**: Sensitive information (like API keys) is not hardcoded and handled via `.env` or similar secure mechanisms as per project convention.

---

## 3. Specification by Example (SBE)

### Scenario: Initial Setup on a New Machine
**Given** a new machine with Git and Python 3.9+ installed, and no existing Luma AI configuration files in the home directory.
**When** the user clones the `dotfiles-repo` and executes the bootstrap script.
**Then** the `~/.ai-shared-memory.md`, `~/.codex/AGENTS.md`, and `~/.gemini/GEMINI.md` files are created or updated with content from the `dotfiles-repo`, using portable home directory references.

#### Examples
| Precondition | Action | Resulting Files & Content | Notes |
|---|---|---|---|
| `~/` is clean of AI config files. | `git clone <dotfiles-repo-url> ~/my-dotfiles` <br> `cd ~/my-dotfiles` <br> `python bootstrap.py` | `~/.ai-shared-memory.md` created/updated. <br> `~/.codex/AGENTS.md` created/updated. <br> `~/.gemini/GEMINI.md` created/updated. <br> All files use `~` for paths. | Bootstrap script handles symbolic linking or copying and ensures correct permissions. |
| `~/.codex/AGENTS.md` (via `bootstrap.py`) contains reference to `~/.ai-shared-memory.md`. | `python bootstrap.py` on existing setup. | Existing AI config files are updated with any new content or rules from the `dotfiles-repo`. | Handles updates gracefully, preserves user additions if possible or clearly indicates overwrite. |

### Scenario: Capturing Local Changes
**Given** a new machine has been set up with the dotfiles, and the user has made local modifications to `~/.ai-shared-memory.md` (e.g., added custom notes or updated rules).
**When** the user runs the capture script from their cloned `dotfiles-repo` directory.
**Then** the local changes from `~/.ai-shared-memory.md` are written back to the corresponding file within the `dotfiles-repo`.

#### Examples
| Precondition | Action | Resulting Files & Content | Notes |
|---|---|---|---|
| User has manually added new content to `~/.ai-shared-memory.md`. | `cd ~/my-dotfiles` <br> `python capture.py` | `~/my-dotfiles/.ai-shared-memory.md` is updated with the latest content from `~/.ai-shared-memory.md`. | Capture script ensures the source of truth in the repo is updated with local modifications. |
| User has modified `~/.codex/AGENTS.md` and `~/.gemini/GEMINI.md` locally. | `cd ~/my-dotfiles` <br> `python capture.py` | Corresponding files in `~/my-dotfiles/` are updated to reflect local changes. | All tracked AI config files are synchronized. |

---

## 4. Constraints & Risks
*What should we watch out for?*
- **Constraint**: Scripts must be compatible with standard shell environments and Python 3.9+.
- **Constraint**: Paths must be universally portable using `~` or `$HOME`.
- **Risk**: Drift between vendor-specific agent instructions and shared memory if the capture mechanism is not used or fails.
- **Risk**: Accidental overwriting of critical user-specific local changes if the capture script is not used carefully.
- **Risk**: Maintaining compatibility of the `dotfiles-repo` template as Luma AI evolves or new vendors are added.
- **Risk**: Ensuring the bootstrap process handles existing files gracefully without data loss.