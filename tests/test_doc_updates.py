from luma_core.doc_updates import (
    PENDING_DOC_UPDATES_KEY,
    detect_pending_doc_updates,
    pending_doc_update_summary,
    refresh_pending_doc_updates,
)
from luma_core.state_manager import LumaState


def _make_project(tmp_path):
    project_dir = tmp_path / "repo"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("# Readme")
    (project_dir / "CHANGELOG.md").write_text("# Changelog")
    (project_dir / "VERSION").write_text("1.0.0\n")
    return {"path": str(project_dir)}


def test_detect_pending_doc_updates_for_code_changes(monkeypatch, tmp_path):
    project = _make_project(tmp_path)

    monkeypatch.setattr(
        "luma_core.doc_updates._get_changed_files",
        lambda _repo_path: ["main.py"],
    )
    monkeypatch.setattr(
        "luma_core.doc_updates._is_version_file_updated",
        lambda _repo_path, _version_file: False,
    )

    status = detect_pending_doc_updates(project)

    assert status["pending"] == ["CHANGELOG.md", "README.md", "VERSION"]
    assert status["meaningful_files"] == ["main.py"]


def test_detect_pending_doc_updates_excludes_already_updated_files(monkeypatch, tmp_path):
    project = _make_project(tmp_path)

    monkeypatch.setattr(
        "luma_core.doc_updates._get_changed_files",
        lambda _repo_path: ["main.py", "README.md", "CHANGELOG.md"],
    )
    monkeypatch.setattr(
        "luma_core.doc_updates._is_version_file_updated",
        lambda _repo_path, _version_file: False,
    )

    status = detect_pending_doc_updates(project)

    assert status["pending"] == ["VERSION"]


def test_detect_pending_doc_updates_ignores_test_only_changes(monkeypatch, tmp_path):
    project = _make_project(tmp_path)

    monkeypatch.setattr(
        "luma_core.doc_updates._get_changed_files",
        lambda _repo_path: ["tests/test_ui.py"],
    )

    status = detect_pending_doc_updates(project)

    assert status["pending"] == []
    assert status["meaningful_files"] == []


def test_refresh_pending_doc_updates_stores_status(monkeypatch, tmp_path):
    project = _make_project(tmp_path)
    state = LumaState()

    monkeypatch.setattr(
        "luma_core.doc_updates._get_changed_files",
        lambda _repo_path: ["main.py"],
    )
    monkeypatch.setattr(
        "luma_core.doc_updates._is_version_file_updated",
        lambda _repo_path, _version_file: False,
    )

    status = refresh_pending_doc_updates(state, project)

    assert state.context[PENDING_DOC_UPDATES_KEY] == status
    assert pending_doc_update_summary(status) == "CHANGELOG.md, README.md, VERSION"
