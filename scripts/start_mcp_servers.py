# scripts/start_mcp_servers.py
"""
Start MCP servers for financial data and document search.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    print("Starting MCP Servers...")
    print("=" * 50)

    # Start financial data server
    print("\n📊 Starting Financial Data MCP Server...")
    print("   Command: python -m src.mcp.financial_data_server")

    # Start document search server
    print("\n📄 Starting Document Search MCP Server...")
    print("   Command: python -m src.mcp.document_search_server")

    print("\n" + "=" * 50)
    print("To start servers individually, run:")
    print("  python -m src.mcp.financial_data_server")
    print("  python -m src.mcp.document_search_server")
    print("\nNote: MCP servers use stdio transport by default.")
    print("They can be connected to Claude Desktop or other MCP clients.")


if __name__ == "__main__":
    main()