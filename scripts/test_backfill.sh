#!/bin/bash
gh api repos/oatrice/Luma/issues/17/events --jq '.[].event'
gh pr list --search '17' --state all --json createdAt,mergedAt,title
