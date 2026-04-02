# Implementation Plan: CLI Contract: Metadata Endpoint and Headless JSON Output Guarantees

> **Refers to**: ./spec.md
> **Status**: Completed

## 1. Architecture & Design

### Component View
- **Modified Components**:
  - `main.py`: added metadata mode, contract validation, metadata builders, and startup-safe compatibility initialization
  - `tests/test_main_headless_cli.py`: added coverage for metadata mode and real subprocess stdout contract
  - `README.md`: documented the external CLI contract
- **Reused Components**:
  - `luma_core.tools.get_current_version()`
  - `luma_core.tools.get_project_git_info()`
- **Dependencies**:
  - Python standard libraries: `json`, `platform`, `subprocess`, `sys`
  - repository version source: `VERSION`

---

## 2. Implementation Steps

### Step 1: Add metadata mode
- Added `--meta` parsing in `main.py`
- Defined explicit metadata-mode validation:
  - `--meta` requires `--json`
  - `--meta` cannot be combined with `--action` or `--auto`

### Step 2: Build stable metadata payload
- Added `CONTRACT_VERSION = "2.0"`
- Added `SUPPORTED_HEADLESS_ACTIONS = ("code_review",)`
- Reused existing helpers for version and git info
- Added `is_git_dirty()` and metadata payload builders in `main.py`
- Ensured metadata prefers `VERSION` as the canonical version source

### Step 3: Protect JSON-only stdout
- Moved `ensure_importlib_metadata_compat()` before heavier imports in `main.py`
- Preserved `redirect_stdout(sys.stderr)` for headless action execution
- Verified startup-time warnings no longer corrupt JSON stdout

### Step 4: Document the contract
- Updated `README.md` with:
  - metadata endpoint usage
  - payload shape
  - stdout/stderr separation guarantees
- Updated this feature folder to match shipped behavior

---

## 3. Verification Plan

### Automated Tests

Run:

```bash
python3 -m pytest tests/test_main_headless_cli.py tests/test_main_global_config.py tests/test_main_refresh_state.py tests/test_action_code_review.py -q
```

Expected:

- all tests pass
- metadata mode remains machine-readable
- subprocess-based stdout contract remains parseable

### Manual Verification

#### Scenario 1: Metadata success path

Run:

```bash
python3 main.py --meta --json
```

Verify:

- stdout is valid JSON
- payload contains `version`, `git_commit`, `dirty`, `contract_version`, `supported_actions`, `python_version`
- `version` matches `VERSION`

#### Scenario 2: Invalid metadata flags

Run:

```bash
python3 main.py --meta --json --action code_review
```

Verify:

- exit code is `2`
- stdout is JSON error payload
- error message is `--meta cannot be combined with --action or --auto.`

#### Scenario 3: Real subprocess stdout contract

Run:

```bash
python3 - <<'PY'
import json
import subprocess
import sys

cmd = [
    sys.executable,
    "main.py",
    "--auto",
    "--action",
    "invalid_action",
    "--json",
    "--project",
    "12",
]
res = subprocess.run(cmd, capture_output=True, text=True)
print(res.returncode)
print(res.stdout)
print(res.stderr)
json.loads(res.stdout)
print("JSON OK")
PY
```

Verify:

- `json.loads(res.stdout)` succeeds
- stdout has no human-readable prefix/suffix
- stderr may contain warnings without breaking stdout

#### Scenario 4: Interactive regression

Run:

```bash
python3 main.py
```

Verify:

- interactive menu still appears
- normal exit still works
- no forced headless behavior appears without flags
