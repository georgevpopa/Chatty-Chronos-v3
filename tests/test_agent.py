import os
import pytest
from unittest.mock import patch, MagicMock
from core.agent import ReActAgent
from core.config import Config

class MockResponse:
    def __init__(self, content, tool_calls=None):
        self.message = MagicMock()
        self.message.content = content
        self.message.tool_calls = tool_calls or []

class MockToolCall:
    def __init__(self, name, arguments, tc_id="call_mock123"):
        self.id = tc_id
        self.function = MagicMock()
        self.function.name = name
        self.function.arguments = arguments

def test_react_loop_integration(tmp_path):
    # Setup config
    config = Config()
    config.set("provider", "ollama")
    config.set("model", "test-model")
    
    agent = ReActAgent(config=config, max_iterations=5)
    
    # We will simulate an agent that uses tools successively:
    # 1. list_directory
    # 2. write_file
    # 3. read_file
    # 4. Final response
    
    tc1 = MockToolCall("list_directory", {"path": str(tmp_path)}, tc_id="call_01")
    resp1 = MockResponse("I need to check the directory first.", [tc1])
    
    test_file_path = str(tmp_path / "agent_test.txt")
    tc2 = MockToolCall("write_file", {"path": test_file_path, "content": "success"}, tc_id="call_02")
    resp2 = MockResponse("I will create a file now.", [tc2])
    
    tc3 = MockToolCall("read_file", {"path": test_file_path}, tc_id="call_03")
    resp3 = MockResponse("I will read the file to verify.", [tc3])
    
    resp4 = MockResponse("Task completed successfully.")
    
    responses = [resp1, resp2, resp3, resp4]
    
    def side_effect(*args, **kwargs):
        return responses.pop(0)
    
    # Mock LLM and request_permission
    with patch("core.agent.ollama_provider.chat", side_effect=side_effect), \
         patch("core.agent.request_permission", return_value=True):
        
        final_output = agent.run("Create a test file and verify its contents.")
        
    assert final_output == "Task completed successfully."
    assert agent.iteration == 4
    
    # Check if tools actually executed and modified the filesystem
    assert os.path.exists(test_file_path)
    with open(test_file_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert content == "success"
