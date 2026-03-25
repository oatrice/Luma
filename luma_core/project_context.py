"""
project_context.py — Loads tech stack and agent rules from a target project.

Reads README.md, AGENTS.md, and GEMINI.md from target_dir so that
LLM agents receive accurate, project-specific context instead of
hardcoded tech-stack assumptions.
"""
from __future__ import annotations

import os
from typing import TypedDict

_README_MAX_CHARS = 5000
_AGENTS_MAX_CHARS = 2000


class ProjectContext(TypedDict):
    stack_summary: str
    agent_rules: str


def load_project_context(target_dir: str) -> ProjectContext:
    """Load project-specific context from well-known files in *target_dir*.

    Priority:
    - stack_summary: first 5 000 chars of README.md (or "" if absent)
    - agent_rules: AGENTS.md if present, otherwise GEMINI.md (or "" if absent)

    Never raises — returns empty strings on any error.
    """
    stack_summary = _read_truncated(target_dir, "README.md", _README_MAX_CHARS)
    agent_rules = _read_truncated(target_dir, "AGENTS.md", _AGENTS_MAX_CHARS)
    if not agent_rules:
        agent_rules = _read_truncated(target_dir, "GEMINI.md", _AGENTS_MAX_CHARS)
    return ProjectContext(stack_summary=stack_summary, agent_rules=agent_rules)


def build_context_block(ctx: ProjectContext) -> str:
    """Format a ProjectContext into a prompt-injection-ready string block.

    Returns "" when both fields are empty so callers can skip injection.
    """
    parts: list[str] = []

    if ctx.get("stack_summary"):
        parts.append(
            "### 📦 PROJECT CONTEXT — Tech Stack\n"
            f"{ctx['stack_summary']}"
        )

    if ctx.get("agent_rules"):
        parts.append(
            "### 📋 PROJECT CONTEXT — Agent Rules\n"
            f"{ctx['agent_rules']}"
        )

    if not parts:
        return ""

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _read_truncated(directory: str, filename: str, max_chars: int) -> str:
    """Read *filename* from *directory*, truncating to *max_chars*.

    Returns "" on any error (missing dir, missing file, permission error …).
    """
    try:
        path = os.path.join(directory, filename)
        if not os.path.isfile(path):
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read(max_chars)
        return content
    except OSError:
        return ""
