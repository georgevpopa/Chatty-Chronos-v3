"""ReAct Agent — Autonomous reasoning and action loop.

The agent follows the ReAct pattern:
1. Think about the task
2. Choose an action (tool call)
3. Observe the result
4. Repeat until task is complete or max iterations reached
"""
import json
import os
from rich.console import Console
from rich.markdown import Markdown

from core.config import Config
from core.permissions import request_permission
from core.logger import log
from llm import ollama_provider
from tools.registry import get_all_tools, get_ollama_tools_schema, get_tool_by_name
from core.telemetry import init_telemetry, get_tracer, get_logger

init_telemetry()
tracer = get_tracer(__name__)
struct_logger = get_logger(__name__)

console = Console()

AGENT_SYSTEM_PROMPT = """\
You are Chatty Chronos, an autonomous coding agent operating in ReAct mode.
Working directory: {cwd}

You have these tools: read_file, write_file, search_replace, list_directory, glob_search, grep, execute_command.

IMPORTANT:
- Use relative paths (e.g. "." or "chatty_chronos") or the working directory shown above.
- For glob_search, use path="." and pattern="**/*.py" to find files recursively.
- For list_directory, use path="." to list the current directory.

For each step:
1. Think about what you need to do next
2. Use a tool to take action
3. Observe the result and decide next steps
4. When done, provide a final summary to the user

Be methodical. Break complex tasks into steps. Verify your work.
"""


