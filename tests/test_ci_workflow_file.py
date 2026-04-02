from pathlib import Path


def test_ci_workflow_uses_zenith_template_structure():
    workflow_path = Path(".github/workflows/ci.yml")
    content = workflow_path.read_text(encoding="utf-8")

    assert 'name: Continuous Integration' in content
    assert 'branches: [ "main", "master" ]' in content
    assert "jobs:" in content
    assert "  test:" in content
    assert "TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}" in content
    assert "TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}" in content
    assert '- name: Set up Python 3.11' in content
    assert 'python-version: "3.11"' in content
    assert 'pip install pytest' in content
    assert 'if [ -f requirements.txt ]; then pip install -r requirements.txt; fi' in content
    assert 'run: echo "PYTHONPATH=$PWD" >> $GITHUB_ENV' in content
    assert 'python -m pytest tests/ -v' in content
    assert '- name: Notify Telegram on success' in content
    assert '- name: Notify Telegram on failure' in content
