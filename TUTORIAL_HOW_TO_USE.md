# Chatty Chronos v3 — How To Use

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
