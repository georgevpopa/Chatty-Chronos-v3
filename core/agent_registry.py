"""Agent Registry — register and instantiate specialized agents.

This module allows external code (plugins, extensions, or Chronos itself) to
register specialized agent *types* that the DelegateSubtask tool can then
instantiate by name, giving each sub-agent a focused tool-set and system prompt.

Usage — registering an agent type (e.g., from a plugin):

    from core.agent_registry import register_agent, AgentSpec
    from tools.filesystem import ReadFile, GlobSearch

    register_agent(AgentSpec(
        name        = "code_reviewer",
        description = "Reviews code for bugs, style and security issues.",
        system_prompt = (
            "You are an expert code reviewer. Analyse the code you are given "
            "and provide actionable, specific feedback. Be concise."
        ),
        tool_names  = ["read_file", "glob_search", "grep"],
        max_iterations = 15,
    ))

Usage — delegating to a named agent type:

    /agent Review all Python files in src/ for security issues
    → DelegateSubtask(task=..., agent_type="code_reviewer")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from rich.console import Console

console = Console()

# ─── AgentSpec ───────────────────────────────────────────────────────────────

@dataclass
class AgentSpec:
    """Specification for a named, specialized agent type."""

    name: str
    """Unique identifier used when delegating (e.g. 'code_reviewer')."""

    description: str
    """Human-readable description shown in /agents command."""

    system_prompt: str = ""
    """Custom system prompt for this agent. If empty, the default ReAct prompt is used."""

    tool_names: list[str] = field(default_factory=list)
    """
    Whitelist of tool names this agent can use.
    Empty list means the agent inherits ALL tools (same as the base ReActAgent).
    """

    max_iterations: int = 20
    """Maximum ReAct loop iterations for this agent type."""

    version: str = "1.0.0"


# ─── Registry store ──────────────────────────────────────────────────────────

_REGISTRY: dict[str, AgentSpec] = {}

# Pre-register a set of useful built-in specialized agent types
_BUILTIN_AGENTS: list[AgentSpec] = [
    AgentSpec(
        name        = "file_analyst",
        description = "Read-only agent for analysing codebases, counting lines, and summarising files.",
        system_prompt = (
            "You are a meticulous code analyst. You ONLY read files — never write or execute anything. "
            "Provide thorough, structured summaries. Use bullet points and markdown."
        ),
        tool_names     = ["read_file", "list_directory", "glob_search", "grep"],
        max_iterations = 20,
    ),
    AgentSpec(
        name        = "shell_runner",
        description = "Execution-focused agent that runs shell commands and captures output.",
        system_prompt = (
            "You are a DevOps automation agent. Execute shell commands methodically, "
            "capture output, and report results clearly. Always verify commands before running."
        ),
        tool_names     = ["execute_command", "read_file", "write_file"],
        max_iterations = 15,
    ),
    AgentSpec(
        name        = "writer",
        description = "Write-only agent for generating, editing, and saving files.",
        system_prompt = (
            "You are a precise technical writer and code generator. "
            "You create and edit files based on specifications. "
            "Never execute commands — only read existing files for context and write new ones."
        ),
        tool_names     = ["read_file", "write_file", "search_replace"],
        max_iterations = 20,
    ),
    AgentSpec(
        name        = "researcher",
        description = "Agent that searches and summarises project knowledge without modifying anything.",
        system_prompt = (
            "You are a research agent. Your job is to gather information from the codebase, "
            "understand patterns, and produce a clear written summary. Do NOT modify any files."
        ),
        tool_names     = ["read_file", "list_directory", "glob_search", "grep", "fetch_webpage"],
        max_iterations = 25,
    ),
    AgentSpec(
        name        = "planner",
        description = "Creates step-by-step implementation plans for complex features.",
        system_prompt = (
            "You are a Lead Software Architect. Break down the given feature into a detailed, "
            "step-by-step implementation plan. Define files to be created and functions to be written. "
            "Do NOT write the code yourself. Only return the plan in markdown format."
        ),
        tool_names     = ["read_file", "list_directory", "glob_search", "grep"],
        max_iterations = 10,
    ),
    AgentSpec(
        name        = "code_reviewer",
        description = "Reviews code for bugs, logic errors, and style issues.",
        system_prompt = (
            "You are an expert Code Reviewer. Read the specified files or code blocks, "
            "identify bugs, logic errors, and security issues. Provide actionable feedback "
            "and suggest fixes. Do NOT execute or rewrite the entire files."
        ),
        tool_names     = ["read_file", "glob_search", "grep", "run_python"],
        max_iterations = 15,
    ),
    AgentSpec(
        name        = "test_writer",
        description = "Generates unit tests, integration tests, and test fixtures.",
        system_prompt = (
            "You are an expert test engineer. Write comprehensive unit tests using pytest. "
            "Each test should be isolated, use mocks for external dependencies, and follow "
            "the Arrange-Act-Assert pattern. Name tests descriptively. "
            "Read existing code for context before writing tests."
        ),
        tool_names     = ["read_file", "write_file", "search_replace", "glob_search", "grep", "execute_command"],
        max_iterations = 20,
    ),
    AgentSpec(
        name        = "doc_writer",
        description = "Generates API docs, README sections, and technical documentation.",
        system_prompt = (
            "You are a technical documentation specialist. Write clear, concise, and accurate "
            "documentation. Include code examples where helpful. Follow the existing project's "
            "documentation style. Use markdown formatting."
        ),
        tool_names     = ["read_file", "write_file", "search_replace", "glob_search", "grep"],
        max_iterations = 15,
    ),
    AgentSpec(
        name        = "refactorer",
        description = "Refactors code for better structure, readability, and performance.",
        system_prompt = (
            "You are a senior software engineer specializing in refactoring. "
            "Analyze the code, identify code smells, duplication, and complexity. "
            "Apply clean code principles: SRP, DRY, meaningful names, small functions. "
            "Always preserve existing behavior. Read the code first, then make targeted changes."
        ),
        tool_names     = ["read_file", "write_file", "search_replace", "glob_search", "grep", "run_python"],
        max_iterations = 25,
    ),
    AgentSpec(
        name        = "debugger",
        description = "Helps diagnose and fix bugs by analyzing errors and code.",
        system_prompt = (
            "You are an expert debugger. When given an error or a bug report, "
            "systematically analyze the code, reproduce the issue, identify root cause, "
            "and propose a minimal fix. Always verify your fix doesn't break other functionality."
        ),
        tool_names     = ["read_file", "write_file", "search_replace", "grep", "glob_search", "execute_command", "run_python"],
        max_iterations = 20,
    ),
    AgentSpec(
        name        = "architect",
        description = "Designs system architecture and creates technical specifications.",
        system_prompt = (
            "You are a software architect. Analyze requirements, design system architecture, "
            "define interfaces and data flows, and create technical specifications. "
            "Consider scalability, maintainability, and security. Output structured markdown specs."
        ),
        tool_names     = ["read_file", "list_directory", "glob_search", "grep", "fetch_webpage"],
        max_iterations = 20,
    ),
]


def _bootstrap():
    """Register built-in agents on first import."""
    for spec in _BUILTIN_AGENTS:
        _REGISTRY[spec.name] = spec


_bootstrap()


# ─── Public API ──────────────────────────────────────────────────────────────

def register_agent(spec: AgentSpec) -> None:
    """Register a new agent type. Overwrites if name already exists."""
    _REGISTRY[spec.name] = spec
    console.print(f"  [dim]Agent registered: {spec.name}[/dim]")


def get_agent_spec(name: str) -> Optional[AgentSpec]:
    """Look up a registered agent spec by name. Returns None if not found."""
    return _REGISTRY.get(name)


def list_agents() -> list[AgentSpec]:
    """Return all registered agent specs, built-in + external."""
    return list(_REGISTRY.values())


def build_agent(name: str, config, depth: int = 0):
    """Instantiate a ReActAgent wired to the spec identified by *name*.

    If the spec restricts tool_names, only those tools are injected.
    Falls back to the generic ReActAgent if the name is not registered.

    Returns:
        A ReActAgent instance ready to call .run(task).
    """
    from core.agent import ReActAgent
    from tools.registry import get_all_tools

    spec = get_agent_spec(name)
    if spec is None:
        console.print(f"  [yellow]Agent type '{name}' not registered — using generic agent.[/yellow]")
        return ReActAgent(config, depth=depth)

    agent = ReActAgent(config, max_iterations=spec.max_iterations, depth=depth)

    # Override system prompt if spec provides one
    if spec.system_prompt:
        import os
        cwd = os.getcwd()
        agent.messages = [{
            "role": "system",
            "content": spec.system_prompt + f"\n\nWorking directory: {cwd}",
        }]

    # Filter tool schema to the whitelist (if defined)
    if spec.tool_names:
        all_tools   = get_all_tools()
        allowed     = {n for n in spec.tool_names}
        agent.tools_schema = [
            t.to_ollama_schema()
            for t in all_tools
            if t.name in allowed
        ]

    return agent
