"""System integration check — verifies all modules load and system status."""
import pytest


class TestSystemIntegration:
    def test_all_core_imports(self):
        import core.config
        import core.state
        import core.agent
        import core.chat
        import core.session
        import core.memory
        import core.permissions
        import core.context
        import core.telemetry
        import core.team
        import core.delegator
        import core.agent_registry
        import core.repl_daemon
        import core.logger

    def test_all_llm_imports(self):
        from llm import ollama_provider, llamacpp_provider, openai_provider
        from llm.fallback import get_available_providers, chat_with_fallback
        from llm.server_manager import is_available, start_local_server, stop_local_server, get_system_telemetry
        from llm.rate_limit import RateLimitRotator, PROVIDERS

    def test_all_tool_imports(self):
        from tools.registry import get_all_tools, register_tool
        from tools.base import Tool
        from tools.filesystem import ReadFile, WriteFile, SearchReplace, ListDirectory, GlobSearch, Grep
        from tools.shell import ExecuteCommand
        from tools.web import FetchWebpage
        from tools.memory_tools import StoreMemory, SearchMemory
        from tools.human import AskUser

    def test_all_rag_imports(self):
        from rag.indexer import index_directory, collect_files
        from rag.retriever import get_rag_context
        from rag.embeddings import ChronosEmbeddingFunction

    def test_all_plugin_imports(self):
        from plugins.base import Plugin
        from plugins.loader import load_plugins, get_loaded_plugins, reload_plugins

    def test_tools_registry(self):
        from tools.registry import get_all_tools
        tools = get_all_tools()
        assert len(tools) >= 10
        tool_names = [t.name for t in tools]
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "execute_command" in tool_names
        assert "glob_search" in tool_names
        assert "grep" in tool_names

    def test_providers_list(self):
        from llm.fallback import get_available_providers
        providers = get_available_providers()
        assert len(providers) >= 5
        names = [p["name"] for p in providers]
        assert "ollama" in names

    def test_rate_limit_rotator(self):
        from llm.rate_limit import RateLimitRotator, PROVIDERS
        rotator = RateLimitRotator()
        assert len(rotator._providers) == len(PROVIDERS)

    def test_agent_registry(self):
        from core.agent_registry import list_agents
        agents = list_agents()
        assert len(agents) >= 8
        names = [a.name for a in agents]
        assert "test_writer" in names
        assert "file_analyst" in names

    def test_config_loads(self):
        from core.config import Config
        config = Config()
        assert config.get("provider") is not None

    def test_telemetry(self):
        from llm.server_manager import get_system_telemetry
        t = get_system_telemetry()
        assert "ram_total" in t
        assert "platform" in t
        assert t["platform"] in ("win32", "linux", "darwin")

    def test_spec_generator_imports(self):
        from spec.generator import create_spec, list_specs

    def test_web_ui_imports(self):
        from ui.web import get_workspace_tree, ChronosWebHandler

    def test_chat_module(self):
        from core.chat import send_message
        assert callable(send_message)

    def test_session_module(self):
        from core.session import save_session, load_session, list_sessions
        assert callable(save_session)
        assert callable(load_session)
        assert callable(list_sessions)

    def test_memory_module(self):
        from core.memory import init_memory, store_memory, search_memory
        assert callable(init_memory)
        assert callable(store_memory)
        assert callable(search_memory)

    def test_permissions_module(self):
        from core.permissions import request_permission, reset_session_trust
        assert callable(request_permission)
        assert callable(reset_session_trust)

    def test_delegator_module(self):
        from core.delegator import delegate_task
        assert callable(delegate_task)

    def test_team_module(self):
        from core.team import run_team_workflow
        assert callable(run_team_workflow)
