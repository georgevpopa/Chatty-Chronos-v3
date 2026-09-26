<div align="center">

# 🕰️ Chatty Chronos v3

**A local-first, private, autonomous AI agent — a presence you own.**

*Coding agent · general assistant · multi-agent orchestrator — running on your machine.*

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Local First](https://img.shields.io/badge/local-first-orange.svg)](#)

</div>

---

> *I, who am about to awaken,*
> *Am the Genesis of Time, who has stolen the principles of domination from God.*
> *I laugh at the "infinite," and I grieve over the "dream."*
> *I shall become the Omniscience.*

Chronos is part of the **Chatty** family of tools. It runs on **your** hardware,
keeps your data private by default, and reaches toward being an omniscient,
reactive assistant for real software work.

## ✨ What Chronos is

Not just a chatbot — an **autonomous agent** that takes action. It reads and writes
files, runs commands, searches your codebase, browses the web, and completes
multi-step tasks on its own, using a **ReAct loop** (Reason → Act → Observe).

It spans three roles:
- **Coding agent** — writes, edits, runs, and debugs code.
- **General assistant** — reasoning, writing, research.
- **Multi-agent orchestrator** — delegates to specialized sub-agents and runs
  team workflows (planner → writer → reviewer).

Think *Claude Code / Cursor / Copilot* — but **local, private, extensible, and
multi-agent**.

## 🧭 Design pillars

1. **Local-first & private** — runs against a local LLM (Ollama / llama.cpp) by
   default. Nothing leaves your machine unless you opt into a cloud provider.
2. **Plugin-first & extensible** — add slash commands and agent tools via drop-in
   plugins, hot-reloaded without a restart.
3. **Intelligent routing (optional)** — point Chronos at an OpenAI-compatible
   gateway for many providers, free tiers, and auto-fallback. Optional, never required.
4. **Fast, cheap decisions (optional)** — an optional decision layer for in-loop
   choices, falling back to the LLM when not configured.
5. **Multi-agent** — a registry of specialized agent types, each with a focused
   tool-set and prompt.
6. **Reactive & self-improving** — self-reflection reviewer loop, cross-session
   memory, RAG over your project, and web lookups when its knowledge is stale.

## 🚀 Quick start

Requirements: **Python 3.10+** and a local LLM engine (**[Ollama](https://ollama.com)**
recommended to start).

```bash
# 1. Get a local model (example)
ollama pull qwen3:8b

# 2. Install Chronos
git clone https://github.com/georgevpopa/Chatty-Chronos-v3.git
cd Chatty-Chronos-v3
pip install -e .

# 3. Run
chronos            # or: python main.py
```

Chronos is **local-first**: out of the box it talks to Ollama on
`http://localhost:11434`. On first run it uses your first available local model.

### Web dashboard

```bash
python main.py --web    # opens the browser dashboard
```

## 🔌 Using cloud providers (optional)

Chronos works with zero cloud keys. If you want cloud models, add API keys to a
`.env` file in the project root, or point Chronos at an OpenAI-compatible gateway:

```bash
# .env  (never commit this file)
GROQ_API_KEY=...
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
```

Any OpenAI-compatible endpoint (including self-hosted gateways) can be configured
as a provider. Cloud is always **opt-in**.

## 🧩 Plugins

Drop a plugin folder into `~/.chatty-chronos/plugins/` with a `plugin.json`
manifest and a `main.py`. A plugin can register slash commands and inject new
tools into the agent — hot-reloadable with `/plugins reload`.

## 🛠️ Key features

- ReAct autonomous agent loop with a self-reflection reviewer
- Built-in tools: file read/write/edit, glob, grep, shell, web fetch, sandboxed
  Python REPL, memory, sub-agent delegation
- Specialized agent registry (planner, writer, reviewer, refactorer, debugger, …)
- Multi-agent team workflows
- RAG semantic search over your project (local embeddings + vector store)
- Cross-session persistent memory
- Spec-driven development (`/spec` → requirements, design, tasks)
- 3-tier permission model for dangerous operations
- Web dashboard with live streaming
- OpenTelemetry + structured logging

## 📂 Configuration

Settings live in `~/.chatty-chronos/config.json`. Inspect or change them with the
`/config` command inside Chronos, or edit the file directly. Defaults are
local-first and safe on any machine.

## 🤝 Contributing

Chronos is open source (MIT). Issues and pull requests are welcome. Please keep the
product cross-platform and local-first: no machine-specific hardcoded paths, sane
defaults, and every external integration optional.

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">
Part of the <b>Chatty</b> family · Built to run on your machine.
</div>
