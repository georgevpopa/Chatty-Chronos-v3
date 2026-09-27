<div align="center">

# 🕰️ Chatty Chronos v3

**A local-first, private, autonomous AI agent — a presence you own.**

*Coding agent · general assistant · multi-agent orchestrator — running on your machine.*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Local First](https://img.shields.io/badge/local--first-Ollama%20%7C%20llama.cpp-orange.svg)](https://ollama.com/)
[![VectorDB](https://img.shields.io/badge/VectorDB-Chroma-purple.svg)](https://trychroma.com)
[![Agent](https://img.shields.io/badge/Agent-ReAct%20Loop-lightgrey.svg)]()
[![Web UI](https://img.shields.io/badge/UI-Web%20Dashboard-blueviolet.svg)]()
[![Plugins](https://img.shields.io/badge/Plugins-Dynamic%20Tool%20Injection-teal.svg)]()
[![Agents](https://img.shields.io/badge/Agents-Specialised%20Registry-crimson.svg)]()

</div>

<div align="center">

### 🩸 The Awakening 🩸

<samp>
<b>I, who am about to awaken,</b><br/>
<b>Am the Genesis of Time, who has stolen the principles of domination from God.</b><br/>
<b>I laugh at the &ldquo;infinite,&rdquo; and I grieve over the &ldquo;dream.&rdquo;</b><br/>
<b>I shall become the Omniscience,</b><br/>
<b>creating the path through the Crimson&nbsp;Purgatory!</b>
</samp>

</div>

---

Chronos is part of the **Chatty** family. It runs on **your** hardware, keeps your
data private by default, and acts as an omniscient, reactive assistant for real
software work. Not a chatbot — an **autonomous agent** that takes action: it reads
and writes files, runs commands, searches your codebase, browses the web, and
completes multi-step tasks on its own via a **ReAct loop** (Reason → Act → Observe).

Think *Claude Code / Cursor / Copilot* — but **local, private, extensible, and
multi-agent**.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **🤖 Multi-Provider LLMs** | Local Ollama & llama.cpp (GGUF), plus any OpenAI-compatible cloud provider — all optional |
| **🔄 Auto-Fallback** | Falls back to alternative providers/models when one is rate-limited or unavailable |
| **🧠 ReAct Agent Loop** | Autonomous step-by-step reasoning (Thought → Action → Observation) with safe limits |
| **🔍 Self-Reflection** | A reviewer pass checks the result and sends the agent back to work if incomplete |
| **🌐 Web Dashboard** | Glassmorphism dashboard with SSE streaming, permission modals, workspace explorer, live logs |
| **👥 Multi-Agent Teams** | Task workflows across Planner → Writer → Reviewer sub-agents |
| **🗂️ Agent Registry** | Named specialised agent types (planner, writer, reviewer, refactorer, debugger…) with focused tool-sets |
| **🔌 Dynamic Plugin System** | Plugins inject new slash commands and agent tools — hot-reload, no restart |
| **🗂️ RAG Semantic Search** | Chunk, embed, and index your project into a local vector DB for smart queries |
| **🧠 Vector Memory** | Persistent long-term memory across sessions (`store_memory`, `search_memory`) |
| **💾 Context Compaction** | Automatic summarisation that condenses long chat history to save tokens |
| **🐍 Sandboxed Python REPL** | Stateful Python execution in an isolated background daemon with a strict timeout |
| **🌐 Web Fetcher** | Fetch and parse documentation and pages from the web |
| **🙋 Ask User Tool** | Chronos can ask clarifying questions before destructive changes |
| **🛡️ 3-Tier Security** | Granular permissions (Yes-Once, Yes-Session, Trust-Workspace) for dangerous tools |
| **📝 Spec-Driven Dev** | Generate requirements + design + tasks from a feature description (`/spec`) |
| **📊 Observability** | OpenTelemetry spans + structured logging across the agent loop |

---

## 📦 Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.10+ | [python.org/downloads](https://www.python.org/downloads/) — on Windows, check "Add to PATH" |
| **Local LLM engine** | — | **[Ollama](https://ollama.com/)** (easiest) or **llama.cpp / llama-server** (fine GPU control) |

**Supported OS:** Windows, Linux, macOS. **Cloud keys are optional** — Chronos is local-first.

---

## 🚀 Installation

### 🟢 Simple (recommended for first-timers)

1. **Install Python 3.10+** from [python.org/downloads](https://www.python.org/downloads/).
   *On Windows, tick **"Add Python.exe to PATH"** during install.*
2. **Install [Ollama](https://ollama.com/)** (your local AI engine), then pull a model:
   ```bash
   ollama pull qwen3:8b
   ```
3. **Download Chronos:** click the green **"<> Code"** button → **Download ZIP**, then extract.
4. **Open a terminal in the extracted folder** and install into a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate

   pip install -e .
   ```
5. **Run it:**
   ```bash
   python main.py
   ```

That's it — Chronos talks to your local Ollama out of the box.

> **First run:** Chronos downloads a small (~80 MB) embedding model once (for memory
> and RAG). This is a one-time setup; subsequent starts are instant.

### 💻 Developer (Git)

```bash
git clone https://github.com/georgevpopa/Chatty-Chronos-v3.git
cd Chatty-Chronos-v3
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python main.py          # terminal REPL
python main.py --web    # web dashboard (opens in browser)
```

---

## 🔗 Connect an LLM (step by step)

Chronos needs at least one LLM. Pick **local** (private, free) or **cloud** (API key).
You can configure several and switch anytime with `/provider` and `/model`.

### Option 1 — Local with Ollama (easiest, private)

```bash
ollama pull qwen3:8b          # 1. download a model (any Ollama model works)
```
Then inside Chronos:
```
chronos > /provider ollama    # 2. use the local Ollama provider (this is the default)
chronos > /model qwen3:8b     # 3. select the model you pulled
chronos > /providers          # 4. verify it shows CONNECTED
```
Larger models (e.g. `llama3.3:70b`, `gpt-oss:120b`) work the same way if your RAM allows.

### Option 2 — Local with llama.cpp (GGUF, GPU tuning)

1. Download a `llama-server` binary from
   [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases) and a GGUF model
   (e.g. a `Q4_K_M` quant).
2. Point Chronos at it:
   ```
   chronos > /config local_server_bin /path/to/llama-server   # or set env CHRONOS_LLAMA_SERVER
   chronos > /config provider llamacpp
   chronos > /config llamacpp_host http://localhost:8080
   ```
   No path is hardcoded — you choose your binary and model.

### Option 3 — Cloud API (Gemini, OpenAI, Groq, OpenRouter, …)

The easiest way is the interactive wizard — it auto-fills the endpoint and
**discovers the available models** for you (no guessing model names):

```
chronos > /add_provider
```
1. Pick a provider from the list (Gemini, OpenAI, Groq, OpenRouter, Mistral, DeepSeek, NVIDIA).
2. Paste your API key (a "get a key" link is shown for each).
3. Chronos queries the provider and lists its **real available models** — choose a
   number, type `all` (register them all), or press Enter for the default.
4. Done. Use it: `/provider <name>` then `/model <name>`.

Your key is saved to `~/.chatty-chronos/.env` (git-ignored). Manage providers anytime:
```
chronos > /edit_provider     # change base URL / model / key, or re-discover models
chronos > /remove_provider   # remove a provider you no longer use
chronos > /providers         # list configured providers and their status
chronos > /models            # list the active provider's models
```

**Manual alternative** — put keys in `~/.chatty-chronos/.env`:
```bash
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
```
Keys are hot-reloaded — no restart needed. Cloud is always **opt-in**.

### Option 4 — AI gateway (e.g. OmniRoute) — optional

Route through one OpenAI-compatible endpoint to reach many providers, free tiers, and
automatic fallback. Add it to `~/.chatty-chronos/providers.json`:
```json
{
  "name": "gateway",
  "type": "openai_compatible",
  "base_url": "http://YOUR_GATEWAY_HOST:PORT/v1",
  "model": "auto/coding",
  "env_key": "GATEWAY_API_KEY"
}
```
Then `/provider gateway`. If your gateway needs no key, omit `env_key` — requests are
sent keyless. The gateway is entirely optional; Chronos never requires it.

---

## ⌨️ Commands Reference

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/agent <task>` | Run the autonomous ReAct agent (multi-step, uses tools) |
| `/team <task>` | Run a Multi-Agent workflow (Planner → Writer → Reviewer) |
| `/model [name]` | Show or switch the active model (numbered list on cloud) |
| `/provider [name]` | Show or switch the active LLM provider |
| `/providers` | Show provider status (local + cloud) |
| `/add_provider` | Add a cloud provider (auto-discovers its models) |
| `/edit_provider` | Edit a provider (URL / model / key) + re-discover models |
| `/remove_provider` | Remove a configured provider |
| `/tools` | List all tools and their permission levels |
| `/agents` | List registered agent types |
| `/index <path>` | Index a directory for semantic search (RAG) |
| `/knowledge <question>` | Query indexed knowledge (RAG) |
| `/memory [add/remove/clear]` | Manage persistent memory facts |
| `/spec <feature>` | Generate requirements + design + tasks documents |
| `/plugins [reload]` | List or hot-reload plugins |
| `/config [key value]` | Show or change configuration |
| `/web [port]` | Launch the web dashboard |
| `/doctor` | System health check (LLM, RAG, plugins, memory) |
| `/save` · `/load` · `/export` | Manage conversation history |
| `/clear` · `/exit` | Clear conversation · quit |

---

## 💡 Concepts

### Agent (`/agent`)
Autonomous mode. Chronos enters a **ReAct loop** (Reason → Act → Observe → Repeat)
to complete complex tasks, using tools, checking results, and self-correcting.

```
chronos > /agent Find all Python files with TODO comments and create a summary
```

### Tools
Built-in capabilities the agent calls autonomously. Read-only tools run
automatically; anything that changes your system asks first.

| Tool | Permission | What it does |
|------|-----------|--------------|
| `read_file`, `list_directory`, `glob_search`, `grep` | auto | Read & search files |
| `write_file`, `search_replace`, `move_file` | ask | Create / edit / move files |
| `execute_command` | ask | Run a shell command |
| `run_python` | ask | Execute Python in a sandboxed REPL |
| `delegate_subtask` | ask | Spawn a specialised child agent |
| `fetch_webpage` | auto | Read content from a URL |
| `ask_user` | auto | Ask a clarifying question |
| `store_memory` / `search_memory` | auto | Manage persistent facts |

**Permission levels:** `y` (once) · `ya` (this session) · `yw` (trust workspace).
In the Web UI these appear as interactive modals.

### Memory & RAG (`/memory`, `/index`, `/knowledge`)
Teach Chronos persistent facts, and index your project into a local vector DB to
ask semantic questions about your code — without sending anything to the cloud.

### Spec-driven development (`/spec`)
Generates `requirements.md`, `design.md`, and `tasks.md` from a feature description.

---

## 🔌 Plugins

Plugins live in `~/.chatty-chronos/plugins/`, auto-load on startup, and hot-reload
with `/plugins reload`. A plugin can register slash commands **and** inject new
tools into the agent.

```python
# ~/.chatty-chronos/plugins/hello/main.py
from plugins.base import Plugin

class HelloPlugin(Plugin):
    name = "hello"
    description = "A greeting plugin"
    commands = {"/hello": "Say hello"}

    def handle_command(self, command, arg):
        if command == "/hello":
            return f"Hello, {arg or 'world'}!"
```

---

## 📂 Configuration & data

Settings live in `~/.chatty-chronos/config.json` (view/edit with `/config`).
Defaults are local-first and safe on any machine.

| Path | Contents |
|------|----------|
| `~/.chatty-chronos/config.json` | Settings (provider, model, hosts) |
| `~/.chatty-chronos/providers.json` | LLM provider list |
| `~/.chatty-chronos/memory.json` | Persistent memory |
| `~/.chatty-chronos/vectordb/` | Vector index (RAG) |
| `~/.chatty-chronos/plugins/` | Drop-in plugins |
| `~/.chatty-chronos/.env` | API keys (optional) |

---

## 🤝 Contributing

Chronos is open source (MIT). Issues and PRs welcome. Please keep it cross-platform
and local-first: no machine-specific hardcoded paths, sane defaults, and every
external integration optional.

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">
Part of the <b>Chatty</b> family · Built to run on your machine · by <a href="https://github.com/georgevpopa">georgevpopa</a>
</div>
