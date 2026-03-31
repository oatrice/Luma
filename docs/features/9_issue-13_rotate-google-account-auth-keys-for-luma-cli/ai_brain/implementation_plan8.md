# Implementation Plan - GitHub Activity Commands & Script

## Goal
Provide the user with specific GitHub CLI (`gh`) commands and a helper script to fetch recent activity (active repositories, commits, and contribution heatmap data) to be used in their weekly reports.

## Proposed Changes

### [GitHub CLI Commands]
I will provide the following commands:
- **List Recent Active Repos**: `gh repo list --limit 10 --sort updated`
- **Search Recent Commits**: `gh search commits --author "@me" --limit 10 --sort committer-date`
- **Valid Extension (Optional)**: `gh extension install maxbeizer/gh-contrib` (for terminal visualization)

### [NEW] [fetch_github_activity.sh](file:///Users/oatrice/Software-projects/The Middle Way -Metadata/scripts/fetch_github_activity.sh)
A shell script that:
1. Identifies the top 5 most recently updated repositories.
2. Fetches the last commit message and date for each.
3. Retrieves overall contribution counts (total and daily).
4. **Saves results to `output/github_activity.md` for easy reporting.**

## Verification Plan

### Manual Verification
- Run the `gh repo list` command to ensure it returns the expected repositories.
- Run the `gh search commits` command to verify it accurately tracks recent work.
- Execute the `fetch_github_activity.sh` script and verify that the output is properly formatted and contains correct data.
