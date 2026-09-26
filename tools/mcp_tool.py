import asyncio
from typing import Any
from pydantic import create_model, Field
from tools.base import Tool
from core.mcp_client import get_mcp_manager

class MCPToolWrapper(Tool):
    """Wraps an MCP tool as a Chronos Tool."""
    def __init__(self, server_name: str, mcp_tool_info):
        self.server_name = server_name
        self.mcp_tool_name = mcp_tool_info.name
        
        # Convert JSON schema properties to dynamic Pydantic BaseModel
        schema = mcp_tool_info.inputSchema
        fields = {}
        if "properties" in schema:
            for k, v in schema["properties"].items():
                is_req = "required" in schema and k in schema["required"]
                fields[k] = (Any, Field(... if is_req else None, description=v.get("description", "")))
                    
        DynamicSchema = create_model(f'MCP{self.mcp_tool_name}Schema', **fields)
        tool_name = f"mcp_{server_name}_{self.mcp_tool_name}"
        
        super().__init__(
            name=tool_name,
            description=mcp_tool_info.description or f"MCP tool: {self.mcp_tool_name}",
            input_schema=DynamicSchema,
            requires_permission=True
        )

    def execute(self, **kwargs) -> str:
        manager = get_mcp_manager()
        
        # We need an event loop to call the async tool
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            # If we are already inside a running event loop (e.g. from an async web framework)
            import nest_asyncio
            nest_asyncio.apply()
            
        return loop.run_until_complete(manager.call_tool(self.server_name, self.mcp_tool_name, kwargs))
