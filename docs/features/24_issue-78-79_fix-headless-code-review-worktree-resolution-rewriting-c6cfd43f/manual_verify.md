Step 1: Prepare a Luma worktree context.
- From the main Luma repo, create or reuse a worktree such as `/Users/oatrice/Software-projects/Luma-worktrees/luma1`.
- Change directory into that worktree before running any verification commands.
- Expected Result: `pwd` shows the Luma worktree path, not the main Luma repo path.

Step 2: Verify headless multi-repo `code_review` preserves external repo paths.
- Run Luma headless from the Luma worktree with a multi-repo target that includes external repos such as JarWise.
- Use the same kind of flow that originally reproduced the bug, for example through the Zenith transcript demo or the equivalent `main.py --auto --action code_review --json --project 1` invocation.
- Capture the JSON output returned by Luma.
- Expected Result: each project entry in the JSON keeps its real target repo path.
- Expected Result: JarWise repos should point to JarWise paths such as `/Users/oatrice/Software-projects/JarWise`, `/Users/oatrice/Software-projects/JarWise/Web`, `/Users/oatrice/Software-projects/JarWise/backend`, or `/Users/oatrice/Software-projects/JarWise/Android`.
- Expected Result: only the Luma repo entry may resolve to the active Luma worktree path.

Step 3: Verify the worktree diagnostic message is precise.
- Re-run the same headless `code_review` command while watching the diagnostic output.
- Look for any `🌿 Worktree detected` messages.
- Expected Result: when a path is remapped, the message explains that the remap happened because it is the same git repository as the active `cwd`.
- Expected Result: unrelated repos should not print a misleading remap to the Luma worktree.

Step 4: Verify same-repo worktree remap still works.
- From the same Luma worktree, run a review flow where Luma itself is one of the selected targets.
- Check the returned path for the Luma project entry.
- Expected Result: the Luma project path resolves to the active worktree path, confirming same-repo worktree support still works.

Step 5: Verify project selection resolves the Luma worktree back to project `12`.
- Launch interactive Luma from the Luma worktree.
- Open the project switcher and choose project `12` (`Luma`).
- Return to the main screen/header.
- Expected Result: the selected project remains `Luma` rather than drifting to a dynamic or unrelated project context.

Step 6: Verify the header shows the canonical GitHub Project board for Luma.
- Stay in the Luma worktree after selecting project `12`.
- Inspect the header line labeled `GH Proj`.
- Expected Result: the header shows `Project #5`.
- Expected Result: it does not show a stale or unrelated board such as `Project #1`.

Step 7: Verify non-worktree behavior is unchanged.
- Run the same `code_review` and project-selection checks from the main Luma repo path instead of the worktree.
- Expected Result: flows still work normally.
- Expected Result: Luma should use the main repo path for Luma when not inside a worktree, and external repos should still preserve their own configured paths.

Step 8: Optional automated regression check.
- Run:
- `python3 -m pytest -q tests/test_worktree_detection.py tests/test_worktree_path_resolution.py tests/test_code_review_worktree.py tests/test_action_code_review.py tests/test_config.py`
- Expected Result: the suite passes successfully.
