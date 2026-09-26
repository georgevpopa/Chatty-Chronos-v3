import uuid
from rich.markdown import Markdown

from core import state
from core.permissions import request_permission
from tools.registry import get_tool_by_name, get_ollama_tools_schema
from core.context import compact_context
from rag.retriever import get_rag_context
from llm import ollama_provider, llamacpp_provider
from llm.fallback import get_available_providers
from core.logger import log


def execute_tool_call(tool_call) -> str:
    """Execute a single tool call with permission checking."""
    func_name = tool_call.function.name
    args = tool_call.function.arguments

    tool = get_tool_by_name(func_name)
    if not tool:
        return f"Error: Unknown tool '{func_name}'"

    # Permission check
    if tool.requires_permission:
        desc = f"{func_name}({', '.join(f'{k}={repr(v)[:50]}' for k,v in args.items())})"
        
        diff_text = None
        if hasattr(tool, "get_diff"):
            try:
                diff_text = tool.get_diff(**args)
            except Exception:
                pass
                
        if not request_permission(func_name, desc, diff_text=diff_text):
            return "Permission denied by user."

    state.console.print(f"  [dim]→ {func_name}({', '.join(f'{k}={repr(v)[:30]}' for k,v in args.items())})[/dim]")
    
    # Pass config and depth if the tool signature accepts them
    extra_args = {}
    import inspect
    sig = inspect.signature(tool.execute)
    if "config" in sig.parameters:
        extra_args["config"] = state.config
    if "depth" in sig.parameters:
        extra_args["depth"] = 0
        
    result = tool.execute(**args, **extra_args)
    return result


def send_message_stream(user_input):
    """Generator version of send_message that yields SSE events for Web UI."""
    with state.messages_lock:
        yield from _send_message_stream_locked(user_input)


def _send_message_stream_locked(user_input):
    if user_input.startswith("/"):
        yield {"type": "status", "content": f"Executing command: {user_input}"}
        from cli.commands import handle_command
        handle_command(user_input)
        yield {"type": "done", "messages": state.messages}
        return

    state.messages.append({"role": "user", "content": user_input})
    state._token_usage["messages"] += 1

    model = state.config.get("model")
    provider = state.config.get("provider", "ollama")

    cloud_provider = None
    for p in get_available_providers():
        if p["name"] == provider:
            cloud_provider = p
            break

    if provider == "llamacpp":
        host = state.config.get("llamacpp_host", "http://localhost:8080")
    else:
        host = state.config.get("ollama_host", "http://localhost:11434")
    tools_schema = get_ollama_tools_schema()

    yield {"type": "status", "content": "Retrieving context & memory..."}
    with state.console.status("[bold cyan]Retrieving context & memory...[/bold cyan]"):
        rag_context = get_rag_context(user_input, config=state.config)
        
        from core.memory import search_memory
        past_experiences = search_memory(user_input, n_results=3)
        memory_context = ""
        if past_experiences:
            memory_context = "\n\nPast relevant context from Memory:\n"
            for i, exp in enumerate(past_experiences):
                memory_context += f"[{i+1}] {exp['content']}\n"
                
        system_content = state.SYSTEM_PROMPT + memory_context
        if rag_context:
            system_content += "\n\n" + rag_context
        state.messages[0]["content"] = system_content

    max_iterations = int(state.config.get("agent_max_iterations", 15))

    try:
        for iteration in range(max_iterations):
            yield {"type": "status", "content": f"Thinking... (step {iteration + 1}/{max_iterations})"}
            
            if provider == "llamacpp":
                llamacpp_timeout = int(state.config.get("llamacpp_timeout", 600))
                stream_generator = llamacpp_provider.chat_stream(state.messages, host, model, tools=tools_schema, timeout=llamacpp_timeout)
            elif cloud_provider and cloud_provider.get("type") != "ollama":
                from llm import openai_provider
                active_model = state.config.get("model") or cloud_provider.get("model")
                res = openai_provider.chat(
                    state.messages,
                    base_url=cloud_provider["base_url"],
                    api_key_name=cloud_provider["env_key"],
                    model=active_model,
                    tools=tools_schema
                )
                if res.message.tool_calls:
                    from llm.ollama_provider import ToolCallMarker
                    stream_generator = [ToolCallMarker(res.message)]
                else:
                    stream_generator = [res.message.content]
            else:
                stream_generator = ollama_provider.chat_stream(state.messages, model, host, tools=tools_schema)

            final_text_chunks = []
            tool_call_marker = None
            
            for chunk in stream_generator:
                from llm.ollama_provider import ToolCallMarker
                if isinstance(chunk, ToolCallMarker):
                    tool_call_marker = chunk
                    break
                else:
                    final_text_chunks.append(chunk)
                    yield {"type": "token", "content": chunk}

            if tool_call_marker:
                tool_calls_payload = []
                for tc in tool_call_marker.tool_calls:
                    tc_id = getattr(tc, "id", None) or f"call_{uuid.uuid4().hex[:8]}"
                    tc.id = tc_id
                    tool_calls_payload.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    })
                state.messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls_payload})

                yield {"type": "tool_calls", "content": tool_calls_payload}

                for tc in tool_call_marker.tool_calls:
                    func_name = tc.function.name
                    yield {"type": "status", "content": f"Executing tool: {func_name}..."}
                    result = execute_tool_call(tc)
                    state._token_usage["tool_calls"] += 1
                    state.messages.append({"role": "tool", "content": result, "tool_call_id": tc.id})
                    yield {"type": "tool_result", "name": func_name, "result": result}
                continue

            final_text = "".join(final_text_chunks)
            state.messages.append({"role": "assistant", "content": final_text})
            
            if state.config.get("self_reflection", False):
                yield {"type": "status", "content": "Running Self-Reflection..."}
                is_ok, feedback = _run_self_reflection(user_input, final_text, provider, model, host, cloud_provider)
                if not is_ok:
                    yield {"type": "status", "content": f"Reviewer requested changes..."}
                    state.messages.append({"role": "user", "content": f"[Reviewer Feedback]: The task is incomplete or incorrect. Please fix it based on this feedback: {feedback}"})
                    continue
                    
            break
        else:
            yield {"type": "status", "content": f"Reached max iterations ({max_iterations}). Stopping."}

        state.messages = compact_context(state.messages, state.config)
        yield {"type": "done", "messages": state.messages}

    except Exception as e:
        yield {"type": "error", "content": str(e)}
        if len(state.messages) > 0 and state.messages[-1]["role"] == "user":
            state.messages.pop()
    finally:
        state.messages[0]["content"] = state.SYSTEM_PROMPT + state.memory.get_context()


