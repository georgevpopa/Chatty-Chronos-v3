import sys
import json
import os
from pathlib import Path

from rich.markdown import Markdown
from core import state
from core.session import save_session, load_session
from core.permissions import reset_session_trust
from core.agent import ReActAgent
from llm import ollama_provider, llamacpp_provider
from llm.fallback import get_available_providers
from tools.registry import get_all_tools
from rag.indexer import index_directory, index_url
from rag.retriever import get_rag_context
from spec.generator import create_spec, list_specs
from plugins.loader import get_loaded_plugins, get_plugin_commands, reload_plugins
from llm.server_manager import stop_local_server, start_local_server
from core.agent_registry import list_agents, register_agent, AgentSpec

def handle_command(cmd):
    """Handle slash commands. Returns True if handled."""
    parts = cmd.strip().split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if command in ("/exit", "/quit"):
        save_session()
        stop_local_server()
        state.console.print("[dim]Goodbye![/dim]")
        sys.exit(0)

    elif command == "/help":
        from rich.table import Table
        table = Table(title="Chatty Chronos Commands", header_style="bold cyan", border_style="dim")
        table.add_column("Command", style="bold yellow")
        table.add_column("Description")
        
        table.add_row("/help", "Show this help menu")
        table.add_row("/model [name]", "Show or switch the active LLM model")
        table.add_row("/provider [name]", "Show or switch the active LLM provider")
        table.add_row("/models", "List available models (Ollama, llama.cpp or cloud)")
        table.add_row("/tools", "List available filesystem and execution tools")
        table.add_row("/agent <task>", "Run autonomous ReAct agent on a task")
        table.add_row("/team <task>", "Run a 3-agent autonomous team (Planner->Writer->Reviewer)")
        table.add_row("/paste [prompt]", "Incarca un text mare din clipboard (fara sa umple ecranul)")
        table.add_row("/mcp add <name> <cmd>", "Connect an MCP server (e.g. /mcp add fetch npx -y @anthropic-ai/fetch-server)")
        table.add_row("/index <path>", "Index a directory for RAG project search")
        table.add_row("/index_web <url>", "Index web page/documentation content")
        table.add_row("/knowledge <q>", "Query the semantic project index")
        table.add_row("/memory", "Show/add/clear persistent workspace memory")
        table.add_row("/spec <feature>", "Generate requirements, design, and task specs")
        table.add_row("/specs", "List all generated specs")
        table.add_row("/providers", "Show LLM API providers status")
        table.add_row("/add_provider", "Wizard to dynamically add a new LLM provider")
        table.add_row("/plugins", "List loaded plugins / reload plugins from disk")
        table.add_row("/agents", "List registered agent types / register a new one")
        table.add_row("/doctor", "Check system dependencies health")
        table.add_row("/export [file]", "Export the current chat session to Markdown")
        table.add_row("/stats", "Show token and command session stats")
        table.add_row("/clear", "Clear conversation history")
        table.add_row("/history", "Show brief history of user prompts")
        table.add_row("/config [k v]", "Show or modify settings")
        table.add_row("/save", "Save current chat session to disk")
        table.add_row("/load", "Load last saved session")
        table.add_row("/exit / /quit", "Quit session and save conversation")
        
        state.console.print(table)
        state.console.print()

    elif cmd.startswith("/mcp add "):
        parts = cmd.split(" ", 3)
        if len(parts) < 4:
            state.console.print("[red]Usage: /mcp add <server_name> <command> [args...][/red]")
            return True
        
        server_name = parts[2]
        cmd_string = parts[3]
        
        import shlex
        import asyncio
        try:
            cmd_parts = shlex.split(cmd_string)
        except ValueError as e:
            state.console.print(f"[red]Error parsing command: {e}[/red]")
            return True
            
        cmd_exec = cmd_parts[0]
        args = cmd_parts[1:]
        
        state.console.print(f"[yellow]Connecting to MCP server '{server_name}'...[/yellow]")
        from core.mcp_client import get_mcp_manager
        manager = get_mcp_manager()
        
        success = asyncio.run(manager.connect(server_name, cmd_exec, args))
        if success:
            from tools.mcp_tool import MCPToolWrapper
            from tools.registry import register_tool
            tools = manager.get_server_tools(server_name)
            for t in tools:
                wrapped = MCPToolWrapper(server_name, t)
                register_tool(wrapped)
            state.console.print(f"[green]Successfully connected to '{server_name}' and registered {len(tools)} tools.[/green]")
        else:
            state.console.print(f"[red]Failed to connect to '{server_name}'.[/red]")
            
        return True

    elif command == "/paste":
        try:
            import pyperclip
            clipboard_text = pyperclip.paste()
        except Exception as e:
            state.console.print(f"  [red]Nu am putut citi clipboard-ul (eroare pyperclip): {e}[/red]")
            return True

        if not clipboard_text:
            state.console.print("  [red]Clipboard-ul este gol![/red]")
            return True

        state.console.print(f"  [green]Am citit {len(clipboard_text)} caractere din clipboard.[/green]")
        
        prompt_text = arg.strip() if arg else "Analizează acest conținut:"
        final_prompt = f"{prompt_text}\n\n```text\n{clipboard_text}\n```"
        
        from core.chat import send_message
        send_message(final_prompt)
        return True

    elif command == "/web":
        from ui.web import start_web_server
        port = 8443
        if arg.isdigit():
            port = int(arg)
        start_web_server(state.config, port)

    elif command == "/add_provider":
        state.console.print("\n[bold cyan]=== Integrare Provider Nou ===[/bold cyan]")
        
        p_name = input("  Nume provider (ex: openai, anthropic): ").strip().lower()
        if not p_name:
            state.console.print("  [red]Numele este obligatoriu. Operatiune anulata.[/red]")
            return True
            
        p_url = input("  Base URL (ex: https://api.openai.com/v1): ").strip()
        p_model = input("  Model implicit (ex: gpt-4o): ").strip()
        
        p_env = f"{p_name.upper()}_API_KEY"
        
        p_key = input(f"  API Key pentru {p_env} (lasa gol pentru a sari): ").strip()
        
        prov_file = state.config.dir / "providers.json"
        prov_data = []
        if prov_file.exists():
            with open(prov_file, "r", encoding="utf-8") as f:
                prov_data = json.load(f)
                
        for p in prov_data:
            if p.get("name") == p_name:
                state.console.print(f"  [yellow]Eroare: Providerul '{p_name}' exista deja in configuratie![/yellow]")
                return True
                
        new_provider = {
            "name": p_name,
            "type": "openai_compatible",
            "base_url": p_url,
            "model": p_model,
            "env_key": p_env
        }
        prov_data.append(new_provider)
        
        with open(prov_file, "w", encoding="utf-8") as f:
            json.dump(prov_data, f, indent=2)
            
        if p_key:
            env_file = Path.cwd() / ".env"
            with open(env_file, "a", encoding="utf-8") as f:
                f.write(f"\n{p_env}={p_key}\n")
            os.environ[p_env] = p_key
            
        state.console.print(f"  [green]Succes! Providerul {p_name} a fost integrat in ecosistem.[/green]")
        state.console.print(f"  [dim]Activeaza-l acum folosind: /config provider {p_name}[/dim]\n")

    elif command == "/model":
        provider = state.config.get("provider", "ollama")

        if provider == "llamacpp":
            # List available GGUF files
            model_path = state.config.get("local_server_model", "")
            models_dir = os.path.dirname(model_path) if model_path else ""

            if not models_dir or not os.path.isdir(models_dir):
                state.console.print(f"  [red]Models directory not found: {models_dir}[/red]")
                return True

            gguf_files = sorted([f for f in os.listdir(models_dir) if f.endswith(".gguf")])

            if not gguf_files:
                state.console.print(f"  [red]No .gguf files found in {models_dir}[/red]")
                return True

            current_model = state.config.get("model", "(not set)")

            if not arg:
                # Show list with numbers
                state.console.print(f"\n  [bold]Available models:[/bold] [dim]({models_dir})[/dim]\n")
                for i, f in enumerate(gguf_files, 1):
                    size_mb = os.path.getsize(os.path.join(models_dir, f)) // (1024 * 1024)
                    marker = " [green]← active[/green]" if f == current_model else ""
                    state.console.print(f"  [yellow]{i:>2}.[/yellow] {f} [dim]({size_mb} MB)[/dim]{marker}")
                state.console.print(f"\n  [dim]Usage: /model <number> or /model <filename>[/dim]\n")
            else:
                # Try to resolve by number or filename
                selected = None
                if arg.isdigit():
                    idx = int(arg) - 1
                    if 0 <= idx < len(gguf_files):
                        selected = gguf_files[idx]
                    else:
                        state.console.print(f"  [red]Invalid number. Choose 1-{len(gguf_files)}[/red]")
                        return True
                else:
                    # Match by filename (partial or full)
                    matches = [f for f in gguf_files if arg.lower() in f.lower()]
                    if len(matches) == 1:
                        selected = matches[0]
                    elif len(matches) > 1:
                        state.console.print(f"  [yellow]Multiple matches:[/yellow]")
                        for m in matches:
                            state.console.print(f"    • {m}")
                        state.console.print(f"\n  [dim]Be more specific or use the number.[/dim]")
                        return True
                    else:
                        state.console.print(f"  [red]No model matching '{arg}' found.[/red]")
                        return True

                if selected:
                    from llm.server_manager import restart_with_model
                    state.console.print(f"\n  [cyan]Switching to: {selected}[/cyan]")
                    success = restart_with_model(state.config, selected)
                    if success:
                        # Update system prompt
                        from core.state import _build_system_prompt
                        state.SYSTEM_PROMPT = _build_system_prompt()
                        with state.messages_lock:
                            if state.messages:
                                state.messages[0]["content"] = state.SYSTEM_PROMPT
                        state.console.print(f"  [green]✓ Model switched to: {selected}[/green]\n")
                    else:
                        state.console.print(f"  [red]Failed to start server with {selected}[/red]\n")

        elif provider == "ollama":
            if not arg:
                models = ollama_provider.list_models(state.config.get("ollama_host"))
                current_model = state.config.get("model", "(not set)")
                if models:
                    state.console.print(f"\n  [bold]Available Ollama models:[/bold]\n")
                    for m in models:
                        marker = " [green]← active[/green]" if m == current_model else ""
                        state.console.print(f"  • {m}{marker}")
                    state.console.print(f"\n  [dim]Usage: /model <name>[/dim]\n")
                else:
                    state.console.print("[red]  Cannot connect to Ollama. Is it running?[/red]")
            else:
                state.config.set("model", arg.strip())
                from core.state import _build_system_prompt
                state.SYSTEM_PROMPT = _build_system_prompt()
                with state.messages_lock:
                    if state.messages:
                        state.messages[0]["content"] = state.SYSTEM_PROMPT
                state.console.print(f"  [green]Model set to:[/green] [cyan]{arg.strip()}[/cyan]")

        else:
            # Cloud provider
            if not arg:
                current_model = state.config.get("model", "(not set)")
                state.console.print(f"  [bold]Current model:[/bold] [green]{current_model}[/green]")
                state.console.print(f"  [bold]Provider:[/bold] [cyan]{provider}[/cyan]")
            else:
                state.config.set("model", arg.strip())
                from core.state import _build_system_prompt
                state.SYSTEM_PROMPT = _build_system_prompt()
                with state.messages_lock:
                    if state.messages:
                        state.messages[0]["content"] = state.SYSTEM_PROMPT
                state.console.print(f"  [green]Model set to:[/green] [cyan]{arg.strip()}[/cyan]")

    elif command == "/provider":
        if not arg:
            current_provider = state.config.get("provider", "ollama")
            state.console.print(f"  [bold]Current provider:[/bold] [cyan]{current_provider}[/cyan]\n")
            state.console.print("  [bold green]Local (Open-Source):[/bold green]")
            state.console.print("    • ollama")
            state.console.print("    • llamacpp")
            state.console.print("\n  [bold blue]Cloud (API):[/bold blue]")
            state.console.print("    • nvidia")
            state.console.print("    • gemini")
            state.console.print("    • groq")
            state.console.print("\n  [dim]Usage: /provider <name>[/dim]")
        else:
            new_provider = arg.strip().lower()
            old_provider = state.config.get("provider", "ollama")

            state.config.set("provider", new_provider)

            # Stop llama-server if switching away from llamacpp
            if old_provider == "llamacpp" and new_provider != "llamacpp":
                stop_local_server()

            # Start llama-server if switching to llamacpp
            if new_provider == "llamacpp" and old_provider != "llamacpp":
                state.console.print("  [cyan]Starting llama.cpp server...[/cyan]")
                start_local_server(state.config)

            # Update system prompt
            from core.state import _build_system_prompt
            state.SYSTEM_PROMPT = _build_system_prompt()
            with state.messages_lock:
                if state.messages:
                    state.messages[0]["content"] = state.SYSTEM_PROMPT

            state.console.print(f"  [green]Provider set to:[/green] [cyan]{new_provider}[/cyan]")

    elif command == "/models":
        active_provider = state.config.get("provider", "ollama")

        if active_provider == "nvidia":
            from llm.fallback import list_nvidia_models
            state.console.print("[dim] Se încarcă catalogul live de endpoint-uri de la NVIDIA...[/dim]")
            models = list_nvidia_models()
            if models:
                state.console.print("\n[bold]Modele disponibile în NVIDIA Cloud (Free Endpoints):[/bold]")
                current = state.config.get("model")
                for m in sorted(models):
                    marker = " [green]← activ[/green]" if m == current else ""
                    state.console.print(f"  • {m}{marker}")
                state.console.print()
            else:
                state.console.print("[red]  Nu s-a putut descărca catalogul NVIDIA. Verifică cheia din .env sau conexiunea.[/red]")
        elif active_provider == "llamacpp":
            current = state.config.get("model")
            state.console.print(f"\n[bold]Current llama.cpp model:[/bold]")
            state.console.print(f"  • [green]{current}[/green]  ← active")
            state.console.print("\n[dim]  To change model, restart llama-server with the new GGUF file.[/dim]")
            state.console.print(f"  [dim]Then set it with:[/dim] /model <filename.gguf>")
            state.console.print()
        else:
            models = ollama_provider.list_models(state.config.get("ollama_host"))
            if models:
                state.console.print("\n[bold]Available local models (Ollama):[/bold]")
                current = state.config.get("model")
                for m in models:
                    marker = " [green]← active[/green]" if m == current else ""
                    state.console.print(f"  • {m}{marker}")
                state.console.print()
            else:
                state.console.print("[red]  Cannot connect to Ollama. Is it running?[/red]")

    elif command == "/clear":
        with state.messages_lock:
            state.messages.clear()
            from core.state import _build_system_prompt
            state.SYSTEM_PROMPT = _build_system_prompt()
            state.messages.append({"role": "system", "content": state.SYSTEM_PROMPT})
        reset_session_trust()
        state.console.print("  [dim]Conversation cleared.[/dim]")

    elif command == "/history":
        with state.messages_lock:
            user_msgs = [m for m in state.messages if m["role"] == "user"]
            previews = [m["content"][:60] + ("..." if len(m["content"]) > 60 else "") for m in user_msgs[-5:]]
        state.console.print(f"\n  [bold]{len(user_msgs)}[/bold] exchanges in current session")
        for i, preview in enumerate(previews, 1):
            state.console.print(f"  {i}. {preview}")
        state.console.print()

    elif command == "/config":
        if arg:
            parts2 = arg.split(maxsplit=1)
            if len(parts2) == 2:
                key, val = parts2
                if val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                elif val.isdigit():
                    val = int(val)
                state.config.set(key, val)
                state.console.print(f"  {key} → [cyan]{val}[/cyan]")
            else:
                val = state.config.get(parts2[0], "[not set]")
                state.console.print(f"  {parts2[0]} = [cyan]{val}[/cyan]")
        else:
            state.console.print("\n[bold]Configuration:[/bold]")
            for k, v in state.config.data.items():
                state.console.print(f"  {k}: [cyan]{v}[/cyan]")
            state.console.print()

    elif cmd.startswith("/team "):
        task = cmd[6:].strip()
        state.console.print(f"\n[bold blue]Starting Team Workflow:[/bold blue] {task}")
        from core.team import run_team_workflow
        
        from core.permissions import thread_local
        def _on_agent_switch(agent_name, agent_task):
            if hasattr(thread_local, "yield_func"):
                thread_local.yield_func({
                    "type": "agent_switch",
                    "agent": agent_name,
                    "task": agent_task
                })
                
        final_result = run_team_workflow(task, state.config, on_switch=_on_agent_switch)
        state.console.print("\n[bold green]Team Workflow Completed.[/bold green]")
        with state.messages_lock:
            state.messages.append({"role": "user", "content": f"/team {task}"})
            state.messages.append({
                "role": "assistant", 
                "content": f"**Team Output Summary:**\n\n**Final Result:**\n{final_result}"
            })

    elif command == "/index":
        if not arg:
            state.console.print("  [yellow]Usage: /index <path> [--include pattern][/yellow]")
            state.console.print("  [dim]Example: /index . --include *.py[/dim]")
        else:
            parts2 = arg.split("--include")
            path = parts2[0].strip()
            include = parts2[1].strip() if len(parts2) > 1 else None
            with state.console.status(f"[bold cyan]Indexing directory {path}...[/bold cyan]"):
                n_files, n_chunks = index_directory(path, include=include, config=state.config)
            if n_files:
                state.console.print(f"  [green]Indexed {n_files} files ({n_chunks} chunks)[/green]")
            else:
                state.console.print("  [yellow]No files indexed.[/yellow]")

    elif command == "/index_web":
        if not arg:
            state.console.print("  [yellow]Usage: /index_web <url>[/yellow]")
            state.console.print("  [dim]Example: /index_web https://learn.microsoft.com/powershell[/dim]")
        else:
            with state.console.status(f"[bold cyan]Downloading and indexing {arg}...[/bold cyan]"):
                n_chunks = index_url(arg, config=state.config)
                if n_chunks:
                    state.console.print(f"  [green]Indexed web page successfully ({n_chunks} chunks stored in RAG)[/green]")
                else:
                    state.console.print("  [yellow]No web chunks indexed. Check logs or URL availability.[/yellow]")

    elif command == "/knowledge":
        if not arg:
            state.console.print("  [yellow]Usage: /knowledge <question>[/yellow]")
        else:
            with state.console.status(f"[bold cyan]Searching knowledge base...[/bold cyan]"):
                context = get_rag_context(arg, config=state.config)
            if context:
                state.console.print(Markdown(context))
            else:
                state.console.print("  [dim]No indexed knowledge found. Use /index first.[/dim]")

    elif command == "/memory":
        if not arg:
            if state.memory.facts:
                state.console.print("\n[bold]Persistent memory:[/bold]")
                for i, fact in enumerate(state.memory.facts):
                    state.console.print(f"  {i}. {fact}")
                state.console.print(f"\n  [dim]Use /memory add <fact> or /memory clear[/dim]\n")
            else:
                state.console.print("  [dim]No memories stored. Use /memory add <fact>[/dim]")
        elif arg.startswith("add "):
            fact = arg[4:].strip()
            state.memory.add(fact)
            state.console.print(f"  [green]Remembered: {fact}[/green]")
        elif arg == "clear":
            state.memory.clear()
            state.console.print("  [dim]Memory cleared.[/dim]")
        elif arg.startswith("remove "):
            try:
                idx = int(arg[7:].strip())
                if state.memory.remove(idx):
                    state.console.print(f"  [dim]Removed memory #{idx}[/dim]")
                else:
                    state.console.print("  [red]Invalid index.[/red]")
            except ValueError:
                state.console.print("  [red]Usage: /memory remove <index>[/red]")

    elif command == "/spec":
        if not arg:
            state.console.print("  [yellow]Usage: /spec <feature name>[/yellow]")
            state.console.print("  [dim]Example: /spec Add user authentication[/dim]")
        else:
            state.console.print(f"  [cyan]Generating spec for: {arg}[/cyan]")
            try:
                spec_dir, files = create_spec(arg, ai_generate=True, config=state.config)
                state.console.print(f"  [green]Spec created: {spec_dir}/[/green]")
                for f in files:
                    state.console.print(f"     - {f}")
            except Exception as e:
                state.console.print(f"  [red]Error: {e}[/red]")

    elif command == "/specs":
        specs = list_specs()
        if specs:
            state.console.print("\n[bold]Existing specs:[/bold]")
            for s in specs:
                state.console.print(f"  {s['name']}/  ({', '.join(s['files'])})")
            state.console.print()
        else:
            state.console.print("  [dim]No specs yet. Use /spec <feature> to create one.[/dim]")

    elif command == "/providers":
        providers = get_available_providers()
        state.console.print("\n[bold]LLM Providers:[/bold]")
        for p in providers:
            if p["status"] == "local":
                status = "[green]local (Ollama)[/green]"
            elif p["status"] == "configured":
                status = f"[green]configured[/green] ({p['model']})"
            else:
                status = f"[red]no key[/red] (set {p.get('env_key', '?')})"
            state.console.print(f"  {p['name']:<12} {status}")
        state.console.print()

    elif command == "/plugins":
        plugins = get_loaded_plugins()
        if arg == "reload":
            count = reload_plugins()
            state.console.print(f"  [green]Reloaded: {count} plugin(s)[/green]")
        elif plugins:
            from rich.table import Table
            table = Table(title="Loaded Plugins", header_style="bold magenta", border_style="dim")
            table.add_column("Plugin", style="bold cyan")
            table.add_column("Version")
            table.add_column("Commands")
            table.add_column("Agent Tools")
            table.add_column("Description")
            for p in plugins:
                cmds = ", ".join(p.commands.keys()) if p.commands else "-"
                tool_names = ", ".join(t.name for t in p.get_tools()) if p.get_tools() else "-"
                table.add_row(p.name, p.version, cmds, tool_names, p.description)
            state.console.print(table)
            state.console.print()
        else:
            state.console.print("  [dim]No plugins loaded. Drop .py files in ~/.chatty-chronos/plugins/[/dim]")

    elif command == "/agents":
        from rich.table import Table
        if arg.startswith("register "):
            parts2 = arg[9:].split(None, 2)
            if len(parts2) < 2:
                state.console.print("  [yellow]Usage: /agents register <name> <description> [system_prompt][/yellow]")
            else:
                a_name, a_desc = parts2[0], parts2[1]
                a_prompt = parts2[2] if len(parts2) > 2 else ""
                register_agent(AgentSpec(name=a_name, description=a_desc, system_prompt=a_prompt))
                state.console.print(f"  [green]Agent '{a_name}' registered.[/green]")
        else:
            agents = list_agents()
            table = Table(title="Registered Agent Types", header_style="bold cyan", border_style="dim")
            table.add_column("Name", style="bold yellow")
            table.add_column("Tools Whitelist")
            table.add_column("Max Steps")
            table.add_column("Description")
            for a in agents:
                tools_str = ", ".join(a.tool_names) if a.tool_names else "[all tools]"
                table.add_row(a.name, tools_str, str(a.max_iterations), a.description)
            state.console.print(table)
            state.console.print("  [dim]Use: /agents register <name> <description>[/dim]")
            state.console.print("  [dim]Or in code: from core.agent_registry import register_agent, AgentSpec[/dim]\n")

    elif command == "/doctor":
        state.console.print("\n[bold]System Health Check:[/bold]")
        active_provider = state.config.get("provider", "ollama")
        state.console.print(f"  [green]OK[/green] Provider: {active_provider}")
        
        if active_provider == "llamacpp":
            llamacpp_host = state.config.get("llamacpp_host", "http://localhost:8080")
            if llamacpp_provider.is_available(llamacpp_host):
                state.console.print(f"  [green]OK[/green] llama.cpp: connected at {llamacpp_host}")
            else:
                state.console.print(f"  [red]FAIL[/red] llama.cpp: not running at {llamacpp_host}")
        else:
            models = ollama_provider.list_models(state.config.get("ollama_host"))
            if models:
                state.console.print(f"  [green]OK[/green] Ollama: {len(models)} models available")
            else:
                state.console.print(f"  [red]FAIL[/red] Ollama: not running at {state.config.get('ollama_host')}")
            model = state.config.get("model")
            if models and model in models:
                state.console.print(f"  [green]OK[/green] Model: {model}")
            elif models:
                state.console.print(f"  [yellow]WARN[/yellow] Model '{model}' not found")
        
        state.console.print(f"  [green]OK[/green] Config: {state.config.path}")
        
        embed_provider = state.config.get("embedding_provider", "local")
        if embed_provider == "ollama":
            ollama_host = state.config.get("ollama_host", "http://localhost:11434")
            models = ollama_provider.list_models(ollama_host)
            embed_model = state.config.get("embedding_model", "nomic-embed-text:latest")
            if models and embed_model in models:
                state.console.print(f"  [green]OK[/green] RAG Embeddings: Ollama ({embed_model})")
            elif models:
                state.console.print(f"  [yellow]WARN[/yellow] RAG Embeddings: '{embed_model}' not found")
            else:
                state.console.print(f"  [red]FAIL[/red] RAG Embeddings: Ollama not running at {ollama_host}")
        elif embed_provider == "llamacpp":
            llamacpp_host = state.config.get("llamacpp_host", "http://localhost:8080")
            if llamacpp_provider.is_available(llamacpp_host):
                state.console.print(f"  [green]OK[/green] RAG Embeddings: llama-server ({state.config.get('embedding_model')})")
            else:
                state.console.print(f"  [red]FAIL[/red] RAG Embeddings: llama-server not running at {llamacpp_host}")
        else:
            state.console.print(f"  [green]OK[/green] RAG Embeddings: Local CPU ({state.config.get('embedding_model')})")

        vectordb = state.config.dir / "vectordb"
        if vectordb.exists():
            state.console.print(f"  [green]OK[/green] VectorDB: {vectordb}")
        else:
            state.console.print(f"  [dim]INFO[/dim] VectorDB: not initialized")
            
        plugins = get_loaded_plugins()
        state.console.print(f"  [green]OK[/green] Plugins: {len(plugins)} loaded")
        state.console.print(f"  [green]OK[/green] Memory: {len(state.memory.facts)} facts stored\n")

    elif command == "/logs":
        log_dir = Path.home() / ".chatty-chronos" / "logs"
        if log_dir.exists():
            logs = sorted(log_dir.glob("chronos_*.log"), reverse=True)
            state.console.print(f"\n[bold]Log directory:[/bold] {log_dir}")
            if logs:
                state.console.print(f"  Latest: [cyan]{logs[0].name}[/cyan] ({logs[0].stat().st_size} bytes)")
                state.console.print(f"  Total:  {len(logs)} log files")
            state.console.print()
        else:
            state.console.print("  [dim]No logs yet.[/dim]")

    elif command == "/export":
        filename = arg or "conversation.md"
        if not filename.endswith(".md"):
            filename += ".md"
        lines = [f"# Chatty Chronos Conversation\n"]
        with state.messages_lock:
            for m in state.messages:
                if m["role"] == "system":
                    continue
                prefix = "**You:**" if m["role"] == "user" else "**Chronos:**"
                content = m.get("content", "")
                if content:
                    lines.append(f"\n{prefix}\n{content}\n")
        Path(filename).write_text("\n".join(lines), encoding="utf-8")
        state.console.print(f"  [green]Exported to {filename}[/green]")

    elif command == "/stats":
        with state.messages_lock:
            user_msgs = [m for m in state.messages if m["role"] == "user"]
            assistant_msgs = [m for m in state.messages if m["role"] == "assistant"]
            total_chars = sum(len(m.get("content", "")) for m in state.messages)
        state.console.print("\n[bold]Session Stats:[/bold]")
        state.console.print(f"  Messages: {len(user_msgs)} user, {len(assistant_msgs)} assistant")
        state.console.print(f"  Tool calls: {state._token_usage['tool_calls']}")
        state.console.print(f"  Total context: ~{total_chars} chars")
        state.console.print(f"  Model: {state.config.get('model')}")
        state.console.print(f"  Plugins: {len(get_loaded_plugins())}")
        state.console.print()

    elif command == "/save":
        save_session()
        state.console.print("  [dim]Session saved.[/dim]")

    elif command == "/load":
        if load_session():
            state.console.print("  [dim]Previous session loaded.[/dim]")
        else:
            state.console.print("  [dim]No saved session found.[/dim]")

    elif command == "/tools":
        from rich.table import Table
        tools = get_all_tools()
        table = Table(title="Available AI Tools", header_style="bold green", border_style="dim")
        table.add_column("Tool Name", style="bold cyan")
        table.add_column("Permission Level")
        table.add_column("Description")
        for t in tools:
            perm = "[yellow]Requires Permission[/yellow]" if t.requires_permission else "[green]Auto-Allowed[/green]"
            table.add_row(t.name, perm, t.description)
        state.console.print(table)
        state.console.print()

    elif command == "/agent":
        if not arg:
            state.console.print("  [yellow]Usage: /agent <task description>[/yellow]")
            state.console.print("  [dim]Example: /agent Find all Python files and count lines of code[/dim]")
        else:
            agent = ReActAgent(state.config)
            agent.run(arg)

    else:
        plugin_cmds = get_plugin_commands()
        if command in plugin_cmds:
            result = plugin_cmds[command].handle_command(command, arg)
            if result:
                state.console.print(f"  {result}")
        else:
            state.console.print(f"  [red]Unknown command: {command}[/red]. Type /help")

    return True
