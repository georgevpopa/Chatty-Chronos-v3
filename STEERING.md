# STEERING.md — Chatty Chronos Project Context

## Project Identity
- Name: Chatty Chronos v3
- Type: Terminal-first autonomous coding agent
- Language: Python 3.10+
- Primary OS: Windows (also works on Linux/macOS)
- Default LLM: Ollama (local-first, privacy-focused)

## Coding Style
- Type hints on all function signatures
- Docstrings on all public classes and functions
- Use `pathlib.Path` over `os.path`
- Use `rich` for terminal output formatting
- Keep modules focused and small (single responsibility)
- Error messages should be helpful and suggest fixes

## Architecture Rules
- All LLM providers go in `llm/`
- All tools go in `tools/`
- Core logic (agent, config, permissions, memory) in `core/`
- Plugins are loaded from `~/.chatty-chronos/plugins/`
- User data stored in `~/.chatty-chronos/`
- Never store API keys in code — use .env or environment variables

## Key Patterns
- ReAct loop for autonomous tasks (Think → Act → Observe → Repeat)
- 3-tier permission model for dangerous operations
- Ollama as primary, cloud providers as fallback
- ChromaDB for vector storage, Ollama nomic-embed-text for embeddings
- Spec-driven development (requirements → design → tasks → code)

## Testing
- Quick smoke test: `python main.py` then `/doctor`
- All modules should import cleanly without side effects
- Tools should be testable in isolation
