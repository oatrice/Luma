# SBE (Specification by Example) Template

> 📅 Created: 2026-04-29

> 🔗 Issue: https://gitlab.com/oatricedev/Luma/-/work_items/91

---

## Feature: Provider Abstraction for VCS Integrations

The system should support multiple VCS providers (GitHub and GitLab) through a provider abstraction layer, allowing seamless switching between providers while maintaining consistent functionality.

### Scenario: Auto-detect Provider from Repository URL

**Given** the user has configured Luma with a repository URL

**When** the user starts Luma

**Then** the provider is auto-detected based on the repository URL

**And** the appropriate provider instance is initialized

#### Examples

| Repository URL | Environment Variables | Selected Provider | Reason |
|----------------|----------------------|-------------------|--------|
| https://gitlab.com/oatricedev/Luma | GITLAB_TOKEN=xxx | GitLabProvider | GitLab URL detected |
| https://github.com/oatrice/Luma | GITHUB_TOKEN=yyy | GitHubProvider | GitHub URL detected |
| https://gitlab.com/oatricedev/Luma | GITLAB_TOKEN=xxx, GITHUB_TOKEN=yyy | GitLabProvider | URL takes precedence |
| None | GITLAB_TOKEN=xxx | GitLabProvider | Token fallback |
| None | GITHUB_TOKEN=yyy | GitHubProvider | Token fallback |

---

### Scenario: Create Issue on GitLab

**Given** the user is using GitLabProvider

**When** the user selects "Create New Issue" from the menu

**And** enters title "Feature: Add GitLab support"

**And** enters body "Implementation details..."

**Then** a GitLab issue is created via GitLab API

**And** the issue URL is displayed

#### Examples

| Provider | Issue Title | API Endpoint | Response |
|----------|-------------|--------------|----------|
| GitLabProvider | "Feature: Add GitLab support" | POST /projects/:id/issues | Issue created with URL https://gitlab.com/oatricedev/Luma/-/issues/123 |
| GitHubProvider | "Feature: Add GitLab support" | POST /repos/:owner/:repo/issues | Issue created with URL https://github.com/oatrice/Luma/issues/456 |

---

### Scenario: Create Merge Request on GitLab

**Given** the user is using GitLabProvider

**When** the user selects "Create Pull Request" from the menu

**And** enters title "Implement GitLab provider"

**And** selects source branch "feat/gitlab"

**And** selects target branch "main"

**Then** a GitLab Merge Request is created via GitLab API

**And** the MR URL is displayed

#### Examples

| Provider | Action | API Endpoint | Terminology |
|----------|--------|--------------|-------------|
| GitLabProvider | Create MR | POST /projects/:id/merge_requests | Merge Request (MR) |
| GitHubProvider | Create PR | POST /repos/:owner/:repo/pulls | Pull Request (PR) |

---

### Scenario: Fetch Kanban Items from GitLab Boards

**Given** the user is using GitLabProvider

**When** the user selects "View Kanban Status" from the menu

**Then** Kanban items are fetched from GitLab Boards API

**And** items are displayed with their status (To Do, In Progress, Done)

#### Examples

| Provider | Kanban Source | API Endpoint | Status Values |
|----------|---------------|--------------|---------------|
| GitLabProvider | GitLab Boards | GET /projects/:id/boards | To Do, In Progress, Done |
| GitHubProvider | GitHub Projects V2 | GraphQL project item-list | Todo, In Progress, Done |

---

### Scenario: List Issues from GitLab

**Given** the user is using GitLabProvider

**When** the user selects "List Active Issues" from the menu

**Then** issues are fetched from GitLab Issues API

**And** issues are displayed with their numbers and titles

#### Examples

| Provider | CLI Command | API Endpoint | Output Format |
|----------|-------------|--------------|---------------|
| GitLabProvider | glab issue list | GET /projects/:id/issues | #123: Title, #124: Title |
| GitHubProvider | gh issue list | GET /repos/:owner/:repo/issues | #456: Title, #457: Title |

---

### Scenario: Update Issue Status on GitLab

**Given** the user is using GitLabProvider

**When** the user selects an issue and changes its status

**Then** the issue status is updated via GitLab API

**And** the change is reflected in the Kanban board

#### Examples

| Provider | Status Update | API Endpoint | Board Sync |
|----------|---------------|--------------|------------|
| GitLabProvider | Close issue | PUT /projects/:id/issues/:iid | Item moved to Done column |
| GitHubProvider | Close issue | PATCH /repos/:owner/:repo/issues/:number | Item moved to Done column |

---

### Scenario: Backward Compatibility with GitHub

**Given** the user has an existing GitHub repository

**When** the user runs Luma with the GitHub repository URL

**Then** GitHubProvider is automatically selected

**And** all existing functionality continues to work as before

**And** no breaking changes are introduced

#### Examples

| Scenario | Provider | Expected Behavior |
|----------|----------|-------------------|
| Existing GitHub repo | GitHubProvider | All 13 menu options work as before |
| Existing GitHub token | GitHubProvider | Token is used without changes |
| Existing GitHub Actions | GitHubProvider | CI/CD continues to work |

---

### Scenario: Provider Selection via Configuration

**Given** the user has both GITLAB_TOKEN and GITHUB_TOKEN set

**When** the user sets VCS_PROVIDER=gitlab in environment

**Then** GitLabProvider is selected regardless of repository URL

**And** all operations use GitLab APIs

#### Examples

| VCS_PROVIDER | Repository URL | Selected Provider |
|--------------|----------------|-------------------|
| gitlab | github.com/oatrice/Luma | GitLabProvider (config override) |
| github | gitlab.com/oatricedev/Luma | GitHubProvider (config override) |
| auto | gitlab.com/oatricedev/Luma | GitLabProvider (auto-detect) |

---

### Scenario: Error Handling for Missing Token

**Given** the user has not set any VCS token

**When** the user starts Luma

**Then** an error message is displayed

**And** the user is instructed to set GITLAB_TOKEN or GITHUB_TOKEN

#### Examples

| Environment | Error Message |
|-------------|---------------|
| No tokens set | "No VCS provider configured. Set GITLAB_TOKEN or GITHUB_TOKEN" |
| GITLAB_TOKEN invalid | "Invalid GitLab token. Please check your credentials" |
| GITHUB_TOKEN invalid | "Invalid GitHub token. Please check your credentials" |

---

### Scenario: Sync Metrics with GitLab

**Given** the user is using GitLabProvider

**When** the user selects "Track Issue Metrics" from the menu

**Then** metrics are fetched from GitLab Issues API

**And** metrics are stored in .luma_metrics.json

**And** GitLab URLs are used in the metrics file

#### Examples

| Provider | CLI Command | URL Pattern |
|----------|-------------|-------------|
| GitLabProvider | glab issue list | https://gitlab.com/oatricedev/Luma/-/issues/123 |
| GitHubProvider | gh issue list | https://github.com/oatrice/Luma/issues/456 |

---

## Notes

- Provider auto-detection follows this priority: repository URL > VCS_PROVIDER config > environment tokens
- GitLab uses "Merge Request" (MR) terminology, GitHub uses "Pull Request" (PR)
- GitLab Boards API may have different capabilities than GitHub Projects V2
- All provider-specific differences are abstracted behind the VCSProvider protocol
- Backward compatibility is maintained throughout the migration
