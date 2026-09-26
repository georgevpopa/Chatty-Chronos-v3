"""Sub-agent delegator — spawns child agents for parallel subtasks.

When `agent_type` is provided, the Agent Registry is consulted and a
specialised agent (with a focused system prompt and tool whitelist) is
instantiated instead of the generic ReActAgent.
"""
from typing import Optional
from rich.console import Console
from core.config import Config

console = Console()

MAX_DEPTH = 2


def delegate_task(
    task: str,
    config: Config,
    depth: int = 0,
    max_iterations: int = 10,
    agent_type: Optional[str] = None,
) -> str:
    """Spawn a child agent to handle a subtask.

    Args:
        task:           The subtask description
        config:         Config instance
        depth:          Current delegation depth (prevents infinite recursion)
        max_iterations: Max steps for child agent (used only if agent_type is None)
        agent_type:     Optional name of a registered specialised agent type.
                        If None or not found, falls back to the generic ReActAgent.

    Returns:
        Result text from the child agent
    """
    if depth >= MAX_DEPTH:
        return "Error: Maximum delegation depth reached. Cannot delegate further."

    from core.agent_registry import build_agent, get_agent_spec

    if agent_type:
        spec = get_agent_spec(agent_type)
        label = f"[{agent_type}]" if spec else f"[{agent_type} — unknown, using generic]"
    else:
        label = "[generic]"

    console.print(f"  [cyan]Delegating subtask {label} (depth {depth + 1})...[/cyan]")
    console.print(f"  [dim]{task[:80]}{'...' if len(task) > 80 else ''}[/dim]")

    agent = build_agent(agent_type or "", config, depth=depth + 1)
    result = agent.run(task)
    return result
