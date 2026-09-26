from tools.base import Tool
from core.memory import store_memory, search_memory, init_memory
import json

from pydantic import BaseModel, Field

class StoreMemorySchema(BaseModel):
    key: str = Field(..., description="A short, unique identifier for this memory (e.g. 'user_theme_pref').")
    content: str = Field(..., description="The detailed content to remember.")

class StoreMemory(Tool):
    def __init__(self):
        super().__init__(
            name="store_memory",
            description="Store important information, user preferences, or decisions in the long-term vector memory so you can recall it in future sessions.",
            input_schema=StoreMemorySchema,
            requires_permission=False,
        )
        init_memory()

    def execute(self, key: str, content: str, **kwargs) -> str:
        success = store_memory(key, content)
        if success:
            return f"Successfully stored memory with key '{key}'."
        return "Failed to store memory (ChromaDB might not be installed)."


class SearchMemorySchema(BaseModel):
    query: str = Field(..., description="The concept, question, or keyword to search for.")

class SearchMemory(Tool):
    def __init__(self):
        super().__init__(
            name="search_memory",
            description="Search the long-term vector memory for previously stored information using semantic search.",
            input_schema=SearchMemorySchema,
            requires_permission=False,
        )
        init_memory()

    def execute(self, query: str, **kwargs) -> str:
        results = search_memory(query)
        if not results:
            return "No relevant memories found."
        
        output = ["Found memories:"]
        for i, res in enumerate(results):
            content = res.get('content', '')
            key = res.get('metadata', {}).get('key', 'unknown')
            output.append(f"[{i+1}] (Key: {key}): {content}")
        return "\n".join(output)
