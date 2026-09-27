"""Generic OpenAI-compatible API provider (for Groq, Gemini, OpenRouter, Mistral, etc.).

Supports standard OpenAI chat completions endpoint and tool-calling format.
"""
import os
import json
import httpx
from llm.llamacpp_provider import LlamaCppResponse


def chat(messages: list, base_url: str, api_key_name: str = "", model: str = "", tools=None) -> LlamaCppResponse:
    """Send chat completion to an OpenAI-compatible endpoint.

    Works with cloud providers (Groq, Gemini, OpenRouter, ...) AND local/self-hosted
    gateways (e.g. OmniRoute, LM Studio) that may not require an API key.

    Args:
        base_url: e.g. "https://api.groq.com/openai/v1" or "http://host:20128/v1"
        api_key_name: name of the env var holding the key. If empty or unset, the
                      request is sent without an Authorization header (keyless gateways).
        model: model id to request.
    """
    # Hot-reload environment variables to capture newly added keys
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path.cwd() / ".env", override=True)
    load_dotenv(Path.home() / ".chatty-chronos" / ".env", override=True)

    api_key = os.environ.get(api_key_name, "") if api_key_name else ""

    url = f"{base_url}/chat/completions"
    headers = {"Content-Type": "application/json"}
    # Authorization is optional — many local gateways accept keyless requests.
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    formatted_messages = []
    for m in messages:
        fm = {"role": m["role"], "content": m.get("content") or ""}
        if "tool_calls" in m:
            fm["tool_calls"] = m["tool_calls"]
        if "tool_call_id" in m:
            fm["tool_call_id"] = m["tool_call_id"]
        formatted_messages.append(fm)

    payload = {
        "model": model,
        "messages": formatted_messages,
        "max_tokens": 4096,
        "stream": False,
    }

    if tools:
        payload["tools"] = tools

    with httpx.Client(timeout=120) as client:
        response = client.post(url, json=payload, headers=headers)

        # Friendly handling for common gateway/cloud errors instead of a raw traceback.
        if response.status_code == 413:
            raise RuntimeError(
                "Payload too large for this provider (413). The conversation or a fetched "
                "page is too big. Try /clear, or a provider/model with a larger input limit."
            )
        if response.status_code == 429:
            raise RuntimeError(
                "Provider rate-limited the request (429). Wait a moment or switch provider/model."
            )
        response.raise_for_status()

        text = response.text.strip()
        try:
            data = response.json()
        except Exception:
            # Some gateways still stream SSE ("data: {...}" lines) even with
            # stream=False. Try to recover the last JSON object from an SSE body.
            data = None
            for line in reversed(text.splitlines()):
                line = line.strip()
                if line.startswith("data:"):
                    line = line[len("data:"):].strip()
                if line in ("", "[DONE]"):
                    continue
                try:
                    import json as _json
                    data = _json.loads(line)
                    break
                except Exception:
                    continue
            if data is None:
                raise RuntimeError(
                    f"Provider returned a non-JSON response (first 200 chars): {text[:200]!r}"
                )

        try:
            msg_data = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(f"Unexpected response shape from provider: {str(data)[:200]}")
        content = msg_data.get("content") or ""
        tool_calls = msg_data.get("tool_calls")

        return LlamaCppResponse(content, tool_calls)
