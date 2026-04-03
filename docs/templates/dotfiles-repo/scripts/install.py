#!/usr/bin/env python3
from __future__ import annotations

import shutil

from _shared import backup_target, build_common_parser, iter_manifest_paths


def main() -> int:
    parser = build_common_parser(
        "Install AI dotfiles from the repository into a home directory."
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy files instead of creating symlinks.",
    )
    args = parser.parse_args()

    for source, target in iter_manifest_paths(args.repo_root, args.home_dir):
        if not source.exists():
            raise FileNotFoundError(f"Missing managed source file: {source}")

        target.parent.mkdir(parents=True, exist_ok=True)
        source_resolved = source.resolve()

        if target.is_symlink() and target.resolve() == source_resolved:
            print(f"unchanged {target}")
            continue

        if target.exists() or target.is_symlink():
            backup = backup_target(target)
            print(f"backed up {target} -> {backup}")

        if args.copy:
            shutil.copy2(source_resolved, target)
            print(f"copied {source_resolved} -> {target}")
        else:
            target.symlink_to(source_resolved)
            print(f"linked {target} -> {source_resolved}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
