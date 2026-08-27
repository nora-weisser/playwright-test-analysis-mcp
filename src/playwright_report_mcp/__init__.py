def main() -> None:
    """Run the Playwright Report MCP server over stdio."""

    from playwright_report_mcp.server import mcp

    mcp.run()
