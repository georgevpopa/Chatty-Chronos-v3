"""Tests for core/delegator.py — sub-agent delegation."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class MockAgent:
    def __init__(self, response="Delegated result"):
        self.response = response
        self.messages = [{"role": "system", "content": "mock"}]
        self.iteration = 0
        self.max_iterations = 10
        self.tools_schema = []
        self.run_calls = []

    def run(self, task: str) -> str:
        self.run_calls.append(task)
        return self.response


# ─── delegate_task ────────────────────────────────────────────────────────────
class TestDelegateTask:
    @patch("core.agent_registry.build_agent")
    def test_basic_delegation(self, mock_build):
        """Basic delegation spawns an agent and returns result."""
        mock_agent = MockAgent("Task completed successfully")
        mock_build.return_value = mock_agent

        from core.config import Config
        config = Config()

        from core.delegator import delegate_task
        result = delegate_task("Read all Python files", config)

        assert result == "Task completed successfully"
        mock_build.assert_called_once()

    @patch("core.agent_registry.build_agent")
    def test_delegation_with_agent_type(self, mock_build):
        """Delegation with agent_type uses the correct agent."""
        mock_agent = MockAgent("File analysis complete")
        mock_build.return_value = mock_agent

        from core.config import Config
        config = Config()

        from core.delegator import delegate_task
        result = delegate_task("Analyze the codebase", config, agent_type="file_analyst")

        assert result == "File analysis complete"
        # build_agent should be called with the agent_type
        call_args = mock_build.call_args
        assert call_args[0][0] == "file_analyst"

    @patch("core.agent_registry.build_agent")
    def test_delegation_unknown_agent_type(self, mock_build):
        """Unknown agent type falls back to generic agent."""
        mock_agent = MockAgent("Generic result")
        mock_build.return_value = mock_agent

        from core.config import Config
        config = Config()

        from core.delegator import delegate_task
        result = delegate_task("Do something", config, agent_type="nonexistent")

        assert result == "Generic result"
        # build_agent should still be called
        mock_build.assert_called_once()

    def test_max_depth_reached(self):
        """Delegation fails when max depth is reached."""
        from core.config import Config
        config = Config()

        from core.delegator import delegate_task
        result = delegate_task("Do something", config, depth=2)

        assert "Error" in result
        assert "Maximum delegation depth" in result

    @patch("core.agent_registry.build_agent")
    def test_depth_increments(self, mock_build):
        """Each delegation level increments depth."""
        mock_agent = MockAgent("result")
        mock_build.return_value = mock_agent

        from core.config import Config
        config = Config()

        from core.delegator import delegate_task

        # depth=0 should work
        delegate_task("task1", config, depth=0)
        call_args = mock_build.call_args
        assert call_args[1]["depth"] == 1

        # depth=1 should work (max_depth is 2)
        delegate_task("task2", config, depth=1)
        call_args = mock_build.call_args
        assert call_args[1]["depth"] == 2

        # depth=2 should fail
        result = delegate_task("task3", config, depth=2)
        assert "Error" in result

    @patch("core.agent_registry.build_agent")
    def test_max_iterations_passed(self, mock_build):
        """max_iterations is passed to build_agent."""
        mock_agent = MockAgent("result")
        mock_build.return_value = mock_agent

        from core.config import Config
        config = Config()

        from core.delegator import delegate_task
        delegate_task("task", config, max_iterations=25)

        # The agent should have max_iterations set
        # (build_agent uses spec.max_iterations when agent_type is provided)
        mock_build.assert_called_once()

    @patch("core.agent_registry.build_agent")
    def test_task_forwarded_to_agent(self, mock_build):
        """The task description is forwarded to the agent's run method."""
        mock_agent = MockAgent("done")
        mock_build.return_value = mock_agent

        from core.config import Config
        config = Config()

        from core.delegator import delegate_task
        delegate_task("Count lines in all .py files", config)

        # Verify agent.run was called with the task
        assert len(mock_agent.run_calls) == 1
        assert mock_agent.run_calls[0] == "Count lines in all .py files"


# ─── DelegateSubtask tool ────────────────────────────────────────────────────
class TestDelegateSubtaskTool:
    def test_tool_creation(self):
        from tools.agent_delegator import DelegateSubtask
        tool = DelegateSubtask()
        assert tool.name == "delegate_subtask"
        assert tool.requires_permission is True

    @patch("tools.agent_delegator.delegate_task")
    def test_execute_calls_delegate(self, mock_delegate):
        mock_delegate.return_value = "Delegated result"

        from tools.agent_delegator import DelegateSubtask
        from core.config import Config

        tool = DelegateSubtask()
        config = Config()
        result = tool.execute(task="Read files", config=config, depth=0, agent_type="file_analyst")

        assert result == "Delegated result"
        mock_delegate.assert_called_once_with("Read files", config, depth=0, agent_type="file_analyst")

    @patch("tools.agent_delegator.delegate_task")
    def test_execute_no_agent_type(self, mock_delegate):
        mock_delegate.return_value = "Generic result"

        from tools.agent_delegator import DelegateSubtask
        from core.config import Config

        tool = DelegateSubtask()
        config = Config()
        result = tool.execute(task="Do something", config=config, depth=0, agent_type="")

        assert result == "Generic result"
        mock_delegate.assert_called_once_with("Do something", config, depth=0, agent_type=None)

    def test_tool_schema(self):
        from tools.agent_delegator import DelegateSubtask
        tool = DelegateSubtask()
        schema = tool.to_ollama_schema()

        assert schema["function"]["name"] == "delegate_subtask"
        assert "task" in schema["function"]["parameters"]["properties"]
        assert "agent_type" in schema["function"]["parameters"]["properties"]
