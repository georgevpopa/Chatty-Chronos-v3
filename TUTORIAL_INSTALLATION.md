# Chatty Chronos v3 — Installation Guide

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
