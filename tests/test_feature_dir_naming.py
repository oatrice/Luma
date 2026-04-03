from pathlib import Path
from types import SimpleNamespace

from luma_core.agents import analyst as analyst_module
from luma_core.agents import spec_agent as spec_module


LONG_MULTI_ISSUE_TITLE = (
    "[Luma Integration] Extract machine-readable JSON from mixed stdout and preserve diagnostics "
    "& [Orchestration] Wire a real Akasa -> CEO -> Coder -> Luma handoff path "
    "& [Demo] Add a one-command multi-agent transcript demo for Zenith "
    "& [Trace] Add run-level aggregation for dashboard views"
)

ISSUE_NUMBER = "13-14-15-8"


class DummyLLM:
    def invoke(self, _messages):
        return SimpleNamespace(content="# Generated Content\n")


def _prepare_project(tmp_path: Path) -> Path:
    docs_dir = tmp_path / "docs"
    templates_dir = docs_dir / "templates"
    templates_dir.mkdir(parents=True)

    (templates_dir / "analysis_template.md").write_text("# Analysis Template\n", encoding="utf-8")
    (templates_dir / "spec_template.md").write_text("# Spec Template\n", encoding="utf-8")
    (docs_dir / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Test Project\n", encoding="utf-8")

    return tmp_path


def _build_state(project_dir: Path) -> dict:
    return {
        "task": LONG_MULTI_ISSUE_TITLE,
        "issue_data": {
            "title": LONG_MULTI_ISSUE_TITLE,
            "number": ISSUE_NUMBER,
            "body": "Combined planning body",
        },
        "target_dir": str(project_dir),
        "target_planning_repos": [],
    }


def test_analyst_agent_truncates_long_multi_issue_feature_directory(tmp_path, monkeypatch):
    project_dir = _prepare_project(tmp_path)
    monkeypatch.setattr(
        analyst_module,
        "get_llm",
        lambda temperature=0.3, purpose="code": DummyLLM(),
    )

    result = analyst_module.analyst_agent(_build_state(project_dir))

    output_dir = Path(result["analysis_file"]).parent
    assert output_dir.exists()
    assert output_dir.name.startswith(f"1_issue-{ISSUE_NUMBER}_")
    assert len(output_dir.name.encode("utf-8")) <= 255


def test_spec_agent_truncates_long_multi_issue_feature_directory(tmp_path, monkeypatch):
    project_dir = _prepare_project(tmp_path)
    monkeypatch.setattr(
        spec_module,
        "get_llm",
        lambda temperature=0.3: DummyLLM(),
    )

    result = spec_module.spec_agent(_build_state(project_dir))

    output_dir = Path(result["spec_file"]).parent
    assert output_dir.exists()
    assert output_dir.name.startswith(f"1_issue-{ISSUE_NUMBER}_")
    assert len(output_dir.name.encode("utf-8")) <= 255
