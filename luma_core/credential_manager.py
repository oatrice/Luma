"""
credential_manager.py — Hybrid Credential Rotation for Luma CLI

Manages a mixed pool of Google API Keys and Gemini CLI OAuth Profiles.
Supports round-robin rotation with per-credential cooldown on 429 errors.
Now includes global cross-process cooldown synchronization via ~/.luma/cooldowns.json.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import List, Optional, Dict


# Global storage for cooldowns across processes
LUMA_HOME = os.path.expanduser("~/.luma")
COOLDOWN_FILE = os.path.join(LUMA_HOME, "cooldowns.json")


class CredentialType(str, Enum):
    API_KEY = "API_KEY"
    OAUTH_PROFILE = "OAUTH_PROFILE"


class AllCredentialsExhaustedError(RuntimeError):
    """Raised when every credential in the pool is currently rate-limited."""


def _load_global_cooldowns() -> Dict[str, float]:
    """Load cooldown map from ~/.luma/cooldowns.json"""
    if not os.path.exists(COOLDOWN_FILE):
        return {}
    try:
        with open(COOLDOWN_FILE, "r") as f:
            data = json.load(f)
            # Filter out expired cooldowns immediately
            now = time.time()
            return {k: v for k, v in data.items() if v > now}
    except Exception:
        return {}


def _save_global_cooldowns(cooldowns: Dict[str, float]) -> None:
    """Save cooldown map to ~/.luma/cooldowns.json"""
    try:
        os.makedirs(LUMA_HOME, exist_ok=True)
        # Load existing, merge with new, and filter expired
        existing = _load_global_cooldowns()
        existing.update(cooldowns)
        now = time.time()
        final = {k: v for k, v in existing.items() if v > now}
        
        with open(COOLDOWN_FILE, "w") as f:
            json.dump(final, f)
    except Exception:
        pass


@dataclass
class CredentialStatus:
    type: CredentialType
    value: str
    is_active: bool = True
    fail_count: int = 0
    cooldown_until: Optional[float] = None

    def is_available(self) -> bool:
        """Return True if the credential is ready to use."""
        now = time.time()
        
        # 1. Check local in-memory status first
        if not self.is_active:
            if self.cooldown_until is not None and now >= self.cooldown_until:
                self.is_active = True
                self.cooldown_until = None
            else:
                # Still in local cooldown
                return False
        
        # 2. Check global cooldown file for cross-process synchronization
        global_cooldowns = _load_global_cooldowns()
        if self.value in global_cooldowns:
            until = global_cooldowns[self.value]
            if now < until:
                # Sync local status with global if global is still in cooldown
                self.is_active = False
                self.cooldown_until = until
                return False
            else:
                # Global cooldown expired, we can potentially reuse it
                pass

        return self.is_active


class CredentialManager:
    """
    Manages a mixed pool of API Keys and OAuth Profiles.
    Now supports global cross-process cooldown synchronization.
    """

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

        duplicate_values: set[str] = set()
        seen_values: set[str] = set()
        for value in [*api_keys, *oauth_profiles]:
            if value in seen_values:
                duplicate_values.add(value)
            seen_values.add(value)

        if duplicate_values:
            duplicates = ", ".join(sorted(duplicate_values))
            raise ValueError(
                "Credential values must be unique across API keys and OAuth "
                f"profiles. Duplicates found: {duplicates}"
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
        Skips those currently in cooldown (checked globally).

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
                "All credentials are currently rate-limited across all Luma processes. "
                "Please add a new API key (from a different Google Account) "
                "or wait for the cooldown to expire."
            )

    def mark_rate_limited(self, value: str, retry_after: int = 60) -> None:
        """
        Mark a credential as rate-limited and persist to global file.

        Args:
            value: The API key string or OAuth profile name.
            retry_after: Seconds to wait before retrying. Defaults to 60.

        Raises:
            ValueError: If the credential is not in the pool.
        """
        until = time.time() + retry_after
        
        with self._pool_lock:
            status = self._get_status_unsafe(value)
            if status is None:
                raise ValueError(
                    f"Credential '{value}' not found in the pool."
                )
            # 1. Update in-memory pool
            status.is_active = False
            status.cooldown_until = until
            status.fail_count += 1
        
        # 2. Persist to global file for other processes
        _save_global_cooldowns({value: until})

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
        """Reset a specific named singleton."""
        with cls._lock:
            if name in cls._instances:
                del cls._instances[name]

    @classmethod
    def reset_all_instances(cls) -> None:
        """Reset all named singletons."""
        with cls._lock:
            cls._instances.clear()
