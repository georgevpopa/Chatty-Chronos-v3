import asyncio
import sys
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClientManager:
    """Manages connections to multiple MCP servers."""
    def __init__(self):
        self.servers = {}
        self._exit_stack = AsyncExitStack()

    async def connect(self, server_name: str, command: str, args: list[str], env: dict = None):
        if server_name in self.servers:
            return True
            
        server_parameters = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        
        try:
            # We connect to stdio using context managers.
            transport_ctx = stdio_client(server_parameters)
            read, write = await self._exit_stack.enter_async_context(transport_ctx)
            
            session = ClientSession(read, write)
            await self._exit_stack.enter_async_context(session)
            
            await session.initialize()
            
            # Fetch tools
            tools_response = await session.list_tools()
            tools = tools_response.tools
            
            self.servers[server_name] = {
                "session": session,
                "tools": tools,
                "command": command
            }
            return True
        except Exception as e:
            print(f"Failed to connect to MCP server '{server_name}': {e}", file=sys.stderr)
            return False

    def get_server_tools(self, server_name: str):
        if server_name not in self.servers:
            return []
        return self.servers[server_name]["tools"]

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict):
        if server_name not in self.servers:
            return f"Error: Server '{server_name}' not found."
            
        session = self.servers[server_name]["session"]
        try:
            result = await session.call_tool(tool_name, arguments)
            if not result.content:
                return "Tool executed successfully (no output)."
            
            # Extract text from content blocks
            texts = []
            for block in result.content:
                if block.type == "text":
                    texts.append(block.text)
                else:
                    texts.append(str(block))
            return "\n".join(texts)
        except Exception as e:
            return f"Error calling tool '{tool_name}': {e}"

    async def close_all(self):
        self.servers.clear()
        await self._exit_stack.aclose()


# Global manager instance
_manager = None
def get_mcp_manager():
    global _manager
    if _manager is None:
        _manager = MCPClientManager()
    return _manager
