# 📚 Chatty Chronos v3 - Master Documentation

> This is the unified master documentation file covering everything from installation to advanced usage, plugins, and architecture.

## 📑 Table of Contents
- [1. Introduction & Features](#1-introduction--features)
- [2. Standard Installation Guide](#2-standard-installation-guide)
- [3. Docker & Multi-Engine Guide](#3-docker--multi-engine-guide)
- [4. How to Use & Commands](#4-how-to-use--commands)
- [5. Project Architecture & Guidelines](#5-project-architecture--guidelines)
- [6. Future Roadmap](#6-future-roadmap)

---

<a id='1-introduction--features'></a>
# 1. Introduction & Features

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/georgevpopa/Chatty-Chronos-v2?style=social)](https://github.com/georgevpopa/Chatty-Chronos-v2/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/georgevpopa/Chatty-Chronos-v2?style=social)](https://github.com/georgevpopa/Chatty-Chronos-v2/network/members)
[![Local First](https://img.shields.io/badge/local--first-Ollama%20%7C%20llama.cpp-orange.svg)](https://ollama.com/)
[![VectorDB](https://img.shields.io/badge/VectorDB-Chroma-purple.svg)](https://trychroma.com)
[![ReAct Mode](https://img.shields.io/badge/Agent-ReAct%20Loop-lightgrey.svg)]()
[![Web UI](https://img.shields.io/badge/UI-Web%20Dashboard-blueviolet.svg)]()
[![Plugin System](https://img.shields.io/badge/Plugins-Dynamic%20Tool%20Injection-teal.svg)]()
[![Agent Registry](https://img.shields.io/badge/Agents-Specialised%20Registry-crimson.svg)]()

> A terminal-first autonomous coding agent. Chat with AI, execute tasks, search codebases, generate specs — and now extend everything with MCP, plugins, and a Multi-Agent Swarm. Runs locally with Ollama/llama.cpp or falls back to cloud LLMs.

---

## ✨ What's new in v2 (The Big 5 Improvements)

| Improvement | Description |
|---|---|
| **🔒 Sandboxed Execution** | Python REPL runs in `RestrictedPython` in an isolated IPC background subprocess. Plugins now require strict `plugin.json` manifests declaring their capabilities. |
| **🗃️ Pydantic v2 Core** | Complete refactoring of config, internal schemas, and `Tools` (inputs now fully typed & validated with Pydantic `BaseModel`). |
| **📊 OpenTelemetry & Structlog** | The entire ReAct Loop (Thought → Action → Observation) is instrumented with `opentelemetry-api` spans and `structlog` for deep observability. View traces via `/api/traces` in the Web UI. |
| **🧪 Pytest Suite & LLM Mocking** | Deep test coverage with `pytest`, property-based testing with `hypothesis` for file IO idempotency, and full ReAct loop mocked integrations. |
| **🐳 Docker & DevOps** | Shipped with a multi-stage `Dockerfile`, a `docker-compose.yml` for unified App+ChromaDB+Ollama boot, and VS Code `.devcontainer` support! |

---

## 🌟 Standard Features

| Feature | Description |
|---------|-------------|
| **🤖 Multi-Provider LLMs** | Ollama (local), llama.cpp (local GGUF auto-launcher), Nvidia NIM, Google Gemini, Groq Cloud, OpenRouter |
| **🔄 Auto-Fallback** | Instantly falls back to alternative providers/models when a service is rate-limited or unavailable |
| **🧠 ReAct Agent Loop** | Autonomous step-by-step reasoning loop (Thought → Action → Observation) with safe limits |
| **🌐 Web Dashboard** | Glassmorphism dashboard with SSE streaming, permission modals, workspace explorer, and live log console |
| **🕸️ Multi-Agent Swarm UI** | A visual Swarm dashboard that tracks tasks moving between Planner, Writer, and Reviewer sub-agents |
| **🔌 MCP Protocol Support** | Instantly consume any MCP server (Model Context Protocol) to add new tools to Chronos (`/mcp add`) |
| **💾 Multi-Session History** | Save, load, delete, and manage multiple chat histories dynamically from the sidebar |
| **📊 Hardware Monitor** | iGPU / RAM telemetry card showing system loads and background `llama-server` VRAM footprint |
| **💾 Context Compaction** | LLM-driven summarisation that automatically condenses long chat history to save context tokens |
| **🗂️ RAG Semantic Search** | Chunk, embed, and index files into a local ChromaDB database for smart project queries |
| **🧠 Vector Memory** | Persistent long-term memory for agent preferences and facts via ChromaDB (`store_memory`, `search_memory`) |
| **👥 Specialised Sub-Agents** | Delegate to typed child agents (file_analyst, shell_runner, writer, researcher) each with focused tool-sets |
| **🐍 Sandboxed Python REPL** | Secure, stateful Python REPL running in an isolated background daemon with a strict timeout limit |
| **🌐 Web Fetcher** | Fetch and parse documentation dynamically from the web |
| **🙋 Ask User Tool** | Chronos can ask the user clarifying questions before making destructive changes |
| **🔌 Dynamic Plugin System** | Plugins inject new slash commands and new agent tools. Hot-reload without restarting |
| **🗂️ Agent Registry** | Register, discover and instantiate named agent types at runtime or from plugins |
| **🛡️ 3-Tier Security** | Granular execution security (Yes-Once, Yes-Session, Trust Workspace Permanently) for dangerous tools |
| **🖥️ Interactive Web Permissions** | Tool permission requests surface as interactive modals in the browser — no terminal needed |
| **📋 Git Auto-Commit UI** | View `git status` visually in the dashboard and ask Chronos to generate conventional commit messages |

---

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.10+ | [python.org/downloads](https://www.python.org/downloads/) — check "Add to PATH" |
| **Local LLM Engine** | - | **llama.cpp / llama-server** (Recommended for GPU hardware acceleration) OR **Ollama** |

**Supported OS:** Windows (primary), Linux, macOS

---

## 🚀 Installation (Simple Guide for Windows)

No terminal experience required! Just follow these steps:

1. **Install Python:** Download Python 3.10+ from [python.org/downloads](https://www.python.org/downloads/). 
   *⚠️ CRITICAL: During installation, you MUST check the box that says **"Add Python.exe to PATH"** at the bottom of the installer window!*
2. **Download Chatty Chronos:** Click the green **"<> Code"** button at the top of this GitHub page and select **"Download ZIP"**.
3. **Extract the folder:** Right-click the downloaded ZIP file and select "Extract All...".
4. **Install:** Open the extracted folder and double-click the **`Install_Windows.bat`** file. A window will appear and install everything automatically.
5. **Get the AI Brain:** Download and install [Ollama](https://ollama.com/) (it's a simple installer). Once installed, it runs in your taskbar.

That's it! To play with Chronos, just double-click **`Start_Chronos.bat`** in the folder!

---

## 💻 Advanced / Developer Installation

If you prefer the command line or are on Linux/macOS, use these instructions.

### 🐧 Linux & 🍏 macOS

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git curl

# macOS
brew install python git

# Clone and Deploy
git clone https://github.com/georgevpopa/Chatty-Chronos-v1.git
cd Chatty-Chronos-v1
python3 deploy.py
```

### 🪟 Windows (via Git)

```bash
git clone https://github.com/georgevpopa/Chatty-Chronos-v1.git
cd Chatty-Chronos-v1
python deploy.py
```

*Deploy options (CLI):*
```bash
python deploy.py --skip-models      # Don't pull Ollama models
python deploy.py --path "D:\mypath" # Install to specific directory
python deploy.py --update           # Update existing install
```

---

### 🧠 Setting Up Local AI Brains

#### **Option A: llama.cpp / llama-server (Recommended for AMD & NVIDIA GPUs)**
1. Download a pre-compiled `llama-server` binary for your OS from [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases).
2. Download a GGUF model (e.g. `Qwen3.5-9B-Instruct-Q4_K_M.gguf`) and save it locally.
3. On Windows, double-click `Start_Chronos.bat`. It will prompt you to select the GGUF model and launch `llama-server.exe` automatically on port `8069` with hardware optimisations.

#### **Option B: Ollama (Simple alternative)**
```bash
# Windows/macOS: Download installer from https://ollama.com
# Linux:
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.1
ollama pull nomic-embed-text
```

### Uninstall

```bash
cd Chatty-Chronos-v1
python uninstall.py          # Interactive — asks what to remove
python uninstall.py --all    # Remove everything including user data
```

---

## 🚀 Starting Commands & Environments

Chronos v3 offers multiple ways to run, test, and deploy the application.

### 1. Standard Run (CLI or Web GUI)
Run Chronos natively on your host machine (requires Python 3.10+).

```bash
# Terminal REPL (CLI Mode)
python main.py

# Web Dashboard with GUI (auto-opens browser on http://localhost:8000)
python main.py --web

# Windows Users — double-click the starter batch file
Start_Chronos.bat
```

### 2. Docker & Docker Compose (Containerized Ecosystem)
Launch the entire ecosystem (Chronos App + ChromaDB + Ollama sidecar) fully isolated from your host system.
Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
# Build and start all services in the background
docker-compose up --build -d

# View the live logs of the Chronos app
docker-compose logs -f chronos

# Stop the ecosystem
docker-compose down
```

### 3. Running the Test Suite (`pytest`)
Chronos v3 includes a comprehensive test suite to validate the Agent ReAct loop, sandboxed tools, and Pydantic schemas.

**Step 1: Install testing dependencies**
```bash
pip install pytest hypothesis
```

**Step 2: Run the automated tests**
```bash
# Run all tests in the project
pytest tests/

# Run specific files with verbose output
pytest tests/test_filesystem.py -v
pytest tests/test_agent.py -v
```

### 🌐 Web UI Dashboard

Chronos ships with a premium glassmorphism web interface accessible from any browser:

```bash
python main.py --web        # starts on http://localhost:8000
# or from within the REPL:
chronos > /web
```

**New in the Web UI:**
- **Interactive Permission Modals** — tool execution requests pop up as browser dialogs with Allow Once / Allow Session / Trust Workspace / Deny buttons
- **Workspace Explorer & Git UI** — browse files and view real-time Git status with AI-generated commit messages
- **Multi-Agent Swarm Tab** — watch in real-time as tasks are passed between Planner, Writer, and Reviewer
- **Live Log Console** — view `chronos.log` + `llama_server.log` in real time (📋 button)
- **GGUF Server Restart** — restart `llama-server` without leaving the browser

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/model [name]` | Show or switch the active model |
| `/provider [name]` | Show or switch the active LLM provider |
| `/models` | List available models for current provider |
| `/tools` | List all tools and their permission levels |
| `/agent <task>` | Run autonomous ReAct agent (multi-step, uses tools) |
| `/team <task>` | Pass a task through a Multi-Agent Swarm (Planner → Writer → Reviewer) |
| `/mcp add <name> <cmd>` | Connect an MCP server to add tools to Chronos (e.g. `/mcp add fetch npx -y @anthropic-ai/fetch-server`) |
| `/web [port]` | Launch the interactive web dashboard |
| `/index <path>` | Index a directory for semantic search (RAG) |
| `/index_web <url>` | Index a web page into the knowledge base |
| `/knowledge <question>` | Query indexed knowledge (RAG) |
| `/memory` | Show persistent memory facts |
| `/memory add <fact>` | Teach Chronos a persistent fact |
| `/memory remove <n>` | Remove a fact by index |
| `/memory clear` | Clear all memory |
| `/spec <feature>` | Generate requirements + design + tasks documents |
| `/specs` | List existing specs |
| `/providers` | Show LLM provider status (local + cloud) |
| `/add_provider` | Wizard to dynamically add a new LLM provider |
| `/plugins` | List loaded plugins (shows slash commands + injected tools) |
| `/plugins reload` | Hot-reload plugins from disk without restarting |
| `/agents` | List all registered agent types |
| `/agents register <name> <desc>` | Register a new agent type inline |
| `/doctor` | System health check (LLM, RAG, plugins, memory) |
| `/config` | Show current configuration and file path |
| `/config <key> <value>` | Change a setting (saved immediately) |
| `/save` | Save conversation |
| `/load` | Load last saved conversation |
| `/export [file.md]` | Export conversation to Markdown |
| `/stats` | Show session statistics and token usage |
| `/history` | Show last 5 user messages |
| `/clear` | Clear conversation and reset permissions |
| `/exit` | Quit (auto-saves session) |

---

## Concepts

### Agent (`/agent`)

Autonomous mode. Chronos enters a **ReAct loop** (Reason → Act → Observe → Repeat) to complete complex tasks. It uses tools, checks results, and self-corrects. Max 30 steps with a safety breaker.

```
chronos > /agent Find all Python files with TODO comments and create a summary
```

### Tools (`/tools`)

Built-in capabilities the agent can call autonomously:

| Tool | Permission | What it does |
|------|-----------|--------------|
| `read_file` | auto | Read file contents |
| `write_file` | ask | Create or overwrite a file |
| `search_replace` | ask | Replace exact text in a file |
| `list_directory` | auto | List files in a directory |
| `glob_search` | auto | Find files by pattern (e.g. `**/*.py`) |
| `grep` | auto | Search for text patterns across files |
| `move_file` | ask | Move or rename a file |
| `execute_command` | ask | Run a shell command |
| `delegate_subtask` | ask | Spawn a specialised child agent |
| `ask_user` | auto | Ask you a clarifying question before taking an action |
| `fetch_webpage` | auto | Fetch and read content from URLs |
| `run_python` | ask | Execute Python in a persistent, isolated background REPL |
| `store_memory` / `search_memory` | auto | Manage persistent facts across sessions via Vector DB |

**Tool permission levels:**
- `y` — allow this one invocation
- `ya` — allow all for this session
- `yw` — trust this workspace permanently (saved to disk)

> In Web UI mode, these appear as interactive browser modals.

### Index & Knowledge (`/index`, `/knowledge`)

Index a project into ChromaDB. Chronos chunks files, generates embeddings, and stores them locally. Ask semantic questions about your code without sending anything to the cloud.

```
chronos > /index . --include *.py
chronos > /knowledge how does the config system work
```

### Memory (`/memory`)

Persistent facts that survive across sessions. Teach Chronos your preferences, project conventions, or important context.

```
chronos > /memory add My preferred language is Python with type hints
chronos > /memory add The project uses FastAPI for the backend
```

Stored at `~/.chatty-chronos/memory.json`.

### Spec (`/spec`)

AI-powered spec-driven development. Generates structured documents from a feature description:
- `requirements.md` — user stories, acceptance criteria
- `design.md` — architecture, components, API design
- `tasks.md` — implementation checklist

```
chronos > /spec Add user authentication with JWT
```

Creates `specs/add-user-authentication-with-jwt/` with all three files.

---

## Plugin System

Plugins are `.py` files dropped into `~/.chatty-chronos/plugins/`. They are **auto-loaded on startup** and can be hot-reloaded with `/plugins reload`.

A plugin can do **two things**:
1. Register **slash commands** (e.g. `/git-status`)
2. Inject **new tools** directly into the ReAct agent — no code changes required

### Command-only plugin (minimal)

```python
# ~/.chatty-chronos/plugins/hello.py
from plugins.base import Plugin

class HelloPlugin(Plugin):
    name = "hello"
    description = "A greeting plugin"
    commands = {"/hello": "Say hello to someone"}

    def handle_command(self, command, arg):
        if command == "/hello":
            return f"Hello, {arg or 'world'}!"
```

### Plugin that injects a tool into the agent

```python
# ~/.chatty-chronos/plugins/git_plugin.py
from plugins.base import Plugin
from tools.base import Tool
import subprocess

class GitStatusTool(Tool):
    def __init__(self):
        super().__init__(
            name="git_status",
            description="Return the current git status of a repository directory.",
            parameters={
                "path": {"type": "string", "description": "Repo directory", "required": False}
            },
            requires_permission=False,
        )
    def execute(self, path=".", **kwargs):
        result = subprocess.run(["git", "status", "--short"], cwd=path,
                                capture_output=True, text=True, timeout=10)
        return result.stdout or "(working tree clean)"

class GitPlugin(Plugin):
    name        = "git"
    description = "Git integration: commands + agent tools"
    version     = "1.0.0"
    commands    = {"/git-status": "Show git status"}
    tools       = [GitStatusTool()]        # ← injected into the agent automatically

    def handle_command(self, command, arg):
        if command == "/git-status":
            return GitStatusTool().execute(path=arg or ".")
```

Once loaded, the agent can call `git_status` autonomously when you ask it about git state — just like any built-in tool.

---

## Agent Registry

Chronos ships with a registry of **named, specialised agent types** that can be instantiated via `delegate_subtask`. Each type has its own system prompt and a whitelist of tools it is allowed to use.

### Built-in agent types

| Agent Type | Tools Allowed | Purpose |
|---|---|---|
| `file_analyst` | read_file, list_directory, glob_search, grep | Read-only codebase analysis and summarisation |
| `shell_runner` | execute_command, read_file, write_file | DevOps automation, command execution |
| `writer` | read_file, write_file, search_replace | File generation and editing |
| `researcher` | read_file, list_directory, glob_search, grep | Knowledge gathering without modification |

### Using specialised agents

**From the CLI:**
```
chronos > /agents                              # list all registered types
chronos > /agent Analyse src/ for dead code    # the LLM may pick file_analyst automatically
```

**The LLM decides** which agent type to use when delegating a subtask:
```
delegate_subtask(task="Review all Python files for security issues", agent_type="file_analyst")
delegate_subtask(task="Run the test suite and collect results",      agent_type="shell_runner")
```

### Registering a custom agent type

**From the CLI:**
```
chronos > /agents register security_auditor "Audits code for security vulnerabilities"
```

**From Python (e.g. inside a plugin):**
```python
from core.agent_registry import register_agent, AgentSpec

register_agent(AgentSpec(
    name           = "security_auditor",
    description    = "Audits code for security vulnerabilities",
    system_prompt  = (
        "You are a senior security engineer. Find vulnerabilities, "
        "injection points, and insecure patterns. Never modify files."
    ),
    tool_names     = ["read_file", "glob_search", "grep"],
    max_iterations = 25,
))
```

---

## Configuration

### Config file (`~/.chatty-chronos/config.json`)

```json
{
  "provider": "ollama",
  "model": "llama3.1:latest",
  "ollama_host": "http://localhost:11434",
  "llamacpp_host": "http://localhost:8080",
  "streaming": true,
  "max_context_messages": 20
}
```

Use `/config` inside Chronos to view/edit, or edit the file directly.

### Using a custom llama.cpp server

```bash
# Start your custom build
llama.exe --server --host 127.0.0.1 --port 8069 --model "path\to\model.gguf" --n-gpu-layers 99
```

```
chronos > /config provider llamacpp
chronos > /config llamacpp_host http://localhost:8069
chronos > /config model local
```

### Adding cloud LLM providers

Create `.env` in the project root:
```bash
GROQ_API_KEY=gsk_your_key_here          # https://console.groq.com/keys
GEMINI_API_KEY=your_key_here            # https://aistudio.google.com/apikey
NVIDIA_API_KEY=your_key_here            # https://build.nvidia.com/
MISTRAL_API_KEY=your_key_here           # https://console.mistral.ai/api-keys
OPENROUTER_API_KEY=sk-or-your_key_here  # https://openrouter.ai/keys
```

Verify with `/providers`. Keys are hot-reloaded — no restart needed.

**Add any OpenAI-compatible provider** (`~/.chatty-chronos/providers.json`):
```json
{
    "name": "together",
    "type": "openai_compatible",
    "base_url": "https://api.together.xyz/v1",
    "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "env_key": "TOGETHER_API_KEY"
}
```

---

## Data Locations

| Path | Contents |
|------|----------|
| `~/.chatty-chronos/config.json` | Settings (model, host, provider) |
| `~/.chatty-chronos/providers.json` | LLM provider list |
| `~/.chatty-chronos/memory.json` | Persistent memory (taught facts) |
| `~/.chatty-chronos/session.json` | Last saved conversation |
| `~/.chatty-chronos/vectordb/` | ChromaDB embeddings (RAG index) |
| `~/.chatty-chronos/plugins/` | Drop-in plugin `.py` files |
| `~/.chatty-chronos/prompt_history.txt` | Input history (arrow keys) |
| `~/.chatty-chronos/trusted_workspaces` | Permanently trusted directories |
| `~/.chatty-chronos/.env` | Global API keys (optional) |

---

## Architecture

```
Chatty-Chronos-v1/
├── main.py                  # REPL entry point + CLI command router
├── deploy.py                # Cross-platform installer
├── uninstall.py             # Uninstaller
├── pyproject.toml           # Package configuration
├── STEERING.md              # Project conventions for self-development
├── Start_Chronos.bat        # Model selection starter (Windows)
│
├── core/                    # Agent core
│   ├── agent.py             # ReActAgent — Thought → Tool → Observe loop
│   ├── agent_registry.py    # ★ Named specialised agent types + build_agent()
│   ├── config.py            # Persistent JSON config (~/.chatty-chronos/)
│   ├── permissions.py       # 3-tier trust system + web modal event loop
│   ├── memory.py            # ★ Cross-session persistent vector memory via ChromaDB
│   ├── context.py           # LLM-driven context compaction
│   ├── delegator.py         # Sub-agent spawning with agent_type routing
│   ├── team.py              # ★ Multi-Agent Swarm Orchestration logic
│   ├── mcp_client.py        # ★ Model Context Protocol (MCP) Manager
│   ├── repl_daemon.py       # ★ Secure, sandboxed background Python daemon
│   └── logger.py            # Rotating file logger
│
├── llm/                     # LLM backends
│   ├── ollama_provider.py   # Chat + tool calls via Ollama
│   ├── llamacpp_provider.py # Chat + tool calls via llama-server
│   ├── openai_provider.py   # Universal OpenAI-compatible client
│   ├── fallback.py          # Auto-fallback across providers
│   └── server_manager.py    # Auto-launch/stop llama-server.exe
│
├── tools/                   # Agent tools
│   ├── base.py              # Tool dataclass + Ollama schema converter
│   ├── registry.py          # ★ Dynamic registry (built-ins + plugin tools)
│   ├── filesystem.py        # ReadFile, WriteFile, Grep, Glob, Move...
│   ├── shell.py             # ExecuteCommand
│   ├── human.py             # ★ AskUser tool
│   ├── web.py               # ★ FetchWebpage tool
│   ├── python_repl.py       # ★ Stateful Python execution
│   ├── memory_tools.py      # ★ StoreMemory, SearchMemory
│   ├── mcp_tool.py          # ★ MCP tool wrapper
│   └── agent_delegator.py   # ★ DelegateSubtask with agent_type support
│
├── plugins/                 # Plugin system
│   ├── base.py              # ★ Plugin base class (tools field + get_tools())
│   └── loader.py            # Auto-load + hot-reload from ~/.chatty-chronos/plugins/
│
├── ui/                      # Web Dashboard backend
│   └── web.py               # ThreadingHTTPServer, SSE, permission API, workspace/logs endpoints
│
├── static/                  # Web Dashboard frontend
│   └── index.html           # Glassmorphism UI (streaming, modals, explorer, log console)
│
├── rag/                     # Semantic search
│   ├── indexer.py           # Chunk + embed + store in ChromaDB
│   ├── embeddings.py        # Embedding provider abstraction
│   └── retriever.py         # Semantic query + context assembly
│
├── spec/                    # Spec-driven development
│   ├── generator.py         # AI-powered spec document generator
│   └── templates/           # Markdown templates
│
└── docs/                    # Documentation
    └── CHRONOS_KNOW_HOW.md  # Deep-dive technical reference
```

Items marked **★** are newly added or significantly extended features.

---

## 📈 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=georgevpopa/Chatty-Chronos-v1&type=Date)](https://star-history.com/#georgevpopa/Chatty-Chronos-v1&Date)

---

## License

MIT — see [LICENSE](LICENSE) for details.

> **Author:** [georgevpopa](https://github.com/georgevpopa) 🚀
> If you find this project useful, drop a ⭐!

---

<a id='2-standard-installation-guide'></a>
# 2. Standard Installation Guide

> **Target Systems**: Windows 11 (primary), Linux, macOS
> **Difficulty**: Beginner → Intermediate
> **Estimated Time**: 10–20 minutes (depending on LLM engine choice)
> **Version**: 0.1.0

---

## What You Get

Chatty Chronos v3 is a **terminal-first autonomous coding agent** — a local alternative to Claude Code or GitHub Copilot. It runs entirely on your machine (no data leaves your computer when using local LLMs) and can:

- Read, write, and search files on your computer
- Execute shell commands and Python code in a sandboxed REPL
- Maintain persistent memory across sessions
- Use RAG (Retrieval-Augmented Generation) to search your project
- Delegate tasks to specialized sub-agents
- Connect to an MCP (Model Context Protocol) server ecosystem

---

## Prerequisites

### Required

| Tool | Version | How to Check |
|------|---------|-------------|
| **Python** | 3.10+ | `python --version` |
| **Git** | Any | `git --version` |

> **Windows**: During Python installation, check **"Add Python to PATH"**.

### Choose a Local LLM Engine

You need at least one of these to run Chronos locally:

| Engine | Best For | VRAM Needed | Install |
|--------|----------|-------------|---------|
| **Ollama** | Easiest setup, auto-pulls models | 4–8 GB | [ollama.com/download](https://ollama.com/download) |
| **llama.cpp** | Maximum performance, fine control | 4–8 GB | Download from [github.com/ggml-org/llama.cpp/releases](https://github.com/ggml-org/llama.cpp/releases) |

> **Or** skip local LLMs entirely and use cloud providers (NVIDIA NIM, Groq, Gemini, etc.) — just set API keys.

---

## Step 1: Clone the Repository

```powershell
cd E:\AI_Sandbox
git clone https://github.com/georgevpopa/Chatty-Chronos-v2.git
cd Chatty-Chronos-v2
```

---

## Step 2: Install Python Dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**Or** install as a package (editable mode):

```powershell
pip install -e .
```

### What gets installed

| Package | Purpose |
|---------|---------|
| `ollama` | Python client for Ollama |
| `chromadb` | Vector database for RAG |
| `sentence-transformers` | Local embeddings for RAG |
| `rich` | Terminal UI (colors, tables, panels) |
| `prompt-toolkit` | REPL input with history |
| `pydantic` | Config validation |
| `opentelemetry` | Tracing and telemetry |
| `structlog` | Structured logging |
| `mcp` | Model Context Protocol support |
| `RestrictedPython` | Sandboxed Python REPL |
| `nest-asyncio` | Async event loop compatibility |

---

## Step 3: Configure Your LLM Provider

### Option A: Ollama (Easiest)

1. Install Ollama from [ollama.com](https://ollama.com/download)
2. Pull a model:

```powershell
ollama pull qwen3.5:9b
```

3. Verify Ollama is running:

```powershell
ollama list
```

4. Chronos auto-detects Ollama — no config changes needed. Set provider:

```powershell
# In the Chronos REPL:
/config provider ollama
/config model qwen3.5:9b
```

### Option B: llama.cpp (Best Performance)

1. Download a llama.cpp release (Vulkan build for AMD/NVIDIA):
   - [github.com/ggml-org/llama.cpp/releases](https://github.com/ggml-org/llama.cpp/releases)
   - Look for `llama-*-bin-win-vulkan-x64.zip`

2. Download a GGUF model:
   - Recommended: [Qwen2.5.1-Coder-7B-Instruct-Q4_K_M.gguf](https://huggingface.co/Qwen/Qwen2.5.1-Coder-7B-Instruct-GGUF)
   - Place it in a models directory (e.g., `E:\models\`)

3. Configure Chronos:

```powershell
# In the Chronos REPL:
/config provider llamacpp
/config local_server_model E:\models\Qwen2.5.1-Coder-7B-Instruct-Q4_K_M.gguf
/config local_server_bin E:\AI_Sandbox\llama-b9827-bin-win-vulkan-x64\llama-server.exe
/config local_server_ngl 20
/config local_server_ctx 4096
```

> **GPU Memory Tip**: For integrated GPUs (AMD Radeon 890M), set `local_server_ngl` to 20–40. Setting it to 99 will crash.

4. Chronos auto-starts llama-server when you switch to the llamacpp provider:

```powershell
/config provider llamacpp
```

### Option C: Cloud Providers (No GPU Needed)

Set your API key as an environment variable:

```powershell
# PowerShell
$env:GROQ_API_KEY = "gsk_..."
$env:GEMINI_API_KEY = "AIza..."
$env:NVIDIA_NIM_API_KEY = "nvapi-..."

# Or create a .env file in the project root:
echo GROQ_API_KEY=gsk_... >> .env
echo GEMINI_API_KEY=AIza... >> .env
```

Then configure:

```powershell
/config provider groq
/config model llama-3.3-70b-versatile
```

Available cloud providers: `nvidia`, `groq`, `gemini`, `mistral`, `openrouter`

---

## Step 4: Launch Chronos

```powershell
python main.py
```

Or if installed as a package:

```powershell
chronos
```

You should see:

```
 _____ _                             _____
/ ____| |                           / ____|
| |    | |__  _ __ ___  _ __   ___ | (___
| |    | '_ \| '__/ _ \| '_ \ / _ \ \___ \
| |____| | | | | | (_) | | | | (_) |____) |
 \_____|_| |_|_|  \___/|_| |_|\___/|_____/

   v0.1.0 | Terminal-first autonomous coding agent

  Provider:  llama.cpp
  Model:     Qwen2.5.1-Coder-7B-Instruct-Q4_K_M.gguf
  Host:      http://localhost:8080
  Status:    ● CONNECTED

  Type /help for commands | /exit to quit
```

---

## Step 5: Verify Everything Works

In the Chronos REPL, type:

```
/doctor
```

This runs a health check on:
- LLM provider connection
- Ollama/llama.cpp status
- RAG embeddings availability
- VectorDB status
- Plugins and memory

---

## Docker Installation (Alternative)

If you prefer Docker:

```powershell
docker-compose up -d
```

This starts Chronos with ChromaDB (vector DB) and Ollama (if configured).

---

## Troubleshooting

### "No llama-server binary found"

The binary path doesn't exist. Check your config:

```powershell
/config local_server_bin <correct_path_to_llama-server.exe>
```

### "Model file not found"

The GGUF model path is wrong. Check:

```powershell
/config local_server_model <correct_path_to_model.gguf>
```

### Ollama "Cannot connect"

Make sure Ollama is running:

```powershell
ollama serve
```

Then in a new terminal: `python main.py`

### ChromaDB errors ("Nothing found on disk")

Delete the vector database and it will rebuild:

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.chatty-chronos\vectordb"
```

### VRAM Allocation Error (integrated GPU)

Reduce GPU layers:

```powershell
/config local_server_ngl 20
```

### Python 3.14 warnings

Some warnings are cosmetic (SyntaxWarning for escape sequences in deploy.py). They don't affect functionality.

---

## Quick Reference

| Command | Action |
|---------|--------|
| `python main.py` | Start Chronos |
| `/help` | List all commands |
| `/model` | Show/switch LLM model |
| `/provider` | Show/switch LLM provider |
| `/doctor` | System health check |
| `/config key value` | Change a setting |
| `/exit` | Quit and save session |

---

<a id='3-docker--multi-engine-guide'></a>
# 3. Docker & Multi-Engine Guide

This guide walks you through a completely fresh installation of Chatty Chronos v3 using Docker. Since Chronos is designed to be a private, local-first agent, we will cover how to set up your local AI engines (Ollama or llama.cpp), get the necessary AI models, and finally launch Chronos securely inside a Docker container.

## 📦 Prerequisites

Ensure you have the following installed on your machine:
1. **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** (Make sure it is open and running).
2. **[Git](https://git-scm.com/downloads)** (To clone the codebase).

---

## 🚀 Step 1: Clone the Chronos Repository

Open your terminal (PowerShell, Command Prompt, or bash) and clone the pristine version of the project:

```bash
git clone https://github.com/georgevpopa/Chatty-Chronos-v2.git
cd Chatty-Chronos-v2
```

---

## 🧠 Step 2: Set Up Your Local AI Engine

Chronos acts as the "brain," but it needs an "engine" to generate text. You can choose **Ollama** (easiest) or **llama.cpp** (best for raw performance/custom models).

### Option A: Using Ollama (Easiest)
Ollama manages everything (the engine and the models) for you.

1. **Install Ollama:** Download it from [ollama.com](https://ollama.com/).
2. **Download a Model:** Open a terminal and run the following command to download a solid agentic model (e.g., Llama 3.1):
   ```bash
   ollama pull llama3.1
   ```
   *Other great models for coding include `ollama pull qwen2.5-coder`.*
3. **Verify Ollama is Running:** Ollama runs automatically in the background on port `11434`. You can verify it is active by opening your terminal and running:
   - **Windows (PowerShell):** `Invoke-RestMethod -Uri http://localhost:11434`
   - **Mac/Linux (Terminal):** `curl http://localhost:11434`
   *(It should respond with "Ollama is running").*

### Option B: Using llama.cpp (Advanced / Max Performance)
Llama.cpp allows for extreme GPU optimizations (Vulkan/CUDA).

**Note on Chronos Native vs. Docker Behavior:** 
If you run Chronos *natively* via the terminal (`python main.py`), Chronos has a built-in onboarding sequence: on its first run, it will ask you to choose between Local (Ollama/llama.cpp) or Cloud, automatically scan for your downloaded models, and start the local `.exe` server for you. On subsequent runs, it remembers your last choice (which you can easily switch using `/models`).

**However, because you are installing Chronos in a Linux Docker Container**, Chronos is isolated and cannot automatically launch Windows executable files (`.exe`). Therefore, you must start the `llama-server` externally on your host machine so the container can connect to it.

1. **Download llama.cpp:**
   - Go to the [llama.cpp Releases page on GitHub](https://github.com/ggerganov/llama.cpp/releases).
   - Download the pre-compiled binary for your system (e.g., `llama-bXXXX-bin-win-vulkan-x64.zip` for universal GPU support on Windows, or `cuda` for NVIDIA).
   - Extract the folder somewhere memorable (e.g., `C:\AI\llama.cpp\`).
2. **Download a Quantized Model (GGUF format):**
   - Go to [HuggingFace](https://huggingface.co/).
   - Search for a **GGUF** quantized model (e.g., search for "Qwen2.5-Coder-7B-Instruct GGUF" or "Llama-3.1-8B-Instruct GGUF"). Look for repositories by `bartowski` or `MaziyarPanahi`.
   - Download a **Q4_K_M** or **Q5_K_M** version. *Quantization shrinks the model size so it fits in your RAM/VRAM while retaining almost all of its intelligence.*
   - Place the `.gguf` file in a dedicated models folder (e.g., `C:\AI\Models\Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf`).
3. **Start the llama-server manually on your Host:**
   Open a terminal and run your server. For example:
   ```bash
   C:\AI\llama.cpp\llama-server.exe -m C:\AI\Models\Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf --port 8080 -ngl 99 -c 8192 --host 0.0.0.0
   ```
   *(Note: `-ngl 99` offloads all layers to your GPU, and `-c 8192` sets a nice large context window).*

   > **💡 Troubleshooting Multi-GPU OOM Errors:**
   > If your system has multiple GPUs (e.g., an Integrated AMD APU and a Discrete NVIDIA Card) and `llama-server.exe` crashes immediately with an `ErrorOutOfDeviceMemory` error, it is likely trying to split the model onto a GPU that doesn't have enough VRAM. You can force it to isolate and use only a specific GPU by appending the `--device` flag.
   > 
   > First, list your devices: `llama-server.exe --list-devices`
   > Then, force it to use the GPU with the most free memory (e.g., your APU): 
   > `... --host 0.0.0.0 --device Vulkan0`

---

## ⚙️ Step 3: Configure Chronos to Talk to Your Host Machine

Because Chronos will be running inside an isolated Docker container, it cannot use `http://localhost` to talk to Ollama or llama.cpp running on your host machine (as "localhost" inside Docker just points to the container itself). We must tell it to use `host.docker.internal`.

To keep your Native Windows settings completely separate from your Docker settings, we use a dedicated folder in the project.

1. In the `Chatty-Chronos-v2` project folder, create a new folder named `docker-config`.
2. Inside `docker-config`, create a file named `config.json` with the following content:

**Example `docker-config/config.json`:**
```json
{
  "provider": "ollama",
  "model": "llama3.1",
  
  "ollama_host": "http://host.docker.internal:11434",
  "llamacpp_host": "http://host.docker.internal:8080",
  
  "base_url": "https://integrate.api.nvidia.com/v1",
  
  "embedding_provider": "local",
  "embedding_model": "all-MiniLM-L6-v2",
  "local_server_enabled": false
}
```

> **💡 Switching Providers (Local & Cloud):**
> Notice that the `config.json` holds the connection details for **all** your engines simultaneously (`ollama_host`, `llamacpp_host`, and cloud `base_url`). 
> The `"provider": "ollama"` line simply sets the **default active engine** on startup. Once you open the Web Dashboard, you can seamlessly toggle between your Local engines (Ollama/llama.cpp) and your Cloud engines using the Settings panel!
> 
> *(Keep `embedding_provider` as `"local"` so the Docker container handles memory RAG internally without burdening your main LLM, and leave `local_server_enabled` as `false` so the container doesn't try to boot `.exe` files).*

### 🏗️ How the Architecture Works (Running Multiple Engines)
If you want to use **both** Ollama and Llama.cpp simultaneously, you are basically spinning up two separate "engines" on your host PC, and letting Chronos (the "brain" inside Docker) decide which one to talk to.

Here is how it plays out mechanically:
1. **Engine 1 (Ollama)**: Runs automatically in your system tray on Windows, passively listening on port `11434`. 
2. **Engine 2 (Llama.cpp)**: You manually run your `llama-server.exe` command in a terminal, passively listening on port `8080`.
3. **The Brain (Chronos)**: Because your `docker-config/config.json` holds the connection strings for *both* (`host.docker.internal:11434` and `host.docker.internal:8080`), Chronos has a direct bridge to both engines.

When you open the Web Dashboard, if you select **"Ollama"** in the UI, Chronos routes all your chat prompts out of the container and into your Windows port `11434`. If you select **"Llama.cpp"**, Chronos instantly pivots and routes your prompts to your Windows port `8080`. You don't need to restart Docker to switch!

---

## 🐳 Step 4: Build and Launch Chronos in Docker

With Docker Desktop running, open a terminal in your cloned `Chatty-Chronos-v2` folder and run:

```bash
docker-compose up -d --build
```

**What this does:**
- `--build` guarantees it compiles a pristine image using the `Dockerfile`.
- `-d` runs it quietly in the background.
- It will automatically launch the premium Web Dashboard interface on port `8080`.

---

## 🌐 Step 5: Access the Dashboard

Once the terminal says `chronos_app` is "Started", open your web browser and go to:

👉 **[http://localhost:8080](http://localhost:8080)**

You are now fully set up with a clean, containerized, local-first agentic environment! 

*(Note: Within the Web UI, you can easily swap between your active models and providers in the settings panel, similar to using the `/models` command in the terminal).*

---

## 🛑 Stopping Chronos
When you're done, you can gracefully shut down the container by running:
```bash
docker-compose down
```

---

<a id='4-how-to-use--commands'></a>
# 4. How to Use & Commands

> **Difficulty**: Beginner → Advanced
> **Estimated Time**: 5 minutes to get started, 30 minutes to master
> **Version**: 0.1.0

---

## Quick Start

Launch Chronos:

```powershell
cd E:\AI_Sandbox\Chatty-Chronos-v2
python main.py
```

Start chatting naturally — Chronos understands what you want and uses tools to do it:

```
❯ Read the main.py file and explain its structure
❯ Create a Python function that calculates fibonacci numbers
❯ Search for all TODO comments in the project
❯ Run the tests and fix any failures
```

---

## How Chronos Thinks (ReAct Loop)

When you give Chronos a task, it follows this cycle:

1. **Think** — Analyzes your request and plans the approach
2. **Act** — Executes a tool (reads a file, runs a command, writes code)
3. **Observe** — Checks the result
4. **Repeat** — Until the task is complete

You see this as colored output in your terminal:

```
● Agent thinking... (step 1/30)
  → Reading main.py
  → The file has 131 lines...
● Agent thinking... (step 2/30)
  → Writing fibonacci.py
  → Created fibonacci.py with 15 lines
```

---

## All Slash Commands

### Essential Commands

| Command | What It Does | Example |
|---------|-------------|---------|
| `/help` | Show all commands | `/help` |
| `/model` | Show or switch LLM model | `/model`, `/model qwen3.5:9b` |
| `/provider` | Show or switch LLM provider | `/provider ollama`, `/provider groq` |
| `/clear` | Clear conversation history | `/clear` |
| `/exit` | Save session and quit | `/exit` |

### Model Management

| Command | Description |
|---------|-------------|
| `/model` | List available models |
| `/model 3` | Switch to model #3 |
| `/model qwen` | Switch by partial name |
| `/models` | List models for current provider |
| `/providers` | Show all LLM providers and their status |

### Project Tools

| Command | Description |
|---------|-------------|
| `/index .` | Index entire project for RAG search |
| `/index src --include *.py` | Index only Python files in src/ |
| `/index_web <url>` | Index a web page or docs |
| `/knowledge <query>` | Search your indexed project |

### Agent Commands

| Command | Description |
|---------|-------------|
| `/agent <task>` | Run an autonomous ReAct agent |
| `/team <task>` | Run a 3-agent team (Planner→Writer→Reviewer) |
| `/agents` | List registered agent types |
| `/agents register <name> <desc>` | Register a custom agent |

### Memory & Sessions

| Command | Description |
|---------|-------------|
| `/memory` | Show stored memories |
| `/memory add <fact>` | Store a new memory |
| `/memory clear` | Clear all memories |
| `/memory remove <index>` | Remove a specific memory |
| `/save` | Save current session |
| `/load` | Load previous session |

### Specs & Code Generation

| Command | Description |
|---------|-------------|
| `/spec <feature>` | Generate requirements, design, and tasks |
| `/specs` | List all generated specs |

### System & Diagnostics

| Command | Description |
|---------|-------------|
| `/doctor` | Full system health check |
| `/stats` | Session statistics |
| `/logs` | View recent log files |
| `/config` | Show all settings |
| `/config <key> <value>` | Change a setting |

### Web & External

| Command | Description |
|---------|-------------|
| `/web` | Launch web dashboard (port 8443) |
| `/web 9999` | Launch on custom port |
| `/paste` | Paste text from clipboard |
| `/export` | Export chat to Markdown |
| `/export chat.md` | Export to specific file |

### Plugin System

| Command | Description |
|---------|-------------|
| `/plugins` | List loaded plugins |
| `/plugins reload` | Reload plugins from disk |

### MCP (Model Context Protocol)

| Command | Description |
|---------|-------------|
| `/mcp add <name> <cmd>` | Connect an MCP server |

---

## Practical Examples

### Example 1: Analyze Your Codebase

```
❯ /index .
  Indexed 45 files (180 chunks)

❯ /knowledge How does the authentication system work?
  (Chronos searches your indexed code and provides an answer)
```

### Example 2: Write Code Autonomously

```
❯ /agent Create a REST API endpoint that returns user profiles as JSON.
         Use FastAPI, include input validation with Pydantic, and add tests.
```

Chronos will:
1. Read your existing project structure
2. Create the API endpoint file
3. Create the Pydantic model
4. Write test files
5. Run the tests to verify

### Example 3: Team Workflow for Complex Features

```
❯ /team Implement a complete user authentication system with:
         - JWT token generation
         - Password hashing with bcrypt
         - Login/logout endpoints
         - Role-based access control
         - Database models
```

The team workflow runs 3 agents sequentially:
1. **Planner** — Creates a detailed design document
2. **Writer** — Implements the code based on the plan
3. **Reviewer** — Reviews the code and provides feedback

### Example 4: Debug a Failing Test

```
❯ The tests in test_agent.py are failing. Run them and fix the issues.
```

Chronos will:
1. Run `python -m pytest tests/test_agent.py`
2. Read the failure output
3. Identify the root cause
4. Edit the source code
5. Re-run tests to confirm the fix

### Example 5: Refactor Across Files

```
❯ Refactor all the database connection code into a shared module.
   Currently each file creates its own connection — centralize it.
```

### Example 6: Git Operations

Chronos can also handle git operations:

```
❯ Commit all changes with a descriptive message
❯ Create a new branch called feature/auth
❯ What's the git diff since the last commit?
```

---

## Web Dashboard

Launch the web UI:

```
❯ /web
```

Opens at `http://localhost:8443` with a glassmorphism dashboard featuring:

- **Chat Interface** — Send messages and see real-time responses
- **System Status** — Provider, model, connection status
- **Tool Monitor** — See which tools the agent is using
- **File Browser** — Navigate your project files
- **Git Status** — View and commit changes
- **MCP Server Manager** — Connect/disconnect MCP servers
- **Memory View** — Browse stored memories
- **Session Manager** — Switch between sessions

---

## Configuration

### Config File Location

```
~/.chatty-chronos/config.json
```

### Key Settings

```json
{
  "provider": "llamacpp",
  "model": "Qwen2.5.1-Coder-7B-Instruct-Q4_K_M.gguf",
  "local_server_model": "E:\\models\\Qwen2.5.1-Coder-7B-Instruct-Q4_K_M.gguf",
  "local_server_ngl": 20,
  "local_server_ctx": 4096,
  "enable_reflection": true,
  "compaction_enabled": true,
  "ollama_host": "http://localhost:11434",
  "llamacpp_host": "http://localhost:8080"
}
```

### Change Settings at Runtime

```
/config provider ollama
/config model qwen3.5:9b
/config enable_reflection false
/config local_server_ngl 30
```

---

## Custom Agents

Register your own specialized agents:

```
/agents register security_auditor Analyzes code for security vulnerabilities and OWASP top 10 issues
```

Or create an agent file in `~/.chatty-chronos/agents/`:

```python
from core.agent_registry import register_agent, AgentSpec

register_agent(AgentSpec(
    name="test_writer",
    description="Writes comprehensive pytest test suites",
    system_prompt="You are a test specialist. Write pytest tests...",
    tool_names=["read_file", "write_file", "list_directory"],
    max_iterations=15,
))
```

---

## Plugin System

### Creating a Plugin

1. Create a file in `~/.chatty-chronos/plugins/`:

```python
# ~/.chatty-chronos/plugins/my_plugin.py
from plugins.base import Plugin

class MyPlugin(Plugin):
    name = "My Plugin"
    version = "1.0.0"
    description = "Does something useful"

    def on_start(self):
        print("Plugin loaded!")

    def on_message(self, message):
        return message  # Pass through
```

2. Reload plugins:

```
/plugins reload
```

### Using MCP Servers

Connect to an MCP server for external tools:

```
/mcp add fetch npx -y @anthropic-ai/fetch-server
/mcp add github npx -y @modelcontextprotocol/server-github
```

---

## Safety & Permissions

Chronos has a 3-tier permission system:

| Permission | Meaning | How to Set |
|-----------|---------|------------|
| `y` | Allow once | Type `y` when prompted |
| `ya` | Allow for this session | Type `ya` |
| `yw` | Allow permanently (workspace) | Type `yw` |

Some tools require permission (file writes, shell commands). Others are auto-allowed (file reads, directory listings).

In Web UI mode, permission prompts appear as interactive cards in the dashboard.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+C` | Interrupt current operation (type `/exit` to quit) |
| `Enter` | Send message |
| `↑` / `↓` | Browse command history |
| `Tab` | Auto-complete commands |

---

## Tips & Best Practices

1. **Start with `/index .`** — Index your project first so Chronos can search your codebase
2. **Use `/agent` for focused tasks** — Single-file changes, specific fixes, code review
3. **Use `/team` for complex features** — Multi-file implementations, full features
4. **Use `/memory add` to persist knowledge** — "Project uses pytest, not unittest"
5. **Use `/config enable_reflection false`** if you want faster responses without the reviewer step
6. **Check `/doctor` periodically** — Especially after switching providers or models
7. **Use `/export` to save important conversations** — Exports as clean Markdown
8. **The web dashboard** (`/web`) is great for monitoring agent activity visually

---

## Architecture Overview

```
main.py (entry point)
  ├── cli/commands.py      ← All REPL slash commands
  ├── core/
  │   ├── agent.py         ← ReAct agent loop
  │   ├── chat.py          ← Message handling + tool dispatch
  │   ├── session.py       ← Session persistence
  │   ├── memory.py        ← Long-term memory (ChromaDB)
  │   ├── permissions.py   ← 3-tier permission system
  │   └── state.py         ← Global state
  ├── llm/
  │   ├── ollama_provider  ← Ollama integration
  │   ├── llamacpp_provider ← llama.cpp integration
  │   ├── openai_provider  ← OpenAI-compatible APIs
  │   ├── fallback.py      ← Auto-fallback between providers
  │   ├── rate_limit.py    ← Rate-limit rotation
  │   └── server_manager.py ← llama-server lifecycle
  ├── tools/
  │   ├── filesystem.py    ← Read/write/search files
  │   ├── shell.py         ← Execute shell commands
  │   ├── python_repl.py   ← Sandboxed Python execution
  │   ├── web.py           ← Web scraping
  │   └── registry.py      ← Tool registration
  ├── rag/
  │   ├── indexer.py       ← Project indexing
  │   ├── retriever.py     ← Semantic search
  │   └── embeddings.py    ← Vector embeddings
  ├── plugins/
  │   ├── base.py          ← Plugin base class
  │   └── loader.py        ← Plugin discovery/loading
  ├── ui/
  │   └── web.py           ← Web dashboard server
  └── spec/
      └── generator.py     ← Spec/docs generation
```

---

## Getting Help

- **In Chronos**: Type `/help` for all commands
- **Health check**: Type `/doctor` to diagnose issues
- **Logs**: Type `/logs` to view recent activity
- **GitHub**: [github.com/georgevpopa/Chatty-Chronos-v2](https://github.com/georgevpopa/Chatty-Chronos-v2)

---

<a id='5-project-architecture--guidelines'></a>
# 5. Project Architecture & Guidelines

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

---

<a id='6-future-roadmap'></a>
# 6. Future Roadmap

Următoarele funcționalități vor transforma Chronos dintr-un simplu agent CLI într-o platformă vizuală și arhitecturală de top:

| Prioritate | Direcție | Funcționalitate & Implementare |
| :--- | :--- | :--- |
| **P1** | **Architecture** | **Streaming de Tool Execution:** Trecerea de la procesare "blocantă" (unde așteptăm 30 de pași) la **Server-Sent Events (SSE)** sau WebSockets în `ui/web.py`. Utilizatorul va vedea în timp real (litera cu literă) ce gândește agentul, ce tool apelează și cum arată output-ul parțial. |
| **P2** | **UX** | **Inline Diff View:** Când agentul vrea să modifice un cod, înainte să facă `write_file`, se trimite un semnal de "Approval" către dashboard. UI-ul va randa un block *side-by-side* roșu/verde (tip GitHub) ca utilizatorul să vadă exact ce linii se șterg/adaugă. |
| **P3** | **Memory** | **Hierarchical Memory:** Integrarea *ChromaDB* (deja adăugat în docker-compose). Sesiunea curentă rămâne în contextul imediat, dar rezumatele task-urilor trecute sunt vectorizate. Când agentul primește un task nou, caută similarități în ChromaDB ("am mai rezolvat asta luna trecută?"). |
| **P4** | **AI Quality** | **Self-Reflection Loop:** Un "Reviewer Agent" separat. Când agentul principal zice "Task completed", reviewer-ul citește task-ul inițial, rezultatul final, inspectează fișierele și dă un scor. Dacă e sub 8/10, întoarce agentul la muncă cu un set clar de critici. |
| **P5** | **MCP** | **MCP Registry UI:** Interfață vizuală în dashboard (un fel de App Store) unde aplicația citește toate uneltele `mcp_tool` disponibile pe sistem și permite activarea/dezactivarea lor cu un singur click. |

---
*Acest document va fi folosit ca referință pentru următoarele noastre acțiuni.*

---

