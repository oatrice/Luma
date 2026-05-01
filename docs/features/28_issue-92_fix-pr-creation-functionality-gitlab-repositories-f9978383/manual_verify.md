# Manual Verification Guide for GitLab PR Creation Fix

This guide provides step-by-step instructions to manually verify that the GitLab PR creation functionality works correctly.

## Step 1: Environment Setup

**Prerequisites:**
- Install GitLab CLI (`glab`) and authenticate: `glab auth login`
- Install GitHub CLI (`gh`) and authenticate: `gh auth login`
- Ensure you have access to both GitHub and GitLab repositories

**Expected Result:** Both CLI tools are authenticated and ready to use.

## Step 2: Platform Detection Testing

**Action:** Run the platform detection test script
```bash
cd /Users/oatrice/Software-projects/Luma-worktrees/luma1
python test_pr_creation.py
```

**Expected Result:** 
- All platform detection tests pass ✅
- GitLab URLs are detected as "gitlab"
- GitHub URLs are detected as "github"

## Step 3: PR Status Checking Verification

**Action:** Run the PR status checking test
```bash
python test_pr_status_fix.py
```

**Expected Result:**
- Invalid URLs return appropriate error messages
- GitLab MR URLs are parsed correctly
- GitHub PR URLs are parsed correctly
- No "Invalid PR URL" errors for valid formats

## Step 4: VCS CLI Settings Testing

**Action:** Start Luma and navigate to settings
```bash
python main.py
# Select option 6 (Settings)
# Select option 3 (VCS CLI)
```

**Expected Result:**
- Settings menu shows current VCS CLI (gh/glab)
- Can switch between GitHub CLI and GitLab CLI
- Setting persists after restart

## Step 5: GitLab Repository Testing

**Action:** Test with a GitLab repository
```bash
# Clone a GitLab repo if needed
git clone https://gitlab.com/oatricedev/Zenith.git
cd Zenith

# Create a feature branch
git checkout -b test-feature
echo "test change" >> test.txt
git add test.txt
git commit -m "Test feature"

# Run Luma PR creation
cd /Users/oatrice/Software-projects/Luma-worktrees/luma1
python main.py
# Select option to create PR
```

**Expected Result:**
- Platform detected as GitLab
- MR created successfully on GitLab
- No "422 Validation Failed" errors

## Step 6: GitHub Repository Testing (Regression Test)

**Action:** Test with a GitHub repository to ensure no regression
```bash
# Use existing GitHub repo or create test repo
cd /path/to/github/repo
git checkout -b test-github-feature
echo "github test" >> github-test.txt
git add github-test.txt
git commit -m "GitHub test"

# Run Luma PR creation
cd /Users/oatrice/Software-projects/Luma-worktrees/luma1
python main.py
# Select option to create PR
```

**Expected Result:**
- Platform detected as GitHub
- PR created successfully on GitHub
- All existing functionality works as before

## Step 7: Select Issue Option Testing

**Action:** Test issue selection with GitLab repository
```bash
# Start Luma with GitLab repo context
python main.py
# Select option to browse issues/Kanban
# Try to select an issue
```

**Expected Result:**
- No "GitLab CLI doesn't support GraphQL operations" errors
- Graceful fallback message displayed
- Operations complete without crashing

## Step 8: Multi-Repo PR Creation Testing

**Action:** Test multi-repo PR creation
```bash
cd /Users/oatrice/Software-projects/Luma-worktrees/luma1
python -c "
from luma_core.tools import create_multi_repo_prs
from luma_core.config import DEFAULT_PROJECTS
configs = list(DEFAULT_PROJECTS.values())
results = create_multi_repo_prs(configs[:2], 'main')
print('Multi-repo PR results:', results)
"
```

**Expected Result:**
- Both GitHub and GitLab repos handled correctly
- No crashes or import errors
- Appropriate CLI tools used for each platform

## Step 9: Configuration Verification

**Action:** Verify repository names in configuration
```bash
grep -r "oatrice/Luma" /Users/oatrice/Software-projects/Luma-worktrees/luma1/.luma/
grep -r "oatricedev/Luma" /Users/oatrice/Software-projects/Luma-worktrees/luma1/.luma/
```

**Expected Result:**
- All instances of "oatrice/Luma" changed to "oatricedev/Luma"
- No incorrect repository names remain

## Step 10: End-to-End Workflow Test

**Action:** Complete workflow test
1. Start Luma with GitLab repository
2. Create a feature branch with changes
3. Use Luma to create MR
4. Check MR status through Luma
5. Verify MR appears on GitLab

**Expected Result:**
- Complete workflow succeeds
- No errors at any step
- MR properly created and trackable

## Troubleshooting

**Common Issues:**
- **Authentication errors**: Run `glab auth login` or `gh auth login`
- **Platform detection failures**: Check repository URL format
- **GraphQL errors**: Ensure VCS CLI setting matches repository platform
- **Import errors**: Verify all required modules are in Python path

**Verification Commands:**
```bash
# Check CLI authentication
glab auth status
gh auth status

# Verify platform detection
python -c "from luma_core.platform_detector import detect_repo_platform; print(detect_repo_platform('https://gitlab.com/oatricedev/Luma.git'))"

# Test unified functions import
python -c "from luma_core.platform_detector import create_pull_request_unified; print('Import successful')"
```
