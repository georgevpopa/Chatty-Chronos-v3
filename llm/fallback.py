"""Multi-provider LLM fallback — try providers in order until one works.

Supports: Ollama (local) + any OpenAI-compatible cloud provider.
Rate-limit detection (429) triggers auto-switch to next provider.

Providers are loaded from ~/.chatty-chronos/providers.json (hot-reloaded).
API keys are loaded from .env files (hot-reloaded).
"""
import json
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
from rich.console import Console

console = Console()

PROVIDERS_FILE = Path.home() / ".chatty-chronos" / "providers.json"

# Default providers (used if providers.json doesn't exist)
DEFAULT_PROVIDERS = [
    {
        "name": "ollama",
        "type": "ollama",
        "is_local": True,
    },
    {
        "name": "groq",
        "type": "openai_compatible",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
    {
        "name": "gemini",
        "type": "openai_compatible",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
        "env_key": "GEMINI_API_KEY",
    },
    {
        "name": "mistral",
        "type": "openai_compatible",
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
        "env_key": "MISTRAL_API_KEY",
    },
    {
        "name": "openrouter",
        "type": "openai_compatible",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct",
        "env_key": "OPENROUTER_API_KEY",
    },
    {
        "name": "nvidia",
        "type": "openai_compatible",
        "base_url": "https://integrate.api.nvidia.com/v1",  # REVENIM LA CEL CU SSL VALID
        "model": "nvidia/llama-3.1-nemotron-70b-instruct",
        "env_key": "NVIDIA_API_KEY",
    },
]


def _load_providers() -> list[dict]:
    """Load providers from ~/.chatty-chronos/providers.json (or use defaults).
    Creates or updates the file with defaults if a new provider is missing.
    """
    if PROVIDERS_FILE.exists():
        with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
            try:
                loaded = json.load(f)
                # Sincronizare: Dacă am adăugat nvidia în cod dar nu există în JSON-ul vechi, forțăm rescrierea
                loaded_names = {p["name"] for p in loaded}
                default_names = {p["name"] for p in DEFAULT_PROVIDERS}
                if not default_names.issubset(loaded_names):
                    raise ValueError("New provider detected in code configs.")
                return loaded
            except Exception:
                pass

    # Create or overwrite default providers.json
    PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROVIDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_PROVIDERS, f, indent=2)
    return list(DEFAULT_PROVIDERS)


def _reload_env():
    """Hot-reload .env files so new keys are picked up without restart."""
    load_dotenv(Path.cwd() / ".env", override=True)
    load_dotenv(Path.home() / ".chatty-chronos" / ".env", override=True)


def get_available_providers() -> list[dict]:
    """Return providers with status (hot-reloads .env and providers.json)."""
    _reload_env()
    providers = _load_providers()
    available = []
    for p in providers:
        if p.get("is_local"):
            available.append({**p, "status": "local"})
        elif p.get("env_key") and os.environ.get(p["env_key"]):
            available.append({**p, "status": "configured"})
        else:
            available.append({**p, "status": "no_key"})
    return available


def list_nvidia_models() -> list[str]:
    """Fetch active model catalog directly from NVIDIA endpoint using current environment key."""
    _reload_env()
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key:
        return []
    
    url = "https://integrate.api.nvidia.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        with httpx.Client(timeout=15) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                # Extragem ID-urile modelelor care vin din JSON-ul listat în PowerShell
                return [model["id"] for model in data.get("data", [])]
    except Exception:
        pass
    return []


def call_cloud_provider(messages: list, provider: dict) -> str:
    """Call an OpenAI-compatible cloud provider. Returns response text."""
    api_key = os.environ.get(provider["env_key"], "")
    if not api_key:
        raise ValueError(f"No API key for {provider['name']} (set {provider['env_key']})")

    url = f"{provider['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": provider["model"],
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages if m.get("content")],
        "max_tokens": 4096,
    }

    with httpx.Client(timeout=60) as client:
        response = client.post(url, json=payload, headers=headers)

        if response.status_code == 429:
            raise RateLimitError(f"{provider['name']} rate limited (429)")
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]


def chat_with_fallback(messages: list, config) -> str:
    """Try providers in order. Fall back on failure/rate-limit. Hot-reloads everything."""
    _reload_env()
    from llm import ollama_provider

    providers = get_available_providers()
    errors = []

    for provider in providers:
        try:
            if provider["type"] == "ollama":
                response = ollama_provider.chat(messages, config.get("model"), config.get("ollama_host"))
                return response.message.content or ""
            elif provider["status"] == "configured":
                return call_cloud_provider(messages, provider)
        except RateLimitError as e:
            errors.append(f"{provider['name']}: rate limited")
            console.print(f"  [yellow]{provider['name']}: rate limited, trying next...[/yellow]")
            continue
        except Exception as e:
            errors.append(f"{provider['name']}: {str(e)[:50]}")
            continue

    raise RuntimeError(f"All providers failed: {'; '.join(errors)}")


class RateLimitError(Exception):
    pass