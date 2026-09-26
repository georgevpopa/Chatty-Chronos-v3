# Chatty Chronos v3: The Ultimate Know-How Guide

Welcome to **Chatty Chronos v3**! This guide is written by AI experts for both technical and non-technical users. By the end of this document, you will understand exactly what Chronos is, how to set it up, how to interact with it, and how to extend its capabilities.

---

## 1. What is Chatty Chronos?

**Chatty Chronos** is a "terminal-first autonomous coding agent." Think of it as a smart developer assistant that lives inside your command line (terminal), similar to tools like *Claude Code* or *Amazon Q Developer (Kiro CLI)*.

### How is it different from ChatGPT or Gemini Web Interface?
Unlike standard web chat boxes that can only chat with you, Chronos has **"arms and legs"** (called **Tools**). When you ask Chronos to do a task, it doesn't just explain how to do it; it can:
* 📂 **Read and write files** on your computer.
* 🔍 **Search through entire directories** using glob and search patterns.
* 💻 **Execute commands** in your terminal.
* 🧠 **Remember facts** across different sessions.
* 🤖 **Delegate work** to smaller, independent AI child agents.

Chronos operates in a **ReAct (Reasoning + Action) Loop**:
1. **Think**: Analyze your task and formulate a plan.
2. **Act**: Execute a tool (e.g., write code to a file).
3. **Observe**: Read the tool's output and verify correctness.
4. **Repeat**: Continue until the task is complete.

---

## 2. Installation Step-by-Step

Chronos runs on **Windows, macOS, and Linux**. Follow these simple steps to get it running.

