"""Context Manager — Handles token calculation and conversation compaction."""
import os
from rich.console import Console
from core.config import Config
from llm import ollama_provider, llamacpp_provider
from llm.fallback import get_available_providers

console = Console()


def call_active_llm(messages: list, config: Config) -> str:
    """Helper to send a chat request using the active LLM provider (without tools)."""
    provider = config.get("provider", "ollama")
    model = config.get("model")
    
    # Check cloud providers
    cloud_provider = None
    for p in get_available_providers():
        if p["name"] == provider:
            cloud_provider = p
            break
            
    try:
        if provider == "llamacpp":
            host = config.get("llamacpp_host", "http://localhost:8080")
            llamacpp_timeout = int(config.get("llamacpp_timeout", 600))
            res = llamacpp_provider.chat(messages, host, model, timeout=llamacpp_timeout)
            return res.message.content or ""
        elif cloud_provider and cloud_provider.get("type") != "ollama":
            from llm import openai_provider
            active_model = config.get("model") or cloud_provider.get("model")
            res = openai_provider.chat(
                messages,
                base_url=cloud_provider["base_url"],
                api_key_name=cloud_provider["env_key"],
                model=active_model
            )
            return res.message.content or ""
        else:
            host = config.get("ollama_host", "http://localhost:11434")
            res = ollama_provider.chat(messages, model, host)
            return res.message.content or ""
    except Exception as e:
        # Fallback to empty string in case of failures
        return ""


def estimate_messages_tokens(messages: list) -> int:
    """Estimate token count for a list of messages. Use tiktoken if available, else fallback."""
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        total = 0
        for m in messages:
            content = m.get("content") or ""
            if "tool_calls" in m and m["tool_calls"]:
                import json
                content += json.dumps(m["tool_calls"])
            total += len(encoding.encode(content)) + 4
        return total
    except Exception:
        # Fallback character length divisor
        total_chars = 0
        for m in messages:
            content = m.get("content") or ""
            if "tool_calls" in m and m["tool_calls"]:
                import json
                try:
                    content += json.dumps(m["tool_calls"])
                except Exception:
                    pass
            total_chars += len(content)
        # 3.2 chars/token is a safe, realistic estimate for mixed code and text
        return int(total_chars / 3.2)


def compact_context(messages: list, config: Config) -> list:
    """Cleans up and compacts the context window by summarizing older messages.
    
    If compaction is disabled, falls back to standard message list pruning.
    """
    max_msgs = config.get("max_context_messages", 20)
    max_tokens = int(config.get("max_context_tokens", 4000))
    
    current_tokens = estimate_messages_tokens(messages)
    
    # Trigger compaction if either threshold is breached
    if len(messages) <= max_msgs + 1 and current_tokens <= max_tokens:
        return messages

    compaction_enabled = config.get("compaction_enabled", True)
    if not compaction_enabled:
        # Standard pruning (keep system prompt + last N messages)
        console.print("  [dim]Context compaction: Pruning older messages...[/dim]")
        return [messages[0]] + messages[-(max_msgs):]

    console.print(f"  [dim]Context compaction: Summarizing old context (~{current_tokens} tokens)...[/dim]")
    
    # We keep the system prompt (messages[0]) and the latest max_msgs // 2 messages
    keep_count = max(4, max_msgs // 2)
    latest_messages = messages[-keep_count:]
    old_messages = messages[1:-keep_count]
    
    # Build text representation of old messages for the summarization prompt
    history_text = ""
    for m in old_messages:
        role = m["role"].upper()
        content = m.get("content") or ""
        if not content and "tool_calls" in m:
            content = f"[Called tools: {', '.join(tc['function']['name'] for tc in m['tool_calls'])}]"
        history_text += f"{role}: {content}\n\n"
        
    summary_prompt = [
        {"role": "system", "content": (
            "You are a helpful assistant. Summarize the following conversation history between "
            "the user and the assistant. Extract all key achievements, decisions, code paths "
            "discussed, and preferences. CRITICAL: You must explicitly preserve technical definitions, "
            "exact file paths, variable names, class/function names, and tool execution outcomes. "
            "Be extremely concise, structured, and factual. Do not use conversational filler."
        )},
        {"role": "user", "content": f"Here is the history to summarize:\n\n{history_text}"}
    ]
    
    summary = call_active_llm(summary_prompt, config)
    
    if summary:
        summary_msg = {
            "role": "system",
            "content": f"## Summary of previous conversation:\n{summary}"
        }
        console.print("  [green]✓ Context compacted successfully.[/green]")
        return [messages[0], summary_msg] + latest_messages
    else:
        # If summarization failed, fallback to standard pruning
        console.print("  [yellow]⚠ Context compaction failed. Falling back to pruning.[/yellow]")
        return [messages[0]] + messages[-(max_msgs):]
