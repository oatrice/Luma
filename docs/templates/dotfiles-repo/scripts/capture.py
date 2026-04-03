#!/usr/bin/env python3
from __future__ import annotations

import shutil

from _shared import build_common_parser, iter_manifest_paths


def main() -> int:
    parser = build_common_parser(
        "Capture AI dotfiles from a machine back into the repository."
    )
    args = parser.parse_args()

    for repo_target, machine_source in iter_manifest_paths(args.repo_root, args.home_dir):
        repo_target.parent.mkdir(parents=True, exist_ok=True)

        if not machine_source.exists() and not machine_source.is_symlink():
            print(f"missing {machine_source}")
            continue

        source_path = machine_source.resolve() if machine_source.is_symlink() else machine_source
        if source_path.resolve() == repo_target.resolve():
            print(f"managed {machine_source}")
            continue

        shutil.copy2(source_path, repo_target)
        print(f"captured {machine_source} -> {repo_target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
