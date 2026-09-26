"""llama.cpp server provider — for custom llama.exe / llama-server builds.

Connects to a llama.cpp server running with --server flag.
Uses the OpenAI-compatible /v1/chat/completions endpoint.

Usage:
  1. Start your llama.exe: llama.exe --server --port 8080 --model model.gguf
  2. Set in Chronos: /config llamacpp_host http://localhost:8080
  3. Set in Chronos: /config provider llamacpp
"""
import json
import httpx


class LlamaCppFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class LlamaCppToolCall:
    def __init__(self, name, arguments):
        self.function = LlamaCppFunction(name, arguments)


class LlamaCppMessage:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = []
        if tool_calls:
            for tc in tool_calls:
                func_data = tc.get("function", {})
                name = func_data.get("name")
                args = func_data.get("arguments")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        pass
                self.tool_calls.append(LlamaCppToolCall(name, args))


class LlamaCppResponse:
    def __init__(self, content, tool_calls=None):
        self.message = LlamaCppMessage(content, tool_calls)


# Default timeout: 10 minutes — large GGUF models on iGPU need time
DEFAULT_TIMEOUT = 600


def chat(messages: list, host: str = "http://localhost:8080", model: str = "local", tools=None, timeout: int = None) -> LlamaCppResponse:
    """Send chat completion to llama.cpp server. Returns LlamaCppResponse wrapper."""
    _timeout = timeout or DEFAULT_TIMEOUT
    url = f"{host}/v1/chat/completions"
    
    formatted_messages = []
    for m in messages:
        fm = {"role": m["role"], "content": m.get("content") or ""}
        if "tool_calls" in m:
            fm["tool_calls"] = m["tool_calls"]
        if "tool_call_id" in m:
            fm["tool_call_id"] = m["tool_call_id"]
        formatted_messages.append(fm)

    payload = {
        "model": "local",
        "messages": formatted_messages,
        "max_tokens": 2048,
        "stream": False,
    }

    if tools:
        payload["tools"] = tools

    try:
        with httpx.Client(timeout=_timeout) as client:
            response = client.post(url, json=payload)
            if response.status_code >= 400:
                import logging
                logging.warning(f"llama.cpp {response.status_code}: {response.text[:200]}")
            response.raise_for_status()
            data = response.json()

            msg_data = data["choices"][0]["message"]
            content = msg_data.get("content") or ""
            tool_calls = msg_data.get("tool_calls") or []

            # Workaround for local models outputting raw JSON in content instead of tool_calls
            if not tool_calls and tools and content:
                import re
                import uuid
                # Try finding markdown JSON blocks first
                code_blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                for block in code_blocks:
                    try:
                        parsed = json.loads(block)
                        if isinstance(parsed, dict) and "name" in parsed and "arguments" in parsed:
                            tool_calls.append({
                                "id": f"call_{uuid.uuid4().hex[:8]}",
                                "type": "function",
                                "function": {
                                    "name": parsed["name"],
                                    "arguments": json.dumps(parsed["arguments"]) if not isinstance(parsed["arguments"], str) else parsed["arguments"]
                                }
                            })
                            content = content.replace(block, "").strip()
                    except json.JSONDecodeError:
                        pass
                
                # Try scanning for bare JSON if no markdown blocks matched
                if not tool_calls:
                    match = re.search(r'\{\s*"name"\s*:', content)
                    if match:
                        start_idx = match.start()
                        brace_count = 0
                        end_idx = -1
                        for i in range(start_idx, len(content)):
                            if content[i] == '{':
                                brace_count += 1
                            elif content[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        if end_idx != -1:
                            json_str = content[start_idx:end_idx]
                            try:
                                parsed = json.loads(json_str)
                                if isinstance(parsed, dict) and "name" in parsed and "arguments" in parsed:
                                    tool_calls.append({
                                        "id": f"call_{uuid.uuid4().hex[:8]}",
                                        "type": "function",
                                        "function": {
                                            "name": parsed["name"],
                                            "arguments": json.dumps(parsed["arguments"]) if not isinstance(parsed["arguments"], str) else parsed["arguments"]
                                        }
                                    })
                                    content = content[:start_idx] + content[end_idx:]
                                    content = content.strip()
                            except json.JSONDecodeError:
                                pass

            return LlamaCppResponse(content, tool_calls)
    except httpx.ReadTimeout:
        raise TimeoutError(
            f"llama.cpp did not respond within {_timeout}s. "
            f"Your model may be too large for available VRAM, or try: /config llamacpp_timeout 900"
        )


def chat_stream(messages: list, host: str = "http://localhost:8080", model: str = "local", tools=None, timeout: int = None):
    """Stream chat completion from llama.cpp server. Yields content chunks.
    Falls back to non-streaming chat if tools are provided.
    """
    _timeout = timeout or DEFAULT_TIMEOUT
    if tools:
        # llama-server doesn't support streaming tool calls reliably in some versions
        res = chat(messages, host, model, tools, timeout=_timeout)
        if res.message.tool_calls:
            from llm.ollama_provider import ToolCallMarker
            yield ToolCallMarker(res.message)
        else:
            yield res.message.content
        return

    url = f"{host}/v1/chat/completions"
    
    formatted_messages = []
    for m in messages:
        fm = {"role": m["role"], "content": m.get("content") or ""}
        if "tool_calls" in m:
            fm["tool_calls"] = m["tool_calls"]
        if "tool_call_id" in m:
            fm["tool_call_id"] = m["tool_call_id"]
        formatted_messages.append(fm)

    payload = {
        "model": "local",
        "messages": formatted_messages,
        "max_tokens": 2048,
        "stream": True,
    }

    try:
        with httpx.Client(timeout=_timeout) as client:
            with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
    except httpx.ReadTimeout:
        raise TimeoutError(
            f"llama.cpp stream timed out after {_timeout}s. "
            f"Try: /config llamacpp_timeout 900"
        )


def is_available(host: str = "http://localhost:8080") -> bool:
    """Check if llama.cpp server is running."""
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get(f"{host}/health")
            # llama-server uses /health returning status ok or 200
            return r.status_code == 200
    except Exception:
        return False

