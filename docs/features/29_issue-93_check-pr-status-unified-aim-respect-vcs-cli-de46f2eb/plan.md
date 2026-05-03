# Implementation Plan: check_pr_status_unified() ไม่ respect VCS_CLI configuration

> **Refers to**: [Spec Link](./spec.md)
> **Status**: Draft

## 1. Architecture & Design
*High-level technical approach.*

### Component View
- **Modified Components**: 
  - `luma_core/platform_detector.py`: check_pr_status_unified(), get_open_pr_unified(), update_pull_request_unified()
- **New Components**: None
- **Dependencies**: 
  - `luma_core.config.VCS_CLI` (existing)
  - `luma_core.cli_wrapper` (existing)

### Data Model Changes
```python
# No new data structures needed
# Will use existing VCS_CLI configuration from config.py
```

---

## 2. Step-by-Step Implementation

### Step 1: Add failing tests (TDD - Red)
- **Docs**: N/A
- **Code**: Create test cases in `tests/test_platform_detector.py`
  - Test VCS_CLI=glab with GitHub URL → uses glab
  - Test VCS_CLI=glab with GitLab URL → uses glab  
  - Test VCS_CLI=gh with GitHub URL → uses gh
  - Test VCS_CLI=gh with GitLab URL → uses glab (URL fallback)
  - Test VCS_CLI unset with both URLs → URL regex fallback
- **Tests**: `pytest tests/test_platform_detector.py -v -k test_vcs_cli_priority`

### Step 2: Implement VCS_CLI priority logic (TDD - Green)
- **Docs**: N/A
- **Code**: Modify `check_pr_status_unified()` in `luma_core/platform_detector.py`
  ```python
  def check_pr_status_unified(pr_url: str) -> dict:
      # Import VCS_CLI configuration
      from .config import VCS_CLI
      
      # Check VCS_CLI first
      if VCS_CLI == "glab":
          # Use glab for all URLs
          return _check_pr_with_glab(pr_url)
      elif VCS_CLI == "gh":
          # Use gh for all URLs  
          return _check_pr_with_gh(pr_url)
      else:
          # Fallback to URL regex matching (current behavior)
          return _check_pr_by_url_regex(pr_url)
  ```
- **Tests**: Run failing tests, they should pass now

### Step 3: Refactor helper functions (TDD - Refactor)
- **Docs**: N/A
- **Code**: Extract common logic into helper functions
  ```python
  def _check_pr_with_glab(pr_url: str) -> dict:
      # Extract owner/repo/number from URL (both GitHub and GitLab)
      # Use glab CLI wrapper
      
  def _check_pr_with_gh(pr_url: str) -> dict:
      # Extract owner/repo/number from URL  
      # Use gh CLI wrapper
      
  def _check_pr_by_url_regex(pr_url: str) -> dict:
      # Current implementation (URL-based detection)
  ```
- **Tests**: Ensure all tests still pass

### Step 4: Update related functions
- **Docs**: N/A
- **Code**: Apply same pattern to:
  - `get_open_pr_unified()`
  - `update_pull_request_unified()`
- **Tests**: Add tests for these functions with VCS_CLI scenarios

### Step 5: Add logging and error handling
- **Docs**: N/A
- **Code**: Add debug logging:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  
  def check_pr_status_unified(pr_url: str) -> dict:
      logger.debug(f"VCS_CLI={VCS_CLI}, PR URL={pr_url}")
      # ... implementation
      logger.debug(f"Using CLI tool: {cli_tool}")
  ```
- **Tests**: Test log output in test cases

---

## 3. Verification Plan
*How will we verify success?*

> [!IMPORTANT]
> **Android Build Policy**: MUST use scripts in `Android/scripts/` (e.g., `build_android.sh`) instead of direct `./gradlew` to ensure correct JDK version (Java 21).

### Automated Tests
- [ ] Unit Tests: `tests/test_platform_detector.py`
  - Test VCS_CLI priority logic
  - Test URL parsing for both platforms
  - Test error handling
- [ ] Integration Tests: Test with real CLI tools
  - Mock CLI wrapper for unit tests
  - Integration tests with actual gh/glab (if available)

### Manual Verification
- [ ] Set VCS_CLI=glab in .env
- [ ] Run `luma refresh state` with GitHub PR URL in .luma_state.json
- [ ] Verify glab is used instead of gh (check logs)
- [ ] Test with GitLab MR URL to ensure it still works
- [ ] Test VCS_CLI=gh scenario
- [ ] Test VCS_CLI unset scenario (default behavior)

### Performance Verification
- [ ] Measure response time before and after changes
- [ ] Ensure no regression (>500ms target)

---

## 4. File Changes Summary

### Modified Files
1. **luma_core/platform_detector.py**
   - check_pr_status_unified(): Add VCS_CLI priority logic
   - get_open_pr_unified(): Apply same pattern
   - update_pull_request_unified(): Apply same pattern
   - Add helper functions: _check_pr_with_glab(), _check_pr_with_gh(), _check_pr_by_url_regex()

2. **tests/test_platform_detector.py**
   - Add test_vcs_cli_priority_* test cases
   - Add tests for all three functions
   - Mock CLI wrapper for reliable testing

### New Files
- None (all changes are modifications to existing files)

---

## 5. Risk Mitigation

### Backward Compatibility
- Maintain URL regex fallback when VCS_CLI=gh or unset
- No changes to function signatures
- Preserve all existing behavior for default configurations

### Error Handling
- Validate VCS_CLI value (must be "gh" or "glab")
- Graceful fallback to URL regex for invalid VCS_CLI values
- Better error messages when CLI tools are unavailable

### Testing Coverage
- Test all VCS_CLI combinations with both URL types
- Test edge cases (invalid URLs, missing CLI tools)
- Mock external dependencies for reliable unit tests