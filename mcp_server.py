"""
MCP Server — Fix #19
=====================
Model Context Protocol server that exposes the agent's ToolRegistry
as MCP-compatible tools. Any MCP client (Claude Desktop, Cursor, etc.)
can connect and use the agent's tools directly.

Usage:
    python mcp_server.py
    # or via gateway /mcp endpoint
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MCPServer")

# Try to import the official MCP SDK
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, CallToolResult
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("[MCP] 'mcp' package not installed. Run: pip install mcp")


class AgentMCPServer:
    """
    Wraps the agent's ToolRegistry as a Model Context Protocol server.
    Supports both stdio transport (for desktop clients) and JSON-RPC over HTTP.
    """

    def __init__(self, tool_registry=None, agent=None):
        self.tool_registry = tool_registry
        self.agent = agent
        self.server_name = "ultimate-ai-agent"
        self.server_version = "1.0.0"

    def get_mcp_tools(self) -> List[Dict]:
        """Export all registered tools as MCP tool descriptors."""
        if not self.tool_registry:
            return []
        tools = []
        for name, meta in self.tool_registry.tools.items():
            tools.append({
                "name": name,
                "description": meta.get("description", f"Tool: {name}"),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        p: {"type": "string", "description": f"Parameter: {p}"}
                        for p in meta.get("params", [])
                    },
                    "required": meta.get("required", []),
                },
            })
        return tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool by name and return its result as a string."""
        if not self.tool_registry:
            return "Error: No tool registry available."
        try:
            result = self.tool_registry.call(name, **arguments)
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            return f"Tool error ({name}): {e}"

    def run_stdio(self):
        """
        Run MCP server over stdio transport (for Claude Desktop / Cursor).
        Add this to your claude_desktop_config.json:
            {
              "mcpServers": {
                "ultimate-agent": {
                  "command": "python",
                  "args": ["mcp_server.py"]
                }
              }
            }
        """
        if not MCP_AVAILABLE:
            print("ERROR: mcp package not installed. Run: pip install mcp")
            return

        server = Server(self.server_name)

        @server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name=t["name"],
                    description=t["description"],
                    inputSchema=t["inputSchema"],
                )
                for t in self.get_mcp_tools()
            ]

        @server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]):
            result_text = await asyncio.to_thread(
                lambda: asyncio.run(self.call_tool(name, arguments))
            )
            return CallToolResult(content=[TextContent(type="text", text=result_text)])

        async def _run():
            async with stdio_server() as (read_stream, write_stream):
                await server.run(read_stream, write_stream,
                                 server.create_initialization_options())

        logger.info(f"[MCP] Starting stdio server: {self.server_name}")
        asyncio.run(_run())

    def get_jsonrpc_manifest(self) -> Dict:
        """Return a JSON manifest for HTTP-based MCP discovery (GET /mcp)."""
        return {
            "name": self.server_name,
            "version": self.server_version,
            "description": "Ultimate AI Agent — MCP tool server",
            "tools": self.get_mcp_tools(),
            "transport": ["stdio", "http"],
        }


# --- Standalone entry point ---
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    try:
        from tool_registry import ToolRegistry
        registry = ToolRegistry()
        registry.register_builtins()
    except ImportError:
        registry = None

    mcp = AgentMCPServer(tool_registry=registry)

    if "--list" in sys.argv:
        tools = mcp.get_mcp_tools()
        print(f"Available MCP tools ({len(tools)}):")
        for t in tools:
            print(f"  • {t['name']}: {t['description'][:60]}")
    else:
        mcp.run_stdio()
