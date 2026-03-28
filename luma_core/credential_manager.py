"""
credential_manager.py — Hybrid Credential Rotation for Luma CLI

Manages a mixed pool of Google API Keys and Gemini CLI OAuth Profiles.
Supports round-robin rotation with per-credential cooldown on 429 errors.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import List, Optional


class CredentialType(str, Enum):
    API_KEY = "API_KEY"
    OAUTH_PROFILE = "OAUTH_PROFILE"


class AllCredentialsExhaustedError(RuntimeError):
    """Raised when every credential in the pool is currently rate-limited."""


@dataclass
class CredentialStatus:
    type: CredentialType
    value: str
    is_active: bool = True
    fail_count: int = 0
    cooldown_until: Optional[float] = None

    def is_available(self) -> bool:
        """Return True if the credential is ready to use."""
        if not self.is_active:
            # Auto-recover if cooldown has expired
            if self.cooldown_until is not None and time.time() >= self.cooldown_until:
                self.is_active = True
                self.cooldown_until = None
        return self.is_active


class CredentialManager:
    """
    Manages a mixed pool of API Keys and OAuth Profiles.

    Usage:
        manager = CredentialManager.get_instance(
            api_keys=["key_A", "key_B"],
            oauth_profiles=["profile_1"],
        )
        cred = manager.get_next_credential()
        # cred.type == CredentialType.API_KEY or OAUTH_PROFILE
        # cred.value == the key string or profile folder name
    """

    _instance: Optional[CredentialManager] = None
    _lock: Lock = Lock()

    def __init__(
        self,
        api_keys: List[str],
        oauth_profiles: List[str],
    ) -> None:
        if not api_keys and not oauth_profiles:
            raise ValueError(
                "CredentialManager requires at least one credential "
                "(API key or OAuth profile)."
            )

        self.pool: List[CredentialStatus] = []
        for key in api_keys:
            self.pool.append(CredentialStatus(type=CredentialType.API_KEY, value=key))
        for profile in oauth_profiles:
            self.pool.append(
                CredentialStatus(type=CredentialType.OAUTH_PROFILE, value=profile)
            )

        self._index: int = 0
        self._pool_lock: Lock = Lock()

    # ── Public API ──────────────────────────────────────────────────────────

    def get_next_credential(self) -> CredentialStatus:
        """
        Return the next available credential using round-robin.

        Raises:
            AllCredentialsExhaustedError: when all credentials are rate-limited.
        """
        with self._pool_lock:
            n = len(self.pool)
            for _ in range(n):
                cred = self.pool[self._index % n]
                self._index = (self._index + 1) % n
                if cred.is_available():
                    return cred

            raise AllCredentialsExhaustedError(
                "All credentials are currently rate-limited. "
                "Please add a new API key (from a different Google Account) "
                "or wait for the cooldown to expire."
            )

    def mark_rate_limited(self, value: str, retry_after: int = 60) -> None:
        """
        Mark a credential as rate-limited.

        Args:
            value: The API key string or OAuth profile name.
            retry_after: Seconds to wait before retrying. Defaults to 60.

        Raises:
            ValueError: If the credential is not in the pool.
        """
        with self._pool_lock:
            status = self._get_status_unsafe(value)
            if status is None:
                raise ValueError(
                    f"Credential '{value}' not found in the pool."
                )
            status.is_active = False
            status.cooldown_until = time.time() + retry_after
            status.fail_count += 1

    def _get_status(self, value: str) -> Optional[CredentialStatus]:
        """Public thread-safe lookup by value."""
        with self._pool_lock:
            return self._get_status_unsafe(value)

    # ── Internals ────────────────────────────────────────────────────────────

    def _get_status_unsafe(self, value: str) -> Optional[CredentialStatus]:
        """Lookup without acquiring the lock (caller must hold it)."""
        for cred in self.pool:
            if cred.value == value:
                return cred
        return None

    # ── Named Singleton Pattern ─────────────────────────────────────────────
    _instances: dict[str, CredentialManager] = {}
    _lock: Lock = Lock()

    @classmethod
    def get_instance(
        cls,
        api_keys: Optional[List[str]] = None,
        oauth_profiles: Optional[List[str]] = None,
        name: str = "default",
    ) -> "CredentialManager":
        """
        Return a named singleton instance of CredentialManager.
        
        On first call for a given name, api_keys and oauth_profiles are used to initialize.
        Subsequent calls return the cached instance for that name.
        """
        with cls._lock:
            if name not in cls._instances:
                cls._instances[name] = cls(
                    api_keys=api_keys or [],
                    oauth_profiles=oauth_profiles or [],
                )
            return cls._instances[name]

    @classmethod
    def reset_instance(cls, name: str = "default") -> None:
        """Reset a specific named singleton (primarily used for testing)."""
        with cls._lock:
            if name in cls._instances:
                del cls._instances[name]

    @classmethod
    def reset_all_instances(cls) -> None:
        """Reset all named singletons."""
        with cls._lock:
            cls._instances.clear()
