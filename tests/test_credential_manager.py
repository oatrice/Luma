import pytest
import time
import os
from unittest.mock import patch
from luma_core.credential_manager import (
    CredentialManager,
    CredentialType,
    AllCredentialsExhaustedError,
    STATE_FILE,
)

@pytest.fixture(autouse=True)
def clean_global_state():
    """Ensure global state file is removed before each test for isolation."""
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
        except Exception:
            pass
    CredentialManager.reset_all_instances()
    yield
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
        except Exception:
            pass
    CredentialManager.reset_all_instances()

@pytest.fixture
def api_keys():
    return ["key_A", "key_B"]


@pytest.fixture
def oauth_profiles():
    return ["profile_1", "profile_2"]


@pytest.fixture
def manager_keys_only(api_keys):
    return CredentialManager(api_keys=api_keys, oauth_profiles=[])


@pytest.fixture
def manager_profiles_only(oauth_profiles):
    return CredentialManager(api_keys=[], oauth_profiles=oauth_profiles)


@pytest.fixture
def manager_with_both(api_keys, oauth_profiles):
    return CredentialManager(api_keys=api_keys, oauth_profiles=oauth_profiles)


class TestCredentialManagerInit:
    def test_init_with_keys_only(self, api_keys):
        manager = CredentialManager(api_keys=api_keys, oauth_profiles=[])
        assert len(manager.pool) == 2
        assert manager.pool[0].type == CredentialType.API_KEY
        assert manager.pool[0].value == "key_A"

    def test_init_with_profiles_only(self, oauth_profiles):
        manager = CredentialManager(api_keys=[], oauth_profiles=oauth_profiles)
        assert len(manager.pool) == 2
        assert manager.pool[0].type == CredentialType.OAUTH_PROFILE
        assert manager.pool[0].value == "profile_1"

    def test_init_no_credentials_raises(self):
        with pytest.raises(ValueError, match="at least one credential"):
            CredentialManager(api_keys=[], oauth_profiles=[])

    def test_duplicate_api_keys_raise(self):
        with pytest.raises(ValueError, match="must be unique"):
            CredentialManager(api_keys=["key_A", "key_A"], oauth_profiles=[])

    def test_cross_type_value_collisions_raise(self):
        with pytest.raises(ValueError, match="must be unique"):
            CredentialManager(
                api_keys=["shared_value"],
                oauth_profiles=["shared_value"],
            )


class TestGetNextCredential:
    def test_rotates_through_all_credentials(self, manager_with_both):
        seen_values = set()
        # Reset manager index for test
        manager_with_both._index = 0
        for _ in range(4):
            cred = manager_with_both.get_next_credential()
            seen_values.add(cred.value)
        assert len(seen_values) == 4

    def test_skips_rate_limited_credential(self, manager_keys_only, api_keys):
        manager_keys_only.mark_rate_limited(api_keys[0], retry_after=60)
        # Should skip key_A and return key_B
        cred = manager_keys_only.get_next_credential()
        assert cred.value == api_keys[1]

    def test_raises_exhausted_error_when_all_rate_limited(self, manager_keys_only, api_keys):
        for key in api_keys:
            manager_keys_only.mark_rate_limited(key, retry_after=60)
        
        with pytest.raises(AllCredentialsExhaustedError, match="currently rate-limited"):
            manager_keys_only.get_next_credential()


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


class TestNamedSingleton:
    def test_get_instance_returns_same_object(self, api_keys):
        m1 = CredentialManager.get_instance(api_keys=api_keys, name="test_pool")
        m2 = CredentialManager.get_instance(api_keys=api_keys, name="test_pool")
        assert m1 is m2

    def test_different_names_return_different_objects(self, api_keys):
        m1 = CredentialManager.get_instance(api_keys=api_keys, name="pool_1")
        m2 = CredentialManager.get_instance(api_keys=api_keys, name="pool_2")
        assert m1 is not m2

    def test_reset_instance(self, api_keys):
        m1 = CredentialManager.get_instance(api_keys=api_keys, name="to_be_reset")
        CredentialManager.reset_instance("to_be_reset")
        m2 = CredentialManager.get_instance(api_keys=api_keys, name="to_be_reset")
        assert m1 is not m2