### 📋 Prerequisites (What you need installed first)
1. **Python (version 3.10 or higher)**: The programming language Chronos is built with.
   * *How to get it:* Download and install from [python.org](https://www.python.org/downloads/). During installation on Windows, **make sure to check the box that says "Add Python to PATH"**.
2. **Git**: A tool used to clone the project code.
   * *How to get it:* Download and install from [git-scm.com](https://git-scm.com/).

---

### 🚀 OS-Specific Step-by-Step Setup

Follow the specific commands for your Operating System to set up base prerequisites (Python, Git, curl) and deploy Chatty Chronos:

#### **🪟 On Windows:**
1. Download **Python 3.10+** from [python.org](https://www.python.org/downloads/) (ensure **"Add Python to PATH"** is checked during setup).
2. Download and install **Git** from [git-scm.com](https://git-scm.com/).
3. Open Command Prompt or PowerShell and run:
   ```powershell
   # Clone the repository
   git clone https://github.com/georgevpopa/Chatty-Chronos-v1.git
   cd Chatty-Chronos-v1

   # Run the deployment helper
   python deploy.py
   ```

#### **🍏 On macOS (using Homebrew):**
1. Open Terminal. If you don't have Homebrew, install it first from [brew.sh](https://brew.sh).
2. Install Python and Git:
   ```bash
   brew install python git
   ```
3. Clone and deploy Chatty Chronos:
   ```bash
   git clone https://github.com/georgevpopa/Chatty-Chronos-v1.git
   cd Chatty-Chronos-v1
   python3 deploy.py
   ```

#### **🐧 On Linux (Debian / Ubuntu / Mint):**
1. Install base dependencies:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv git curl
   ```
2. Clone and deploy Chatty Chronos:
   ```bash
   git clone https://github.com/georgevpopa/Chatty-Chronos-v1.git
   cd Chatty-Chronos-v1
   python3 deploy.py
   ```

#### **🐧 On Linux (Fedora / RHEL / CentOS):**
1. Install base dependencies:
   ```bash
   sudo dnf install -y python3 git curl
   ```
2. Clone and deploy Chatty Chronos:
   ```bash
   git clone https://github.com/georgevpopa/Chatty-Chronos-v1.git
   cd Chatty-Chronos-v1
   python3 deploy.py
   ```

#### **🐧 On Linux (Arch / Manjaro):**
1. Install base dependencies:
   ```bash
   sudo pacman -Sy python git curl --noconfirm
   ```
2. Clone and deploy Chatty Chronos:
   ```bash
   git clone https://github.com/georgevpopa/Chatty-Chronos-v1.git
   cd Chatty-Chronos-v1
   python3 deploy.py
   ```

*What the installer does:* It creates a virtual environment, installs all required python dependencies, sets up local databases, asks you for host configurations, and compiles a quick-start runner script (`start.bat` on Windows or `start.sh` on Unix).

---

### 🧠 Setting Up Your AI Brain (llama.cpp vs. Ollama vs. Cloud)

Chronos is highly flexible and can run GGUF models directly via llama.cpp or connect to Ollama and cloud APIs:

#### **Option A: llama.cpp / llama-server (Recommended for AMD & NVIDIA GPUs - Free & Offline)**
If you have a dedicated or integrated graphics card (like the Radeon 890M) and want maximum speed via GPU hardware acceleration (Vulkan/ROCm/HIP):
1. Download a pre-compiled `llama-server` binary for your OS (e.g. Vulkan or ROCm version) from [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases).
2. Download a GGUF model (such as `Qwen_Qwen3.5-9B-Q4_K_M.gguf`) and save it locally in your sandbox folder.
3. On Windows, double-click `Start_Chronos.bat`. It will prompt you to select the GGUF file and automatically launch the local GPU-accelerated server on port `8069`.

#### **Option B: Ollama (Alternative local server - Free & Offline)**
1. Download and install [Ollama](https://ollama.com/).
2. Keep Ollama running in the background.
3. Open a terminal and download your models:
   ```bash
   ollama pull llama3.1
   ollama pull nomic-embed-text    # Required for project indexing/RAG
   ```

#### **Option B: Local & Private (Using llama.cpp - Advanced)**
* If you have a dedicated graphics card (like the integrated Radeon 890M) and want maximum speed via GPU acceleration:
* Put your `.gguf` model files in your sandbox folder.
* Launch Chronos using `Start_Chronos.bat` and select the model from the interactive local menu. It will configure and start `llama-server.exe` automatically.

#### **Option C: Cloud Power (Gemini, Groq, Nvidia NIM - Faster & Smarter)**
1. Start Chronos:
   ```bash
   python main.py
   ```
2. Type `/add_provider` in the console.
3. Follow the wizard to input your API Key (e.g. Gemini key or Nvidia NIM key).
4. Run `/config provider nvidia` or `/config provider gemini` to activate it.

---

## 3. What Can You Do with Chronos?

Once you start Chronos by running `python main.py` or launching `Start_Chronos.bat`, you will see a command prompt: `chronos >`. Here are the core things you can do:

### 💬 Chat and Coding
You can talk to it like a normal chatbot, but you can also ask it to do real work.
* *Example:* `chronos > write a python script that downloads images from a URL`
* *What happens:* Chronos will write the script, verify it, and save it directly to your folder.

### ⚡ System Commands (Slash Commands)
Type these commands starting with a `/` to perform special operations:

| Command | Purpose | Example |
| :--- | :--- | :--- |
| `/help` | Shows all available commands | `/help` |
| `/tools` | Lists the actions the agent can perform | `/tools` |
| `/model` | Switches or checks the active AI model | `/model llama3.1` |
| `/providers` | Shows status of all active AI servers | `/providers` |
| `/config` | View or edit config parameters | `/config compaction_enabled false` |
| `/index` | Reads and indexes your current folder for code lookup | `/index .` |
| `/knowledge` | Search your indexed project files semantically | `/knowledge how does main.py start?` |
| `/memory` | Teach the agent permanent facts about your preferences | `/memory add I prefer Python over JS` |
| `/spec` | Creates design/requirements files for a new feature | `/spec Create user login page` |
| `/agent` | Enters fully autonomous mode to solve a complex task | `/agent Find all TODOs and write them to todo.md` |
| `/web` | Launches the interactive web dashboard on localhost | `/web` |
| `/doctor` | Checks if Ollama, database, and connections are healthy | `/doctor` |
| `/exit` | Saves your chat session and quits safely | `/exit` |

---

### 🌐 Interactive Web UI Dashboard

If you prefer a visual interface over the terminal command prompt, Chronos includes a stunning web-based dashboard featuring:
* **Modern Glassmorphism Theme Selector:** Persistent theme selection supporting 7 vibrant cyber-dark and light variations.
* **Real-time SSE Token Streaming:** Generates text dynamically character-by-character as it comes from the LLM, rather than waiting for complete generation.
* **Interactive ReAct Step Logs:** Visual logs and collapsible summaries that display tool execution arguments and console observations in real-time as the agent progresses.
* **Multi-Session Sidebar:** Save, reload, clear, and delete past conversations on the fly. Conversations are saved individually as JSON files in the `~/.chatty-chronos/sessions/` directory.
* **Hardware iGPU & Process Monitor:** Visual telemetry displaying system memory usage (crucial for AMD APU shared memory allocation) and the specific VRAM footprint of the background `llama-server.exe` process.
* **Runtime Config Modifiers:** Interactive selectors to swap models, change providers, toggle automatic tool approvals, and clear history.

#### **How to Start the Web UI:**
* **Method 1 (Dynamic CLI Switch):** While in a terminal session, type:
  ```text
  chronos > /web
  ```
* **Method 2 (Direct Command Line):** Start Chronos directly in web-only mode:
  ```bash
  python main.py --web
  ```
* **Method 3 (Custom Port):** Specify a custom port if port `8000` is occupied:
  ```bash
  python main.py --web --port=8080
  ```

Once launched, the dashboard will open automatically in your default browser at `http://localhost:8000`.

---

## 4. How to Create Sub-Agents

A **Sub-Agent** is a child agent spawned by the main Chronos agent to work on a task in isolation. 

### How delegation works in Chronos:
Inside the core engine, the agent is equipped with a tool called `delegate_subtask`. When you give Chronos a large task, the model writes a prompt and calls this tool to spawn a separate child instance. 

To create sub-agents, **you do not need to write code!** You simply command the agent.

### How to trigger a Sub-Agent:
Simply ask the main agent to delegate or run subtasks.
* **Example Task**: 
  `chronos > /agent Refactor the whole folder. Delegate the search of python files to a sub-agent, and let another sub-agent review the logs.`
* **Under the Hood**:
  1. The main agent decides to invoke the `delegate_subtask` tool.
  2. A new child `ReActAgent` is initialized.
  3. The child agent runs, performs the tasks, returns the result to the parent, and shuts down.

### Specialised Agent Types (Agent Registry)
Instead of just generic sub-agents, Chronos features an **Agent Registry** containing specialised agent profiles. Each profile has a focused system prompt and a specific whitelist of tools.
* **`file_analyst`**: Read-only codebase analysis (can only read files, list dirs, grep, glob).
* **`shell_runner`**: DevOps and execution (can run shell commands).
* **`writer`**: Code generation and editing (can read, write, and search-replace).
* **`researcher`**: Knowledge gathering.

When you ask the main agent to delegate, it will intelligently pick the right `agent_type`. You can view all registered agent types by typing:
```text
chronos > /agents
```
You can also register custom agent types inline using `/agents register <name> <description>`.

---

## 5. How to Create Plugins

Plugins are Python scripts that allow you to expand Chronos by adding custom commands or hooks without modifying the main codebase.

### Where do Plugins live?
Chronos looks for plugins in your home folder at:
* **Windows**: `C:\Users\<YourUsername>\.chatty-chronos\plugins\`
* **macOS/Linux**: `/Users/<YourUsername>/.chatty-chronos/plugins/`

---

### Step-by-Step: Creating Your First Plugin

Let's create a plugin called `weather_plugin.py` that adds a `/weather` command.

1. Navigate to your `~/.chatty-chronos/plugins/` directory.
2. Create a file named `weather_plugin.py`.
3. Paste the following Python code:

```python
from plugins.base import Plugin
from rich.console import Console

console = Console()

class WeatherPlugin(Plugin):
    name = "WeatherPlugin"
    description = "Adds a simple slash command to check the weather status."
    
    # Register the custom slash commands provided by this plugin
    commands = {
        "/weather": "Check the weather for a city"
    }

    def handle_command(self, command: str, arg: str):
        if command == "/weather":
            city = arg.strip() if arg else "Bucharest"
            console.print(f"\n[bold blue]☁ Checking weather for {city}...[/bold blue]")
            console.print(f"  Status: [green]Sunny & Warm (26°C)[/green]\n")
            return "Weather displayed."
```

4. Launch or return to your Chronos console.
5. Reload the plugins by typing:
   ```text
   chronos > /plugins reload
   ```
6. Test your new command:
   ```text
   chronos > /weather Tokyo
   ```

### Advanced: Injecting Agent Tools
Plugins aren't just for slash commands! A plugin can also inject entirely new **Tools** into the autonomous ReAct Agent. 

To do this, create a class that inherits from `Tool` (from `tools.base`) and add it to the plugin's `tools` list:
```python
from plugins.base import Plugin
from tools.base import Tool
import subprocess

class GitStatusTool(Tool):
    def __init__(self):
        super().__init__(
            name="git_status",
            description="Returns the current git status.",
            parameters={},
            requires_permission=False
        )
    def execute(self, **kwargs):
        return subprocess.check_output(["git", "status", "--short"]).decode()

class GitPlugin(Plugin):
    name = "git"
    description = "Exposes git status to the ReAct agent"
    tools = [GitStatusTool()]  # The agent can now use git_status autonomously!
```
Type `/plugins` to see all loaded plugins along with the tools they inject.

---

## 💡 Summary: What Can You Achieve with Chatty Chronos?

With Chatty Chronos v3, you have a software assistant that sits in your workspace:
- **Build new features**: Generate planning documents using `/spec` and have the agent write the code using `/agent`.
- **Learn codebases**: Use `/index` on any open-source code folder, and then ask questions using `/knowledge` to understand how the project works without reading thousands of lines manually.
- **Automate boring tasks**: Rename files, clean up directories, run search-and-replace refactoring on code, or write test files automatically.
- **Custom Fit**: Teach the agent your coding style using `/memory`, and add custom commands using **Plugins**.

---

## 6. A 5-Minute Hands-On Tutorial (Quick Start)

To get comfortable with Chronos, try running this simple sequence of tasks:

1. **Launch Chronos**:
   * Double-click `Start_Chronos.bat` (on Windows) or run `python main.py` in your terminal.
2. **Teach it your name**:
   ```text
   chronos > /memory add My developer name is George
   ```
3. **Index your project**:
   * Tell Chronos to scan the directory you are in:
   ```text
   chronos > /index .
   ```
4. **Ask a question about the code**:
   ```text
   chronos > /knowledge how does config.json work?
   ```
5. **Run your first autonomous agent task**:
   * Let's ask it to create a hello world file and run it:
   ```text
   chronos > /agent Create a file named hello.py that prints "Hello from Chronos!", run it, and tell me if it works.
   ```
   * *Watch the screen*: You will see the agent "think," ask you for permission to write the file, write it, ask you for permission to execute it, run it, and summarize the result!
6. **Exit the session**:
   ```text
   chronos > /exit
   ```

---

## 7. Best Practices for Prompting Chronos

To get the best results out of the autonomous `/agent` mode, keep these expert tips in mind:

* **Be Specific**: Instead of saying *"fix the code,"* say *"Read llamacpp_provider.py, find why it returns a 400 Bad Request on empty assistant messages, and edit the file to fix it."*
* **Provide Context**: If your code requires special environment settings, mention them (e.g., *"Make sure to run the script with python3"*).
* **Ask for Verification**: Always ask the agent to verify its work (e.g., *"After editing the file, run the tests to make sure it passes"*).
* **Break Down Huge Tasks**: If you want to build a complete web app, don't ask for it in one prompt. Use `/spec` to generate the plan first, then ask Chronos to build it component by component.

---

## 8. Safety & Permissions (The Trust Model)

Because Chronos can run commands and edit files, it includes a **3-tier safety lock** to protect your computer. 

When Chronos wants to do something potentially dangerous (like writing to a file or running a shell command), it will ask you:
```text
  [?] Grant permission for write_file(path='E:\AI_Sandbox\hello.py')? (y/n/a/w)
```

### What do the options mean?
* **`y` (Yes)**: Allow this single action only.
* **`n` (No)**: Deny this action. The agent will try to find another way or stop.
* **`a` (Allow Session)**: Trust this action type for the entire terminal session (e.g., allow all file writes until you close the app).
* **`w` (Trust Workspace)**: Permanently trust this folder. Chronos will never ask for permission in this directory again. You can manage trusted workspaces inside the `~/.chatty-chronos/trusted_workspaces` configuration file.
* **🔧 Web UI Auto-Approval**: When running in Web UI dashboard mode, `auto_approve_tools` is enabled by default to allow smooth, non-blocking background operations. You can toggle this security lock dynamically from the dashboard panel at any time.

---

## 9. Troubleshooting & Common Issues

### ❌ Error: `Cannot connect to Ollama` / `llama.cpp disconnected`
* **What to do:** 
  1. Make sure your local server is actually running. If using Ollama, ensure the Ollama app is open in your system tray.
  2. If using `llama.cpp` (local GGUF), check the logs folder: `~/.chatty-chronos/logs/llama_server.log` to see if there is an issue loading the GGUF file.

### ❌ Error: `Client error '400 Bad Request' (context exceeded)`
* **What to do:**
  1. This happens when the conversation history or RAG context is too big for the server's memory.
  2. Run `/clear` to clear the conversation history and start fresh.
  3. Ensure your `"local_server_ctx"` is set to `16384` or higher in `/config`.

### ❌ The model is behaving weirdly or replying in the wrong language
* **What to do:**
  * Some smaller local models (e.g., under 7B parameters) can lose track of instructions. Run `/clear` to reset the agent's memory, or switch to a stronger model (such as `Qwen 3.5 9B` or a cloud model like `Gemini`) using `/config provider gemini` or the startup launcher.

