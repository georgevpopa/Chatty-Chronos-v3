"""Ollama LLM provider — local-first, streaming support."""
import json
import ollama


def list_models(host="http://localhost:11434"):
    """Return list of locally available model names."""
    try:
        client = ollama.Client(host=host)
        response = client.list()
        return [m.model for m in response.models]
    except Exception:
        return []


def chat_stream(messages, model, host="http://localhost:11434", tools=None):
    """Stream a chat completion from Ollama. Yields content chunks.
    If tools are provided and model calls a tool, returns tool_calls via exception-like protocol.
    """
    client = ollama.Client(host=host)
    kwargs = {"model": model, "messages": messages, "stream": True}
    if tools:
        # Ollama doesn't stream tool calls — fall back to non-streaming
        return _chat_with_tools(messages, model, host, tools)
    stream = client.chat(**kwargs)
    for chunk in stream:
        content = chunk.message.content
        if content:
            yield content


def chat(messages, model, host="http://localhost:11434", tools=None):
    """Non-streaming chat completion. Returns full response text."""
    client = ollama.Client(host=host)
    kwargs = {"model": model, "messages": messages}
    if tools:
        kwargs["tools"] = tools
    response = client.chat(**kwargs)
    return response


def _chat_with_tools(messages, model, host, tools):
    """Handle tool-calling: returns a generator that either yields content or raises ToolCallResult."""
    client = ollama.Client(host=host)
    response = client.chat(model=model, messages=messages, tools=tools)

    # Check if there are tool calls
    if response.message.tool_calls:
        # Signal tool calls by yielding a special marker
        yield ToolCallMarker(response.message)
    else:
        content = response.message.content or ""
        yield content


class ToolCallMarker:
    """Marker yielded when the LLM wants to call tools instead of responding with text."""
    def __init__(self, message):
        self.message = message
        self.tool_calls = message.tool_calls

