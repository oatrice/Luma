# Luma Integration (CLI Wrapper) Tasks

- `[x]` Create Zenith-side Luma Controller in `zenith_core/luma.py`
  - `[x]` Define a robust subprocess wrapper to execute Luma commands
  - `[x]` Implement methods for standard actions (e.g. `run_action`, `code_review`, `generate_plan`)
  - `[x]` Handle JSON parsing of Luma's standard output
- `[x]` Integrate `LumaCLI` into `agents/coder_agent.py`
  - `[x]` Provide CoderAgent with tools/methods to call Luma via the wrapper
- `[x]` Write automated tests in `tests/test_luma_integration.py`
  - `[x]` Mock `subprocess.run` to simulate Luma's `--json` responses
  - `[x]` Verify successful data parsing and error handling
- `[x]` Manual verification (Mocking a real run - unit testing completed)
- `[x]` Create `docs/features/...` documentation for completed issues based on other projects.