def send_message(user_input):
    """Send message to LLM, handle tool calls, stream final response."""
    with state.messages_lock:
        return _send_message_locked(user_input)


def _send_message_locked(user_input):
    state.messages.append({"role": "user", "content": user_input})
    state._token_usage["messages"] += 1

    model = state.config.get("model")
    provider = state.config.get("provider", "ollama")

    cloud_provider = None
    for p in get_available_providers():
        if p["name"] == provider:
            cloud_provider = p
            break

    if provider == "llamacpp":
        host = state.config.get("llamacpp_host", "http://localhost:8080")
    else:
        host = state.config.get("ollama_host", "http://localhost:11434")
    tools_schema = get_ollama_tools_schema()

    with state.console.status("[bold cyan]Retrieving context & memory...[/bold cyan]"):
        rag_context = get_rag_context(user_input, config=state.config)
        
        from core.memory import search_memory
        past_experiences = search_memory(user_input, n_results=3)
        memory_context = ""
        if past_experiences:
            memory_context = "\n\nPast relevant context from Memory:\n"
            for i, exp in enumerate(past_experiences):
                memory_context += f"[{i+1}] {exp['content']}\n"
                
        system_content = state.SYSTEM_PROMPT + memory_context
        if rag_context:
            system_content += "\n\n" + rag_context
            
        state.messages[0]["content"] = system_content

    max_iterations = int(state.config.get("agent_max_iterations", 15))

    try:
        for iteration in range(max_iterations):
            with state.console.status(f"[bold cyan]Thinking... (step {iteration + 1}/{max_iterations})[/bold cyan]"):
                if provider == "llamacpp":
                    llamacpp_timeout = int(state.config.get("llamacpp_timeout", 600))
                    response = llamacpp_provider.chat(state.messages, host, model, tools=tools_schema, timeout=llamacpp_timeout)
                elif cloud_provider and cloud_provider.get("type") != "ollama":
                    from llm import openai_provider
                    active_model = state.config.get("model") or cloud_provider.get("model")
                    response = openai_provider.chat(
                        state.messages,
                        base_url=cloud_provider["base_url"],
                        api_key_name=cloud_provider["env_key"],
                        model=active_model,
                        tools=tools_schema
                    )
                else:
                    response = ollama_provider.chat(state.messages, model, host, tools=tools_schema)

            if response.message.tool_calls:
                for tc in response.message.tool_calls:
                    if not getattr(tc, "id", None):
                        tc.id = f"call_{uuid.uuid4().hex[:8]}"

                state.messages.append({"role": "assistant", "content": "", "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    }
                    for tc in response.message.tool_calls
                ]})

                for tc in response.message.tool_calls:
                    result = execute_tool_call(tc)
                    state._token_usage["tool_calls"] += 1
                    state.messages.append({"role": "tool", "content": result, "tool_call_id": tc.id})

                continue

            final_text = response.message.content or ""
            if final_text:
                state.console.print()
                state.console.print(Markdown(final_text))
                state.console.print()
            else:
                state.console.print("\n  [green]✅ Procesare finalizată (niciun răspuns text).[/green]\n")
            state.messages.append({"role": "assistant", "content": final_text})
            
            if state.config.get("self_reflection", False):
                state.console.print("[dim]  Running Self-Reflection...[/dim]")
                is_ok, feedback = _run_self_reflection(user_input, final_text, provider, model, host, cloud_provider)
                if not is_ok:
                    state.console.print(f"[yellow]  Reviewer Feedback: {feedback}[/yellow]")
                    state.messages.append({"role": "user", "content": f"[Reviewer Feedback]: The task is incomplete or incorrect. Please fix it based on this feedback: {feedback}"})
                    continue

            break
        else:
            state.console.print(f"[yellow]  Reached max iterations ({max_iterations}). Stopping.[/yellow]\n")

        state.messages = compact_context(state.messages, state.config)

    except Exception as e:
        error_msg = str(e)
        log.error(f"LLM error ({provider}): {error_msg}", exc_info=True)
        if provider == "llamacpp":
            llamacpp_host = state.config.get("llamacpp_host", "http://localhost:8080")
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                state.console.print(f"[red]  Cannot connect to llama.cpp server at {llamacpp_host}[/red]")
                state.console.print(f"  [dim]Start your server: llama-server --port 8080 --model your.gguf[/dim]\n")
            else:
                state.console.print(f"[red]  llama.cpp error: {error_msg}[/red]\n")
        else:
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                state.console.print("[red]  Cannot connect to Ollama. Is it running?[/red]")
                state.console.print(f"  [dim]Host: {host}[/dim]\n")
            elif "not found" in error_msg.lower() or "404" in error_msg:
                state.console.print(f"[red]  Model '{model}' not found. Run: ollama pull {model}[/red]\n")
            else:
                state.console.print(f"[red]  Error: {error_msg}[/red]\n")
        state.messages.pop()
    finally:
        state.messages[0]["content"] = state.SYSTEM_PROMPT + state.memory.get_context()