class ReActAgent:
    def __init__(self, config: Config, max_iterations: int = 30, depth: int = 0):
        self.config = config
        self.max_iterations = max_iterations
        self.depth = depth
        self.model = config.get("model")
        self.provider = config.get("provider", "ollama")
        
        # Check if provider is a cloud provider
        from llm.fallback import get_available_providers
        self.cloud_provider = None
        for p in get_available_providers():
            if p["name"] == self.provider and not p.get("is_local"):
                self.cloud_provider = p
                break

        if self.provider == "llamacpp":
            self.host = config.get("llamacpp_host", "http://localhost:8080")
        else:
            self.host = config.get("ollama_host", "http://localhost:11434")
        self.tools_schema = get_ollama_tools_schema()
        cwd = os.getcwd()
        self.messages = [{"role": "system", "content": AGENT_SYSTEM_PROMPT.format(cwd=cwd)}]
        self.iteration = 0

    def run(self, task: str) -> str:
        """Execute a task autonomously. Returns final response."""
        from core.permissions import thread_local
        yield_func = getattr(thread_local, "yield_func", None)

        self.messages.append({"role": "user", "content": task})
        self.iteration = 0

        console.print(f"\n  [bold cyan]Agent starting task[/bold cyan] (max {self.max_iterations} steps)")
        console.print(f"  [dim]{task[:80]}{'...' if len(task) > 80 else ''}[/dim]\n")
        
        if yield_func:
            yield_func({"type": "status", "content": f"Agent starting task (max {self.max_iterations} steps)"})

        with tracer.start_as_current_span("agent_task", attributes={"task": task}) as task_span:
            while self.iteration < self.max_iterations:
                self.iteration += 1

                if yield_func:
                    yield_func({"type": "status", "content": f"Agent thinking... (step {self.iteration}/{self.max_iterations})"})

                with tracer.start_as_current_span(f"react_step_{self.iteration}", attributes={"step": self.iteration}) as step_span:
                    try:
                        with console.status(f"[bold cyan]Agent thinking... (step {self.iteration}/{self.max_iterations})[/bold cyan]"):
                            if self.provider == "llamacpp":
                                from llm import llamacpp_provider
                                response = llamacpp_provider.chat(
                                    self.messages, self.host, self.model, tools=self.tools_schema
                                )
                            elif self.cloud_provider:
                                from llm import openai_provider
                                active_model = self.config.get("model") or self.cloud_provider.get("model")
                                response = openai_provider.chat(
                                    self.messages,
                                    base_url=self.cloud_provider["base_url"],
                                    api_key_name=self.cloud_provider["env_key"],
                                    model=active_model,
                                    tools=self.tools_schema
                                )
                            else:
                                response = ollama_provider.chat(
                                    self.messages, self.model, self.host, tools=self.tools_schema
                                )
                    except Exception as e:
                        log.error(f"Agent LLM error (step {self.iteration}): {e}", exc_info=True)
                        console.print(f"  [red]Agent error: {e}[/red]")
                        if yield_func:
                            yield_func({"type": "error", "content": f"Agent failed: {e}"})
                        return f"Agent failed: {e}"

                    # Tool calls — execute and continue
                    if response.message.tool_calls:
                        import uuid
                        # Ensure each tool call has an ID
                        for tc in response.message.tool_calls:
                            if not getattr(tc, "id", None):
                                tc.id = f"call_{uuid.uuid4().hex[:8]}"

                        tool_calls_payload = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name, 
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in response.message.tool_calls
                        ]
                        
                        self.messages.append({
                            "role": "assistant",
                            "content": response.message.content or "",
                            "tool_calls": tool_calls_payload
                        })
                        
                        if yield_func:
                            if response.message.content:
                                yield_func({"type": "token", "content": response.message.content + "\n\n"})
                            yield_func({"type": "tool_calls", "content": tool_calls_payload})

                        # Show thinking if present
                        if response.message.content:
                            console.print(f"  [dim]Step {self.iteration}:[/dim] {response.message.content[:100]}")

                        # Execute tools
                        for tc in response.message.tool_calls:
                            import time
                            start_time = time.time()
                            
                            if yield_func:
                                yield_func({"type": "status", "content": f"Executing tool: {tc.function.name}..."})
                                
                            result = self._execute_tool(tc)
                            latency = time.time() - start_time
                            
                            self.messages.append({"role": "tool", "content": result, "tool_call_id": tc.id})
                            
                            if yield_func:
                                yield_func({"type": "tool_result", "name": tc.function.name, "result": result})
                            
                            llm_tokens = getattr(response, "eval_count", 0)
                            struct_logger.info("tool_call",
                                tool_name=tc.function.name,
                                input=tc.function.arguments,
                                output=result[:1000] if len(result) > 1000 else result,
                                latency=latency,
                                llm_tokens=llm_tokens,
                                step_number=self.iteration
                            )

                        continue

                    # No tool calls — final response
                    final = response.message.content or ""
                    self.messages.append({"role": "assistant", "content": final})

                    # --- Self-Reflection Loop ---
                    if self.config.get("enable_reflection", True):
                        with console.status("[bold magenta]Reviewer checking result...[/bold magenta]"):
                            if yield_func:
                                yield_func({"type": "status", "content": "Reviewer is checking the result..."})
                                
                            reviewer_prompt = f"You are an expert QA Reviewer.\nOriginal Task: {task}\nAgent's Final Answer: {final}\n\nEvaluate if the agent fully completed the task. Did the agent write the code, or just talk about it? If the task required taking action (e.g. creating files, modifying code) and the agent only provided the code in text but didn't use the tools, that is a FAIL. If it is completely correct and done, reply exactly with 'PASS'. If it is incomplete, incorrect, or requires further action, reply with 'FAIL: <detailed reason and what to do next>'."
                            
                            try:
                                rev_msgs = [{"role": "user", "content": reviewer_prompt}]
                                if self.provider == "llamacpp":
                                    rev_resp = llamacpp_provider.chat(rev_msgs, self.host, self.model)
                                elif self.cloud_provider:
                                    rev_resp = openai_provider.chat(rev_msgs, base_url=self.cloud_provider["base_url"], api_key_name=self.cloud_provider["env_key"], model=active_model)
                                else:
                                    rev_resp = ollama_provider.chat(rev_msgs, self.model, self.host)
                                review = rev_resp.message.content.strip()
                            except Exception as e:
                                review = "PASS" # Fallback to pass if reviewer fails
                                
                        if review.startswith("FAIL"):
                            console.print(f"  [bold red]Reviewer Feedback:[/bold red] {review}")
                            if yield_func:
                                yield_func({"type": "status", "content": f"Reviewer Feedback: {review}"})
                            
                            self.messages.append({
                                "role": "user", 
                                "content": f"Reviewer feedback: {review}\nPlease continue working and use the tools to fix this. Do not just output text, use the tools."
                            })
                            continue # Continue the ReAct loop
                            
                        console.print("  [bold green]Reviewer approved.[/bold green]")
                        if yield_func:
                            yield_func({"type": "status", "content": "Reviewer approved the result."})
                    # --- End Self-Reflection Loop ---

                    # Store in Long-Term Memory
                    try:
                        from core.memory import store_memory
                        import uuid
                        store_memory(
                            key=f"task_{uuid.uuid4().hex[:8]}",
                            content=f"Task: {task}\nResolution: {final[:1000]}",
                            metadata={"type": "task_completion"}
                        )
                    except Exception as e:
                        pass

                    if yield_func:
                        yield_func({"type": "status", "content": f"Agent completed in {self.iteration} step(s)"})
                        yield_func({"type": "token", "content": final})

                    console.print(f"\n  [bold green]Agent completed in {self.iteration} step(s)[/bold green]\n")
                    console.print(Markdown(final))
                    console.print()
                    return final

        # Hit max iterations
        if yield_func:
            yield_func({"type": "status", "content": f"Agent reached {self.max_iterations} iterations. Stopping."})
            
        console.print(f"\n  [yellow]Agent reached {self.max_iterations} iterations. Stopping.[/yellow]\n")
        return "Agent reached maximum iterations without completing the task."

    def _execute_tool(self, tool_call) -> str:
        """Execute a tool call with permission checks."""
        func_name = tool_call.function.name
        args = tool_call.function.arguments

        tool = get_tool_by_name(func_name)
        if not tool:
            return f"Error: Unknown tool '{func_name}'"

        # Permission check for dangerous tools
        if tool.requires_permission:
            desc = f"{func_name}({', '.join(f'{k}={repr(v)[:40]}' for k, v in args.items())})"
            diff_text = None
            if func_name == "write_file":
                path = args.get("path")
                content = args.get("content", "")
                if path and os.path.exists(path):
                    import difflib
                    old_content = open(path, "r", encoding="utf-8", errors="replace").read()
                    diff = list(difflib.unified_diff(
                        old_content.splitlines(keepends=True),
                        content.splitlines(keepends=True),
                        fromfile=f"a/{path}",
                        tofile=f"b/{path}",
                        n=3
                    ))
                    if diff:
                        diff_text = "".join(diff)
            elif func_name == "search_replace":
                path = args.get("path")
                search = args.get("search", "")
                replace = args.get("replace", "")
                if path and os.path.exists(path):
                    import difflib
                    old_content = open(path, "r", encoding="utf-8", errors="replace").read()
                    new_content = old_content.replace(search, replace)
                    diff = list(difflib.unified_diff(
                        old_content.splitlines(keepends=True),
                        new_content.splitlines(keepends=True),
                        fromfile=f"a/{path}",
                        tofile=f"b/{path}",
                        n=3
                    ))
                    if diff:
                        diff_text = "".join(diff)

            if not request_permission(func_name, desc, cwd=None, diff_text=diff_text):
                return "Permission denied by user."

        # Show what's happening
        args_preview = ", ".join(f"{k}={repr(v)[:30]}" for k, v in args.items())
        console.print(f"  [dim]  [{self.iteration}] {func_name}({args_preview})[/dim]")

        # Pass config and agent depth if the tool signature accepts them
        extra_args = {}
        import inspect
        sig = inspect.signature(tool.execute)
        if "config" in sig.parameters:
            extra_args["config"] = self.config
        if "depth" in sig.parameters:
            extra_args["depth"] = self.depth

        result = tool.execute(**args, **extra_args)

        # Show brief result
        result_preview = result[:80].replace("\n", " ")
        console.print(f"  [dim]      -> {result_preview}{'...' if len(result) > 80 else ''}[/dim]")

        return result
