# SBE (Specification by Example) Template

> 📅 Created: 2026-05-01
> 🔗 Issue: https://gitlab.com/oatricedev/Luma/-/issues/92

---

## Feature: GitLab Repository PR Creation Support

Enable Luma to create, check status, and manage Pull Requests for GitLab repositories, providing the same functionality that exists for GitHub repositories.

### Scenario: Successful PR Creation on GitLab Repository - Happy Path

**Given** Luma is configured with GitLab CLI authentication and a GitLab repository
**When** User initiates PR creation through Luma's workflow
**Then** PR is created successfully on GitLab with correct source and target branches

#### Examples

| Repository URL | Source Branch | Target Branch | Expected Result |
|---------------|---------------|---------------|----------------|
| https://gitlab.com/oatricedev/Luma.git | feature/new-feature | main | MR created successfully |
| https://gitlab.com/oatricedev/Zenith.git | fix/bug-fix | develop | MR created successfully |
| https://gitlab.com/oatricedev/ProjectX.git | hotfix/critical | main | MR created successfully |

---

### Scenario: PR Status Checking for GitLab Merge Request - Edge Case / Error Handling

**Given** Luma has a GitLab MR URL in state
**When** User checks PR status or Luma performs automatic status check
**Then** MR status is retrieved correctly without GraphQL errors

#### Examples

| MR URL | Expected Status | Expected Error Handling |
|-------------|------------------|------------------|
| https://gitlab.com/oatricedev/Luma/-/merge_requests/91 | "opened" | No GraphQL operations attempted |
| https://gitlab.com/oatricedev/Luma/-/merge_requests/92 | "merged" | Status detected correctly |
| https://gitlab.com/oatricedev/Luma/-/merge_requests/999 | "not found" | Graceful error message |

---

### Scenario: Select Issue Option with GitLab Repository - Boundary Conditions

**Given** User selects issue from Kanban in a GitLab repository context
**When** Luma attempts to sync Kanban status or add issue to project
**Then** Operations complete successfully without GraphQL dependency

#### Examples

| Repository Type | Issue Number | Kanban Sync Result | Project Addition Result |
|------------------|---------------|-------------------|------------------------|
| GitLab | #92 | Sync skipped gracefully | Addition skipped gracefully |
| GitHub | #93 | Sync successful | Addition successful |
| GitLab | #94 | GraphQL operations skipped | Operations completed |

---

## Notes

- GitLab CLI does not support GraphQL operations like GitHub CLI
- All GitHub Project operations must have fallback handling for GitLab
- Platform detection must work automatically based on repository URL
- VCS CLI settings must allow user to switch between gh/glab tools
- Repository names in configuration must match actual GitLab repository names