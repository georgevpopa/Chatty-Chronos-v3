"""Human-in-the-loop tools — allowing the agent to ask the user for help or decisions."""
from pydantic import BaseModel, Field
from tools.base import Tool
from core.permissions import ask_user_prompt

class AskUserSchema(BaseModel):
    question: str = Field(..., description="The specific question to ask the user.")

class AskUser(Tool):
    def __init__(self):
        super().__init__(
            name="ask_user",
            description=(
                "Pause execution and ask the human user a free-text question. "
                "Use this when you are stuck, need a password, need a design decision, "
                "or require clarification before proceeding. Do not overuse this."
            ),
            input_schema=AskUserSchema,
            requires_permission=False,
        )

    def execute(self, question: str, **kwargs) -> str:
        answer = ask_user_prompt(question)
        if not answer:
            return "User provided no answer."
        return f"User replied: {answer}"
