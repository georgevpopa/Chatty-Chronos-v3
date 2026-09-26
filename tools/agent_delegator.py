"""Agent delegation tool — exposes sub-agent spawning to the LLM.

Supports an optional `agent_type` parameter that lets the LLM pick a
specialised agent (e.g. 'file_analyst', 'shell_runner', 'writer') from
the Agent Registry, each with its own system prompt and tool whitelist.
"""
from tools.base import Tool
from core.config import Config
from core.delegator import delegate_task


from pydantic import BaseModel, Field

class DelegateSubtaskSchema(BaseModel):
    task: str = Field(..., description="Detailed prompt or task description for the sub-agent.")
    agent_type: str = Field(default="", description=(
        "Optional. Name of a registered specialised agent type. "
        "Available: 'file_analyst', 'shell_runner', 'writer', 'researcher'. "
        "Custom agent types registered via core.agent_registry are also accepted."
    ))

class DelegateSubtask(Tool):
    def __init__(self):
        super().__init__(
            name="delegate_subtask",
            description=(
                "Delegate a specific technical subtask to a new autonomous child agent. "
                "Returns the child agent's final response/summary. Useful for parallelizing "
                "or isolating complex subtasks (e.g. compiling, scanning directories, or "
                "writing test files in isolation). "
                "Optionally specify agent_type to use a specialised agent: "
                "'file_analyst' (read-only codebase analysis), "
                "'shell_runner' (command execution), "
                "'writer' (file generation), "
                "'researcher' (project knowledge gathering). "
                "Leave agent_type empty or omit it to use the generic agent."
            ),
            input_schema=DelegateSubtaskSchema,
            requires_permission=True,
        )

    def execute(
        self,
        task: str,
        agent_type: str = "",
        config: Config = None,
        depth: int = 0,
        **kwargs,
    ) -> str:
        if not config:
            config = Config()
        return delegate_task(task, config, depth=depth, agent_type=agent_type or None)
