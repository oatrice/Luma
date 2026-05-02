# Specification: Fix PR creation functionality for GitLab repositories

> **Status**: Proposed
> **Owner**: Luma Development Team
> **Dates**: Created: 2026-05-01 | Last Updated: 2026-05-01

## 1. Context & Goal
*Why are we building this? What is the problem statement?*

### Problem
Luma currently only supports GitHub repositories for PR creation and management. When users attempt to work with GitLab repositories, they encounter multiple errors:
- "Failed to create PR: 422 - Validation Failed, field: head, code: invalid"
- "GitLab CLI doesn't support GraphQL operations in this context"
- "Could not get project field schema" when selecting issues
- PR status checking fails with "Invalid PR URL" errors

The root cause is that Luma uses GitHub-specific APIs and workflows for all repositories, regardless of their actual platform.

### Goal
Enable Luma to seamlessly work with GitLab repositories by:
1. Automatically detecting repository platform (GitHub vs GitLab)
2. Using appropriate APIs and CLI tools for each platform
3. Providing unified user experience across both platforms
4. Maintaining full compatibility with existing GitHub functionality

---

## 2. User Journey & Requirements
*What should the user experience?*

### User Story
As a **Luma user working with GitLab repositories**, I want to **create, manage, and check status of merge requests** using Luma's workflow, so that **I can have the same productive development experience regardless of my VCS platform**.

### Functional Requirements
- [ ] **Platform Detection**: Automatically detect GitHub vs GitLab from repository URLs and git remotes
- [ ] **PR Creation**: Create merge requests on GitLab using appropriate API calls
- [ ] **PR Status Checking**: Check MR status using GitLab CLI commands
- [ ] **Select Issue Integration**: Allow issue selection from GitLab repositories without GraphQL dependency
- [ ] **VCS CLI Settings**: User-friendly interface to switch between gh/glab CLI tools
- [ ] **Configuration Management**: Correct repository names in all configuration files
- [ ] **Backward Compatibility**: Maintain full functionality for GitHub repositories

### Non-Functional Requirements
- [ ] **Performance**: Platform detection and API calls should complete within 5 seconds
- [ ] **Security**: Use existing CLI authentication mechanisms, no hardcoded credentials
- [ ] **Reliability**: Graceful fallbacks when platform-specific features are unavailable
- [ ] **Maintainability**: Clean separation between GitHub and GitLab logic

---

## 3. Specification by Example (SBE)
*Concrete examples of behavior.*

### Scenario: Platform Detection and PR Creation
**Given** User is working in a GitLab repository (https://gitlab.com/oatricedev/Luma.git)
**When** User initiates PR creation through Luma workflow
**Then** Luma detects GitLab platform and creates MR using GitLab API

#### Examples
| Repository URL | Detected Platform | CLI Tool Used | Result |
|---------------|------------------|--------------|--------|
| https://gitlab.com/oatricedev/Luma.git | GitLab | glab | MR created successfully |
| https://github.com/user/repo.git | GitHub | gh | PR created successfully |
| git@gitlab.com:oatricedev/Zenith.git | GitLab | glab | MR created successfully |

### Scenario: PR Status Checking
**Given** Luma has a GitLab MR URL in state (https://gitlab.com/oatricedev/Luma/-/merge_requests/91)
**When** User checks PR status or automatic status check occurs
**Then** Status is retrieved using GitLab CLI without GraphQL operations

#### Examples
| PR URL | Platform | Status Command | Expected Result |
|-------|----------|----------------|----------------|
| https://gitlab.com/oatricedev/Luma/-/merge_requests/91 | GitLab | glab mr view 91 | Status: "opened" |
| https://github.com/user/repo/pull/42 | GitHub | gh pr view 42 | Status: "open" |
| https://gitlab.com/oatricedev/Luma/-/merge_requests/92 | GitLab | glab mr view 92 | Status: "merged" |

---

## 4. Constraints & Risks
*What should we watch out for?*

- **Constraint**: GitLab CLI does not support GraphQL operations like GitHub CLI
- **Constraint**: GitLab and GitHub have different API endpoints and data structures
- **Risk**: Platform detection logic might incorrectly identify repository type
- **Risk**: Existing GitHub functionality could be broken during implementation
- **Risk**: GitLab authentication might require different setup than GitHub
- **Mitigation**: Implement comprehensive testing for both platforms
- **Mitigation**: Use feature flags to enable/disable platform-specific functionality
- **Mitigation**: Maintain clear separation between platform-specific code