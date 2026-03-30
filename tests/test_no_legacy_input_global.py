from pathlib import Path

TARGET_FILES = [
    "luma_core/tools.py",
    "luma_core/agents/publisher.py",
]


def test_no_standard_input_calls():
    project_root = Path(__file__).resolve().parents[1]
    legacy_calls = []

    for file_name in TARGET_FILES:
        file_path = project_root / file_name
        assert file_path.is_file(), f"Expected file to exist: {file_path}"

        with file_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            if "input(" in line and "ui.safe_input(" not in line:
                legacy_calls.append(f"{file_name}:{i + 1}: {line.strip()}")

    assert not legacy_calls, (
        "Found legacy input() usage:\n" + "\n".join(legacy_calls)
    )


if __name__ == "__main__":
    test_no_standard_input_calls()
