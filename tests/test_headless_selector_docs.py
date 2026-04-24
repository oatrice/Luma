from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_issue40_followup_sbe_uses_prefixed_selector_examples():
    content = _read(
        "docs/features/17_issue-40-42-41_add-headless-select-issue-action-that-mirrors-menu-000930f1/sbe.md"
    )

    assert "repo:oatrice/Zenith" in content
    assert "path:/Users/oatrice/Software-projects/Zenith" in content
    assert "slug:zenith" in content

    assert "repo=oatrice/Zenith" not in content
    assert "path=/Users/oatrice/Software-projects/Zenith" not in content
    assert "slug=zenith" not in content


def test_issue84_docs_use_supported_selector_examples():
    spec = _read(
        "docs/features/25_issue-84_cli-contract-support-stable-headless-project-selection-c8d4bcc1/spec.md"
    )
    sbe = _read(
        "docs/features/25_issue-84_cli-contract-support-stable-headless-project-selection-c8d4bcc1/sbe.md"
    )
    plan = _read(
        "docs/features/25_issue-84_cli-contract-support-stable-headless-project-selection-c8d4bcc1/plan.md"
    )

    for content in (spec, sbe, plan):
        assert "--project repo:oatrice/Zenith" in content or "--project repo:oatrice/Luma" in content
        assert "--project path:/Users/oatrice/Software-projects/Zenith" in content or "--project path:/Users/oatrice/Software-projects/Cerebro" in content

    assert "--project oatrice/Luma" not in spec
    assert "--project /Users/oatrice/Software-projects/Cerebro" not in spec
    assert "--project zenith" not in spec
    assert "--project backend" not in spec
    assert "--project oatrice/UnknownRepo" not in spec
    assert "--project /tmp/not-a-repo" not in spec

    assert "| `code_review` | `oatrice/Luma` |" not in sbe
    assert "| `code_review` | `/Users/oatrice/Software-projects/Cerebro` |" not in sbe
    assert "| `bootstrap` | `zenith` |" not in sbe
    assert "| `backend` | `Ambiguous project selector 'backend'.` |" not in sbe
    assert "| `oatrice/UnknownRepo` | `Could not resolve project selector 'oatrice/UnknownRepo'.` |" not in sbe
    assert "| `/tmp/not-a-repo` | `Unknown project key or invalid path '/tmp/not-a-repo'.` |" not in sbe

    assert "--project /Users/oatrice/Software-projects/Cerebro" not in plan
    assert "--project oatrice/Luma" not in plan
    assert "--project backend" not in plan
