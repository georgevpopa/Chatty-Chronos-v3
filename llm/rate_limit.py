"""Rate-limit rotation — auto-switch providers on 429 errors.

Ported from chatty-local-claude. Tracks per-provider request counts
and rotates to the next available provider when limits are hit.
"""
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class ProviderState:
    name: str
    env_key: str
    rpm_limit: int
    request_times: list[float] = field(default_factory=list)
    disabled_until: float = 0.0

    @property
    def is_available(self) -> bool:
        if time.time() < self.disabled_until:
            return False
        if not os.environ.get(self.env_key):
            return False
        return True

    def record_request(self) -> None:
        now = time.time()
        self.request_times.append(now)
        # Keep only requests from the last 60 seconds
        self.request_times = [t for t in self.request_times if now - t < 60]

    @property
    def current_rpm(self) -> int:
        now = time.time()
        return sum(1 for t in self.request_times if now - t < 60)

    @property
    def is_rate_limited(self) -> bool:
        return self.current_rpm >= self.rpm_limit


# Provider registry with RPM limits
PROVIDERS = [
    ProviderState("ollama", "", rpm_limit=999),  # Local, no limit
    ProviderState("nvidia_nim", "NVIDIA_NIM_API_KEY", rpm_limit=40),
    ProviderState("groq", "GROQ_API_KEY", rpm_limit=30),
    ProviderState("cerebras", "CEREBRAS_API_KEY", rpm_limit=30),
    ProviderState("gemini", "GEMINI_API_KEY", rpm_limit=15),
    ProviderState("mistral", "MISTRAL_API_KEY", rpm_limit=60),
    ProviderState("openrouter", "OPENROUTER_API_KEY", rpm_limit=20),
]


class RateLimitRotator:
    """Rotates through providers, avoiding rate-limited ones."""

    def __init__(self):
        self._reload_env()
        self._providers = list(PROVIDERS)

    def _reload_env(self) -> None:
        load_dotenv(Path.cwd() / ".env", override=True)
        load_dotenv(Path.home() / ".chatty-chronos" / ".env", override=True)

    def get_next_provider(self, exclude: str | None = None) -> ProviderState | None:
        """Get the next available provider, skipping rate-limited ones."""
        self._reload_env()

        for provider in self._providers:
            if provider.name == exclude:
                continue
            if provider.is_available and not provider.is_rate_limited:
                return provider

        return None

    def mark_rate_limited(self, provider_name: str, retry_after: int = 60) -> None:
        """Mark a provider as rate-limited."""
        for p in self._providers:
            if p.name == provider_name:
                p.disabled_until = time.time() + retry_after
                break

    def record_request(self, provider_name: str) -> None:
        """Record a successful request for rate tracking."""
        for p in self._providers:
            if p.name == provider_name:
                p.record_request()
                break

    def get_status(self) -> list[dict]:
        """Get status of all providers."""
        self._reload_env()
        status = []
        for p in self._providers:
            status.append({
                "name": p.name,
                "available": p.is_available,
                "rate_limited": p.is_rate_limited,
                "rpm": p.current_rpm,
                "rpm_limit": p.rpm_limit,
            })
        return status
