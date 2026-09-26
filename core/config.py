"""Configuration manager — persistent settings in ~/.chatty-chronos/config.json."""
import json
import os
from pathlib import Path
from pydantic import BaseModel, Field

class AppConfigSchema(BaseModel):
    # Provider defaults: local-first. Ollama is the zero-config default so a fresh
    # install works out of the box against a local Ollama on :11434. Cloud providers
    # and OmniRoute are opt-in (configured by the user in providers.json / .env).
    provider: str = "ollama"
    model: str = ""  # empty -> auto-detect first available local model at runtime
    base_url: str = ""  # empty -> derived from provider (ollama_host by default)
    ollama_host: str = "http://localhost:11434"
    llamacpp_host: str = "http://localhost:8080"
    embedding_provider: str = "local"
    embedding_model: str = "all-MiniLM-L6-v2"
    streaming: bool = True
    max_context_messages: int = 20
    local_server_enabled: bool = False
    local_server_bin: str = ""  # user sets path to their llama-server binary if used
    local_server_model: str = ""
    local_server_port: int = 8080
    local_server_ngl: int = 99
    local_server_ctx: int = 16384
    local_server_parallel: int = 1
    local_server_reasoning_budget: int = 1024
    local_server_cache_ram: int = 512
    llamacpp_timeout: int = 600
    agent_max_iterations: int = 30
    # Extra environment variables passed to a self-launched local server.
    # Empty by default; hardware-specific vars (e.g. AMD ROCm HSA_OVERRIDE_GFX_VERSION)
    # are opt-in and set by the user for their machine.
    local_server_env: dict = Field(default_factory=dict)
    compaction_enabled: bool = True
    self_reflection: bool = False
    enable_reflection: bool = True
    show_incantation: bool = True  # startup awakening incantation (typewriter)


class Config:
    def __init__(self):
        self.dir = Path.home() / ".chatty-chronos"
        self.dir.mkdir(exist_ok=True)
        self.path = self.dir / "config.json"
        self._schema = self._load()

    @property
    def data(self):
        return self._schema.model_dump()

    def _load(self) -> AppConfigSchema:
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    saved = json.load(f)
                return AppConfigSchema(**saved)
            except Exception:
                return AppConfigSchema()
        return AppConfigSchema()

    def save(self):
        with open(self.path, "w") as f:
            f.write(self._schema.model_dump_json(indent=2))

    def get(self, key, default=None):
        return getattr(self._schema, key, default)

    def set(self, key, value):
        setattr(self._schema, key, value)
        self.save()