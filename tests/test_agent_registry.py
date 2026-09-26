"""Tests for core/agent_registry.py — agent registration and building."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestAgentSpec:
    def test_default_values(self):
        from core.agent_registry import AgentSpec
        spec = AgentSpec(name="test", description="A test agent")
        assert spec.name == "test"
        assert spec.description == "A test agent"
        assert spec.system_prompt == ""
        assert spec.tool_names == []
        assert spec.max_iterations == 20
        assert spec.version == "1.0.0"

    def test_custom_values(self):
        from core.agent_registry import AgentSpec
        spec = AgentSpec(
            name="custom",
            description="Custom agent",
            system_prompt="You are custom.",
            tool_names=["read_file", "write_file"],
            max_iterations=10,
            version="2.0.0",
        )
        assert spec.name == "custom"
        assert spec.system_prompt == "You are custom."
        assert spec.tool_names == ["read_file", "write_file"]
        assert spec.max_iterations == 10
        assert spec.version == "2.0.0"


class TestRegistry:
    def test_builtin_agents_registered(self):
        from core.agent_registry import list_agents
        agents = list_agents()
        names = [a.name for a in agents]
        assert "file_analyst" in names
        assert "shell_runner" in names
        assert "writer" in names
        assert "researcher" in names
        assert "planner" in names
        assert "code_reviewer" in names
        assert "test_writer" in names
        assert "doc_writer" in names
        assert "refactorer" in names
        assert "debugger" in names
        assert "architect" in names

    def test_register_new_agent(self):
        from core.agent_registry import register_agent, get_agent_spec, AgentSpec
        spec = AgentSpec(name="my_agent", description="My custom agent")
        register_agent(spec)

        found = get_agent_spec("my_agent")
        assert found is not None
        assert found.name == "my_agent"
        assert found.description == "My custom agent"

        # Cleanup
        from core.agent_registry import _REGISTRY
        _REGISTRY.pop("my_agent", None)

    def test_get_unknown_agent_returns_none(self):
        from core.agent_registry import get_agent_spec
        result = get_agent_spec("nonexistent_agent")
        assert result is None

    def test_list_agents_count(self):
        from core.agent_registry import list_agents
        agents = list_agents()
        # At least 11 built-in agents
        assert len(agents) >= 11


class TestBuildAgent:
    def test_build_known_agent(self):
        from core.agent_registry import build_agent
        from core.config import Config
        config = Config()
        agent = build_agent("file_analyst", config)
        assert agent is not None
        assert agent.max_iterations == 20
        # System prompt should be set from spec
        assert "read-only" in agent.messages[0]["content"].lower() or "analyst" in agent.messages[0]["content"].lower()

    def test_build_unknown_agent_falls_back(self):
        from core.agent_registry import build_agent
        from core.config import Config
        config = Config()
        agent = build_agent("nonexistent", config)
        # Should fall back to generic agent
        assert agent is not None
        assert agent.max_iterations == 30  # default

    def test_build_agent_filters_tools(self):
        from core.agent_registry import build_agent
        from core.config import Config
        config = Config()
        agent = build_agent("shell_runner", config)
        # shell_runner only has: execute_command, read_file, write_file
        tool_names = [t["function"]["name"] for t in agent.tools_schema]
        assert "execute_command" in tool_names
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        # Should NOT have tools not in the whitelist
        assert "grep" not in tool_names
        assert "glob_search" not in tool_names

    def test_build_agent_without_tool_filter(self):
        from core.agent_registry import build_agent
        from core.config import Config
        config = Config()
        # researcher has tools defined, but let's test with one that has empty tool_names
        # file_analyst has tool_names, but let's verify it only has those tools
        agent = build_agent("file_analyst", config)
        tool_names = [t["function"]["name"] for t in agent.tools_schema]
        # file_analyst: read_file, list_directory, glob_search, grep
        assert "read_file" in tool_names
        assert "list_directory" in tool_names
        assert "glob_search" in tool_names
        assert "grep" in tool_names
        # Should not have write_file or execute_command
        assert "write_file" not in tool_names
        assert "execute_command" not in tool_names


class TestBuiltinAgentSpecs:
    def test_file_analyst_spec(self):
        from core.agent_registry import get_agent_spec
        spec = get_agent_spec("file_analyst")
        assert spec is not None
        assert "read" in spec.system_prompt.lower()
        assert "read_file" in spec.tool_names
        assert spec.max_iterations == 20

    def test_shell_runner_spec(self):
        from core.agent_registry import get_agent_spec
        spec = get_agent_spec("shell_runner")
        assert spec is not None
        assert "execute_command" in spec.tool_names
        assert "write_file" in spec.tool_names

    def test_writer_spec(self):
        from core.agent_registry import get_agent_spec
        spec = get_agent_spec("writer")
        assert spec is not None
        assert "write_file" in spec.tool_names
        assert "execute_command" not in spec.tool_names

    def test_researcher_spec(self):
        from core.agent_registry import get_agent_spec
        spec = get_agent_spec("researcher")
        assert spec is not None
        assert "fetch_webpage" in spec.tool_names
        assert "write_file" not in spec.tool_names

    def test_planner_spec(self):
        from core.agent_registry import get_agent_spec
        spec = get_agent_spec("planner")
        assert spec is not None
        assert spec.max_iterations == 10

    def test_code_reviewer_spec(self):
        from core.agent_registry import get_agent_spec
        spec = get_agent_spec("code_reviewer")
        assert spec is not None
        assert "run_python" in spec.tool_names

    def test_test_writer_spec(self):
        from core.agent_registry import get_agent_spec
        spec = get_agent_spec("test_writer")
        assert spec is not None
        assert "write_file" in spec.tool_names
        assert "execute_command" in spec.tool_names
        assert "pytest" in spec.system_prompt.lower()

    def test_doc_writer_spec(self):
        from core.agent_registry import get_agent_spec
        spec = get_agent_spec("doc_writer")
        assert spec is not None
        assert "write_file" in spec.tool_names
        assert "documentation" in spec.system_prompt.lower()

    def test_refactorer_spec(self):
        from core.agent_registry import get_agent_spec
        spec = get_agent_spec("refactorer")
        assert spec is not None
        assert "search_replace" in spec.tool_names
        assert "run_python" in spec.tool_names

    def test_debugger_spec(self):
        from core.agent_registry import get_agent_spec
        spec = get_agent_spec("debugger")
        assert spec is not None
        assert "execute_command" in spec.tool_names
        assert "run_python" in spec.tool_names

    def test_architect_spec(self):
        from core.agent_registry import get_agent_spec
        spec = get_agent_spec("architect")
        assert spec is not None
        assert "fetch_webpage" in spec.tool_names
        assert "write_file" not in spec.tool_names
