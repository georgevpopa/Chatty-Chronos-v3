import pytest
from core.config import Config
from llm.llamacpp_provider import chat_stream

def test_streaming():
    config = Config()
    messages = [{"role": "system", "content": "Ce este o masina?"}]
    tool_schema = []
    for chunk in chat_stream(messages, "http://localhost:8080", "local", tools_schema=tool_schema):
        print(chunk)
        break

test_streaming()