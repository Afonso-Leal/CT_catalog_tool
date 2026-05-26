"""
MCP Client for Furia - Model Context Protocol integration
"""

import asyncio
import json
from typing import Any, Optional
from dataclasses import dataclass


try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict

    def to_openai_format(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


class MCPClient:
    def __init__(self, server_url: str = "http://127.0.0.1:8000/sse"):
        self.server_url = server_url
        self._session: Optional[ClientSession] = None

    async def connect(self) -> bool:
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP not installed. Install with: pip install mcp")
        try:
            read, write, _ = await streamable_http_client(self.server_url)
            self._session = ClientSession(read, write)
            await self._session.initialize()
            return True
        except Exception as e:
            print(f"Failed to connect to MCP server: {e}")
            return False

    async def disconnect(self):
        if self._session:
            await self._session.close()
            self._session = None

    async def list_tools(self) -> list[MCPTool]:
        if not self._session:
            await self.connect()
        tools_response = await self._session.list_tools()
        return [
            MCPTool(name=t.name, description=t.description, input_schema=t.inputSchema)
            for t in tools_response.tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        if not self._session:
            await self.connect()
        result = await self._session.call_tool(tool_name, arguments=arguments)
        if result.content:
            return (
                result.content[0].text
                if hasattr(result.content[0], "text")
                else str(result.content[0])
            )
        return None


def get_mcp_tools_sync(server_url: str = "http://127.0.0.1:8000/sse") -> list[dict]:
    """Get MCP tools in OpenAI format (synchronous)."""
    if not MCP_AVAILABLE:
        print("Warning: MCP not installed. Install with: pip install mcp")
        return []

    try:
        client = MCPClient(server_url)
        result = asyncio.run(client.connect())
        if result:
            tools = asyncio.run(client.list_tools())
            asyncio.run(client.disconnect())
            return [t.to_openai_format() for t in tools]
    except Exception as e:
        print(f"Error getting MCP tools: {e}")
    return []


def call_mcp_tool_sync(server_url: str, tool_name: str, arguments: dict) -> Any:
    """Call an MCP tool (synchronous)."""
    if not MCP_AVAILABLE:
        raise RuntimeError("MCP not installed. Install with: pip install mcp")

    async def _call():
        client = MCPClient(server_url)
        await client.connect()
        result = await client.call_tool(tool_name, arguments)
        await client.disconnect()
        return result

    return asyncio.run(_call())


if __name__ == "__main__":
    print(f"MCP Available: {MCP_AVAILABLE}")
    if MCP_AVAILABLE:
        tools = get_mcp_tools_sync()
        print(f"Found {len(tools)} tools")
    else:
        print("Install MCP: pip install mcp")
