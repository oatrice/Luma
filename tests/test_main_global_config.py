import json

import main


def test_save_global_config_merges_nested_dicts_without_losing_custom_projects(
    tmp_path, monkeypatch
):
    config_file = tmp_path / ".luma_global.json"
    config_file.write_text(
        json.dumps(
            {
                "custom_projects": {
                    "12": {
                        "name": "Tmp",
                        "path": "/tmp/tmp",
                        "repo": "",
                        "kanban_number": 1,
                        "kanban_id": "",
                    }
                },
                "last_projects_by_path": {"/existing": "1"},
                "LLM_PROVIDER": "gemini_cli",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "GLOBAL_CONFIG_FILE", str(config_file))

    # Simulate a stale in-memory snapshot loaded before a custom project was added.
    main.save_global_config(
        {
            "custom_projects": {},
            "last_projects_by_path": {"/new": "12"},
        }
    )

    saved = json.loads(config_file.read_text(encoding="utf-8"))

    assert saved["custom_projects"] == {
        "12": {
            "name": "Tmp",
            "path": "/tmp/tmp",
            "repo": "",
            "kanban_number": 1,
            "kanban_id": "",
        }
    }
    assert saved["last_projects_by_path"] == {
        "/existing": "1",
        "/new": "12",
    }


def test_resolve_project_key_falls_back_to_cwd_detection(monkeypatch):
    monkeypatch.setattr(
        main,
        "PROJECTS",
        {
            "1": {"name": "JarWise"},
            "12": {"name": "Luma"},
        },
    )
    monkeypatch.setattr(main, "detect_project_key_for_path", lambda cwd: "12")

    project_key = main.resolve_project_key(
        "1",
        None,
        "/Users/oatrice/Software-projects/Luma",
    )

    assert project_key == "12"
