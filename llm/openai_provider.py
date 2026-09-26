"""Generic OpenAI-compatible API provider (for Groq, Gemini, OpenRouter, Mistral, etc.).

Supports standard OpenAI chat completions endpoint and tool-calling format.
"""
import os
import json
import httpx
from llm.llamacpp_provider import LlamaCppResponse


def chat(messages: list, base_url: str, api_key_name: str, model: str, tools=None) -> LlamaCppResponse:
    """Send chat completion to OpenAI-compatible cloud provider."""
    # Hot-reload environment variables to capture newly added keys
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path.cwd() / ".env", override=True)
    load_dotenv(Path.home() / ".chatty-chronos" / ".env", override=True)

    api_key = os.environ.get(api_key_name, "")
    if not api_key:
        raise ValueError(f"API key not found in environment: {api_key_name}. Please check your .env file.")

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
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
    }

    if tools:
        payload["tools"] = tools

    with httpx.Client(timeout=120) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        msg_data = data["choices"][0]["message"]
        content = msg_data.get("content") or ""
        tool_calls = msg_data.get("tool_calls")
        
        return LlamaCppResponse(content, tool_calls)
