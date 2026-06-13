# Manual Verification Guide: Global Luma CLI Shortcut

**Step 1:** Verify the global wrapper file was created at `~/.local/bin/luma` and has executable permissions.
**Step 2:** Run Luma from a completely different directory (outside Luma and FonMaYang projects) using:
```bash
/Users/oatrice/.local/bin/luma --help
```
**Step 3:** Confirm Luma prints its usage help text successfully.
**Step 4:** Ensure the local wrapper at `/Users/oatrice/Software Project/FonMaYang/luma` is removed.

**Expected Result:**
- Running Luma globally succeeds without issues.
- Environment variables from Luma's `.env` (if exists) are loaded correctly.
- Working directory is preserved in the terminal.
