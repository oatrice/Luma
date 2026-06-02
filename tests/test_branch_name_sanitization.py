import pytest
from luma_core.actions.utils import (
    _build_default_branch_name,
    _normalize_branch_suggestions,
    _sanitize_branch_name,
)

def test_sanitize_branch_name():
    assert _sanitize_branch_name("bug: active alert") == "bug-active-alert"
    assert _sanitize_branch_name("feat: [abc] new feature!") == "feat-abc-new-feature"
    assert _sanitize_branch_name("invalid chars ~^:?*[]\\") == "invalid-chars"
    assert _sanitize_branch_name("trailing leading - - ") == "trailing-leading"
    assert _sanitize_branch_name("feat/123-bug:-active-alert") == "feat/123-bug-active-alert"
    assert _sanitize_branch_name("feat/123-bug:-active/alert") == "feat/123-bug-active/alert"
    assert _sanitize_branch_name("---feat/123---") == "feat/123"

def test_build_default_branch_name_with_special_chars():
    issue_nums = "21"
    title = "bug: active alert locations ar"
    branch = _build_default_branch_name(issue_nums, title)
    assert branch == "feat/21-bug-active-alert-locations-ar"

def test_normalize_branch_suggestions_with_special_chars():
    issue_nums = "21"
    primary_number = 21
    fallback = "feat/21-fallback"
    
    # AI suggestion with colon
    suggestions = ["feat/21-bug:-active-alert-locations-ar"]
    normalized = _normalize_branch_suggestions(
        suggestions,
        issue_nums=issue_nums,
        primary_number=primary_number,
        fallback_branch_name=fallback,
    )
    # The colon should be sanitized and the suggestion kept
    assert normalized == ["feat/21-bug-active-alert-locations-ar"]

    # If the suggestion is completely invalid even after sanitize, fallback is used
    # e.g., an empty string after sanitize
    suggestions = ["???"]
    normalized = _normalize_branch_suggestions(
        suggestions,
        issue_nums=issue_nums,
        primary_number=primary_number,
        fallback_branch_name=fallback,
    )
    assert normalized == [fallback]