def _run_self_reflection(user_input, final_text, provider, model, host, cloud_provider):
    """Run a separate LLM call to evaluate if the response fully answers the user input."""
    from llm.ollama_provider import chat_stream
    from llm.openai_provider import chat
    from llm import llamacpp_provider

    prompt = f"""
You are an expert Reviewer Agent.
The user asked:
{user_input}

The agent replied:
{final_text}

Did the agent completely and correctly fulfill the user's request without cutting corners or leaving TODOs?
Respond ONLY with 'YES' if it is perfect.
If it is incomplete or flawed, respond with 'NO: <specific reason and instructions to fix>'.
""".strip()

    messages = [
        {"role": "system", "content": "You are a strict code and task reviewer."},
        {"role": "user", "content": prompt}
    ]

    try:
        response_text = ""
        if provider == "llamacpp":
            for chunk in llamacpp_provider.chat_stream(messages, host, model, tools=[]):
                response_text += chunk
        elif cloud_provider and cloud_provider.get("type") != "ollama":
            active_model = state.config.get("model") or cloud_provider.get("model")
            res = chat(
                messages,
                base_url=cloud_provider["base_url"],
                api_key_name=cloud_provider["env_key"],
                model=active_model,
                tools=[]
            )
            response_text = res.message.content or ""
        else:
            for chunk in chat_stream(messages, model, host, tools=[]):
                response_text += chunk
        
        response_text = response_text.strip()
        if response_text.upper().startswith("YES"):
            return True, ""
        else:
            feedback = response_text[3:].strip() if response_text.upper().startswith("NO:") else response_text
            return False, feedback
    except Exception as e:
        return True, "" # Skip on error
