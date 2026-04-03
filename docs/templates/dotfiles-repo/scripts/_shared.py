from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Path to the dotfiles repository root.",
    )
    parser.add_argument(
        "--home-dir",
        type=Path,
        default=Path.home(),
        help="Home directory to install into or capture from.",
    )
    return parser


def load_manifest(repo_root: Path) -> list[dict[str, str]]:
    manifest_path = repo_root / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    links = data.get("links", [])
    if not isinstance(links, list):
        raise ValueError("manifest.json must contain a 'links' list.")

    normalized: list[dict[str, str]] = []
    for entry in links:
        if not isinstance(entry, dict):
            raise ValueError("Each manifest entry must be an object.")
        source = entry.get("source")
        target = entry.get("target")
        if not source or not target:
            raise ValueError("Each manifest entry must define 'source' and 'target'.")
        normalized.append({"source": source, "target": target})

    return normalized


def iter_manifest_paths(repo_root: Path, home_dir: Path):
    for entry in load_manifest(repo_root):
        yield repo_root / entry["source"], home_dir / entry["target"]


def backup_target(target: Path) -> Path:
    backup = target.with_name(target.name + ".bak")
    counter = 1
    while backup.exists() or backup.is_symlink():
        backup = target.with_name(f"{target.name}.bak.{counter}")
        counter += 1
    target.rename(backup)
    return backup
