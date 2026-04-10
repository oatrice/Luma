import json
from pathlib import Path

from luma_core.tools import (
    extract_changelog_versions,
    suggest_next_available_changelog_version,
)


def test_suggest_next_available_changelog_version_bumps_minor_when_candidate_exists():
    existing_versions = ["1.11.0", "1.10.0", "1.9.0"]

    assert suggest_next_available_changelog_version("1.11.0", existing_versions) == "1.12.0"


def test_suggest_next_available_changelog_version_keeps_unique_candidate():
    existing_versions = ["1.11.0", "1.10.0", "1.9.0"]

    assert suggest_next_available_changelog_version("1.12.0", existing_versions) == "1.12.0"


def test_repository_changelog_versions_are_unique_and_match_package_version():
    repo_root = Path(__file__).resolve().parents[1]
    changelog_text = (repo_root / "CHANGELOG.md").read_text(encoding="utf-8")
    version_text = (repo_root / "VERSION").read_text(encoding="utf-8").strip()

    versions = extract_changelog_versions(changelog_text)

    assert versions
    assert len(versions) == len(set(versions))
    assert version_text == versions[0]
