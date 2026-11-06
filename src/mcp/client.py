"""MCP client configuration for tools used by the research workflow."""
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool


def create_mcp_client() -> MultiServerMCPClient:
    """Create clients for this project's financial and document MCP servers."""
    return MultiServerMCPClient({
        "financial_data": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "src.mcp.financial_data_server"],
        },
        "document_search": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "src.mcp.document_search_server"],
        },
    })


async def get_mcp_tools() -> list[BaseTool]:
    """Discover tools exposed by the configured MCP servers."""
    return await create_mcp_client().get_tools()
