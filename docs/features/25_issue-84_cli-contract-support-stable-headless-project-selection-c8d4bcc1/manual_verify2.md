Step 1: Prepare a safe local test context.
- From `/Users/oatrice/Software-projects/Luma-worktrees/luma1`, confirm the Zenith repo exists at `/Users/oatrice/Software-projects/Zenith`.
- Keep the current `.luma/projects.json` in place so repo/path/slug selectors can resolve against the local registry.
- Expected Result: both the Luma worktree and Zenith repo directories exist locally.

Step 2: Verify legacy numeric bootstrap compatibility still works.
- Run `python3 main.py --auto --action bootstrap --issue 40 --json --project 12`
- Inspect the JSON response and any resulting git/state side effects.
- Expected Result: the command succeeds, `status` is `success`, and the workflow behaves like the existing bootstrap flow from `#40`.
- Expected Result: the resolved target points to Luma project `12`, and branch/state updates still occur as before.

Step 3: Verify an explicit repo selector overrides fragile context.
- Stay in the Luma worktree so `cwd` is not already the Zenith repo.
- Run `python3 main.py --auto --action invalid_action --json --project repo:oatrice/Zenith`
- Expected Result: the command returns JSON that is still parseable even though the action is invalid.
- Expected Result: `resolved_target.repo` is `oatrice/Zenith`, `resolved_target.path` is `/Users/oatrice/Software-projects/Zenith`, and `resolved_target.slug` is `zenith`.
- Expected Result: the selector wins over any stored project or current working directory context.

Step 4: Verify an explicit slug selector resolves the same target.
- Run `python3 main.py --auto --action invalid_action --json --project slug:zenith`
- Expected Result: the JSON response includes `resolved_target.slug = "zenith"` and points to the same Zenith repo/path as the repo selector case.

Step 5: Verify an explicit path selector resolves deterministically.
- Run `python3 main.py --auto --action invalid_action --json --project path:/Users/oatrice/Software-projects/Zenith`
- Expected Result: the JSON response includes `resolved_target.path = "/Users/oatrice/Software-projects/Zenith"`.
- Expected Result: because this path is already in the local registry, the response should also include the canonical repo/slug/project key for Zenith.

Step 6: Verify invalid selectors fail loudly without fallback.
- Run `python3 main.py --auto --action code_review --json --project slug:notfound`
- Run `python3 main.py --auto --action code_review --json --project repo:oatrice/Cerebro`
- Expected Result: the first command returns a machine-readable not-found error.
- Expected Result: the second command returns a machine-readable ambiguity error with candidate targets.
- Expected Result: neither command silently falls back to the current repo, stored project, or a numeric key.

Step 7: Verify machine-readable output always echoes the resolved target.
- Run one successful headless action, such as `python3 main.py --auto --action code_review --json --project repo:oatrice/Zenith`, if your local Zenith checkout is in a safe reviewable state.
- If you prefer a no-side-effect probe, re-use the `invalid_action` commands above and inspect the JSON payload.
- Expected Result: every JSON response that resolves a target includes a `resolved_target` object with enough information to audit the actual repo/path/slug used.

Step 8: Audit bootstrap parity against interactive constraints.
- Pick one issue that should be selectable in the interactive flow and one that should not be selectable based on project status rules.
- Run `bootstrap` headless against both issue numbers with the same target project.
- Expected Result: issues that are valid in the interactive flow bootstrap successfully in headless mode.
- Expected Result: if a disallowed issue is accepted or rejected differently, document that as a parity gap for follow-up instead of reopening `#40`.
