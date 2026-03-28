# Walkthrough - GitHub Activity Script

I have created a helper script to automate fetching your GitHub activity (recently updated repositories, recent commits, and contribution stats) for your weekly reports.

## Files Created
- [fetch_github_activity.sh](file:///Users/oatrice/Software-projects/The Middle Way -Metadata/scripts/fetch_github_activity.sh)
- **Output File**: `output/github_activity.md` (จะถูกสร้างขึ้นเมื่อรันสคริปต์)

## How to use

### 1. Make the script executable
Open your terminal and run:
```bash
chmod +x ./scripts/fetch_github_activity.sh
```

### 2. Run the script
Execute the script to see your activity summary. You can specify the number of days or months:
```bash
# Default (7 days)
./scripts/fetch_github_activity.sh

# 14 days
./scripts/fetch_github_activity.sh 14
# or
./scripts/fetch_github_activity.sh 14d

# 1 month (approx. 30 days)
./scripts/fetch_github_activity.sh 1m
```

### 3. Output
The script will output a Markdown-formatted summary similar to this:

```markdown
# GitHub Activity Summary (2026-03-27)

## Recently Active Repositories
- **The Middle Way -Metadata** (Updated: 2026-03-27T13:40:32Z)
  _Metadata coordination repo_

## Recent Commits (Last 10)
- **[The Middle Way -Metadata]** Providing Commands for GitHub Activity (2026-03-27T13:41:59Z)

## Contribution Stats
Total contributions (Last 365 days): **3534**

### Daily Activity (Last 7 Days)
- 2026-03-21: **12** contributions
- 2026-03-22: **8** contributions
- 2026-03-23: **45** contributions
- 2026-03-24: **30** contributions
- 2026-03-25: **22** contributions
- 2026-03-26: **15** contributions
- 2026-03-27: **18** contributions
```

## Optional: Visual Heatmap
If you installed the recommended extension and it doesn't show your work (or defaults to an organization), try specifying your username:
```bash
gh extension install maxbeizer/gh-contrib
# Use the --user (or -u) flag to see your own activity across all repos
gh contrib graph --user oatrice
```
หรือหากต้องการสรุป:
```bash
gh contrib summarize --user oatrice
```
