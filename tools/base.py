"""Base tool interface — all tools inherit from this."""
from dataclasses import dataclass, field
from typing import Any, Type, Optional
from pydantic import BaseModel


@dataclass
class Tool:
    name: str
    description: str
    input_schema: Optional[Type[BaseModel]] = None
    requires_permission: bool = True

    def execute(self, **kwargs) -> str:
        raise NotImplementedError

    def get_diff(self, **kwargs) -> Optional[str]:
        """Compute the diff of changes if applicable. Override in subclasses."""
        return None

    def to_ollama_schema(self) -> dict:
        """Convert to Ollama tool call format."""
        schema = self.input_schema.model_json_schema() if self.input_schema else {"type": "object", "properties": {}}
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }
