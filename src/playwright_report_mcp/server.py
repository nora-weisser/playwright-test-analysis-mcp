from mcp.server import MCPServer
import os
from pathlib import Path
from dotenv import load_dotenv
from playwright_report_mcp.models.test_summary import TestSummary
from playwright_report_mcp.playwright_report import PlaywrightReport

load_dotenv()

mcp = MCPServer("Playwright Report")

def get_report_path() -> Path:
    path = os.getenv("REPORT_PATH")
    if not path:
        raise RuntimeError("REPORT_PATH environment variable is not set.")
    return Path(path)

@mcp.tool()
def get_test_summary() -> TestSummary:
    """Return summary of the latest Playwright test run."""

    report = PlaywrightReport(get_report_path())
    summary = report.get_summary()
    return summary

@mcp.tool()
def get_failures() -> list[dict]:
    """Return failed tests of the latest Playwright test run."""

    report = PlaywrightReport(get_report_path())
    failures = report.get_failed_tests()
    return failures
