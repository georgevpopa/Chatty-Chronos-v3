# Chatty Chronos v3 — From Scratch Installation Guide (Docker & Local LLMs)

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
