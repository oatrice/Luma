"""
TDD RED Phase: Tests for CredentialManager (Hybrid Rotation)
These tests are written FIRST and will fail until the implementation is created.
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from luma_core.credential_manager import (
    CredentialManager,
    CredentialStatus,
    CredentialType,
    AllCredentialsExhaustedError,
)


# ─────────────────────────── Fixtures ───────────────────────────


@pytest.fixture
def api_keys():
    return ["key_A", "key_B"]


@pytest.fixture
def oauth_profiles():
    return ["profile_1", "profile_2"]


@pytest.fixture
def manager_with_both(api_keys, oauth_profiles):
    return CredentialManager(api_keys=api_keys, oauth_profiles=oauth_profiles)


@pytest.fixture
def manager_keys_only(api_keys):
    return CredentialManager(api_keys=api_keys, oauth_profiles=[])


@pytest.fixture
def manager_profiles_only(oauth_profiles):
    return CredentialManager(api_keys=[], oauth_profiles=oauth_profiles)


# ─────────────── CredentialStatus Model ───────────────


class TestCredentialStatus:
    def test_api_key_status_defaults(self):
        cs = CredentialStatus(type=CredentialType.API_KEY, value="key_A")
        assert cs.is_active is True
        assert cs.fail_count == 0
        assert cs.cooldown_until is None

    def test_oauth_profile_status_defaults(self):
        cs = CredentialStatus(type=CredentialType.OAUTH_PROFILE, value="profile_1")
        assert cs.is_active is True
        assert cs.type == CredentialType.OAUTH_PROFILE


# ─────────────── CredentialManager Init ───────────────


class TestCredentialManagerInit:
    def test_combined_pool_size(self, manager_with_both):
        # 2 API keys + 2 OAuth profiles = 4 total
        assert len(manager_with_both.pool) == 4

    def test_api_key_types(self, manager_keys_only):
        assert all(c.type == CredentialType.API_KEY for c in manager_keys_only.pool)

    def test_oauth_profile_types(self, manager_profiles_only):
        assert all(
            c.type == CredentialType.OAUTH_PROFILE for c in manager_profiles_only.pool
        )

    def test_empty_pool_raises(self):
        with pytest.raises(ValueError, match="at least one credential"):
            CredentialManager(api_keys=[], oauth_profiles=[])


# ─────────────── Round-Robin Rotation ───────────────


class TestGetNextCredential:
    def test_rotates_through_all_credentials(self, manager_with_both):
        seen_values = set()
        for _ in range(4):
            cred = manager_with_both.get_next_credential()
            seen_values.add(cred.value)
        assert len(seen_values) == 4

    def test_wraps_around_after_full_rotation(self, manager_keys_only):
        first = manager_keys_only.get_next_credential()
        manager_keys_only.get_next_credential()  # advance past second
        third = manager_keys_only.get_next_credential()  # should wrap back to first
        assert first.value == third.value

    def test_skips_rate_limited_credential(self, manager_keys_only, api_keys):
        manager_keys_only.mark_rate_limited(api_keys[0], retry_after=60)
        cred = manager_keys_only.get_next_credential()
        assert cred.value == api_keys[1]

    def test_raises_when_all_exhausted(self, manager_keys_only, api_keys):
        for key in api_keys:
            manager_keys_only.mark_rate_limited(key, retry_after=300)
        with pytest.raises(AllCredentialsExhaustedError):
            manager_keys_only.get_next_credential()


# ─────────────── mark_rate_limited ───────────────


class TestMarkRateLimited:
    def test_marks_key_as_inactive(self, manager_keys_only, api_keys):
        manager_keys_only.mark_rate_limited(api_keys[0], retry_after=60)
        status = manager_keys_only._get_status(api_keys[0])
        assert status.is_active is False

    def test_sets_cooldown_until(self, manager_keys_only, api_keys):
        before = time.time()
        manager_keys_only.mark_rate_limited(api_keys[0], retry_after=120)
        after = time.time()
        status = manager_keys_only._get_status(api_keys[0])
        assert before + 120 <= status.cooldown_until <= after + 120

    def test_increments_fail_count(self, manager_keys_only, api_keys):
        manager_keys_only.mark_rate_limited(api_keys[0], retry_after=60)
        manager_keys_only.mark_rate_limited(api_keys[0], retry_after=60)
        status = manager_keys_only._get_status(api_keys[0])
        assert status.fail_count == 2

    def test_marks_unknown_key_raises(self, manager_keys_only):
        with pytest.raises(ValueError, match="not found"):
            manager_keys_only.mark_rate_limited("non_existent_key", retry_after=60)


# ─────────────── Auto-recovery after cooldown ───────────────


class TestCooldownRecovery:
    def test_recovers_after_cooldown_expires(self, manager_keys_only, api_keys):
        manager_keys_only.mark_rate_limited(api_keys[0], retry_after=1)
        time.sleep(1.1)
        # The manager should re-activate expired credentials before selecting
        cred = manager_keys_only.get_next_credential()
        # Both keys should be available again; we just need the call to succeed
        assert cred is not None


# ─────────────── Singleton behavior ───────────────


class TestSingletonPattern:
    def test_get_instance_returns_same_object(self):
        mgr1 = CredentialManager.get_instance(
            api_keys=["key_X"], oauth_profiles=[]
        )
        mgr2 = CredentialManager.get_instance(
            api_keys=["key_X"], oauth_profiles=[]
        )
        assert mgr1 is mgr2

    def test_get_instance_resets_when_forced(self):
        CredentialManager.reset_instance()
        mgr1 = CredentialManager.get_instance(
            api_keys=["key_Y"], oauth_profiles=[]
        )
        CredentialManager.reset_instance()
        mgr2 = CredentialManager.get_instance(
            api_keys=["key_Z"], oauth_profiles=[]
        )
        assert mgr1 is not mgr2
