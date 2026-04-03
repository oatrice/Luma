import shutil
import subprocess
import sys
from pathlib import Path


TEMPLATE_ROOT = (
    Path(__file__).resolve().parents[1] / "docs" / "templates" / "dotfiles-repo"
)


def _copy_template_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "dotfiles-repo"
    shutil.copytree(TEMPLATE_ROOT, repo_root)
    return repo_root


def test_dotfiles_repo_template_contains_required_files():
    required_paths = [
        "README.md",
        "AGENTS.md",
        ".gitignore",
        "manifest.json",
        "scripts/_shared.py",
        "scripts/install.py",
        "scripts/capture.py",
        "home/.ai-shared-memory.md",
        "home/.codex/AGENTS.md",
        "home/.gemini/GEMINI.md",
    ]

    missing = [rel_path for rel_path in required_paths if not (TEMPLATE_ROOT / rel_path).exists()]

    assert missing == []


def test_global_agent_templates_use_portable_shared_memory_reference():
    codex_agents = (TEMPLATE_ROOT / "home" / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
    gemini_agents = (TEMPLATE_ROOT / "home" / ".gemini" / "GEMINI.md").read_text(encoding="utf-8")

    for content in (codex_agents, gemini_agents):
        assert "~/.ai-shared-memory.md" in content
        assert "/Users/oatrice/.ai-shared-memory.md" not in content


def test_install_script_creates_managed_links(tmp_path):
    repo_root = _copy_template_repo(tmp_path)
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "install.py"),
            "--repo-root",
            str(repo_root),
            "--home-dir",
            str(home_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    targets = [
        (home_dir / ".ai-shared-memory.md", repo_root / "home" / ".ai-shared-memory.md"),
        (home_dir / ".codex" / "AGENTS.md", repo_root / "home" / ".codex" / "AGENTS.md"),
        (home_dir / ".gemini" / "GEMINI.md", repo_root / "home" / ".gemini" / "GEMINI.md"),
    ]

    for target, source in targets:
        assert target.is_symlink()
        assert target.resolve() == source.resolve()


def test_capture_script_syncs_machine_files_back_into_repo(tmp_path):
    repo_root = _copy_template_repo(tmp_path)
    home_dir = tmp_path / "home"
    (home_dir / ".codex").mkdir(parents=True)
    (home_dir / ".gemini").mkdir(parents=True)

    (home_dir / ".ai-shared-memory.md").write_text("# Shared\n\ncaptured\n", encoding="utf-8")
    (home_dir / ".codex" / "AGENTS.md").write_text("# Codex\n\ncaptured\n", encoding="utf-8")
    (home_dir / ".gemini" / "GEMINI.md").write_text("# Gemini\n\ncaptured\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "capture.py"),
            "--repo-root",
            str(repo_root),
            "--home-dir",
            str(home_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert (repo_root / "home" / ".ai-shared-memory.md").read_text(encoding="utf-8") == "# Shared\n\ncaptured\n"
    assert (repo_root / "home" / ".codex" / "AGENTS.md").read_text(encoding="utf-8") == "# Codex\n\ncaptured\n"
    assert (repo_root / "home" / ".gemini" / "GEMINI.md").read_text(encoding="utf-8") == "# Gemini\n\ncaptured\n"
