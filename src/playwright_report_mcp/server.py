from mcp.server import MCPServer
import os
from pathlib import Path
from playwright_report_mcp.analysis.failure_patterns import analyze_failure_patterns
from playwright_report_mcp.analysis.test_history import analyze_test_history
from playwright_report_mcp.models.history import TestHistory
from playwright_report_mcp.models.test_summary import TestSummary
from playwright_report_mcp.playwright_report import PlaywrightReport

mcp = MCPServer("Playwright Report")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Where past runs are kept: one Playwright JSON report per run, named
# run-001.json, run-002.json, ... Copied there after a run, or generated.
DEFAULT_HISTORY_DIR = PROJECT_ROOT / "data" / "history"


def resolve_path(path: str) -> Path:
    """Read a configured path, relative ones counting from the project root.

    The paths come from .mcp.json, which is shared, so they should not be
    tied to one machine -- nor to the directory Claude Code happened to be
    started in.
    """

    configured = Path(path).expanduser()
    return configured if configured.is_absolute() else PROJECT_ROOT / configured

def get_report_path() -> Path:
    path = os.getenv("REPORT_PATH")
    if not path:
        raise RuntimeError("REPORT_PATH is not set -- configure it in .mcp.json.")
    return resolve_path(path)

def get_history_dir() -> Path:
    """Return the history directory, overridable for a different checkout."""

    path = os.getenv("HISTORY_DIR")
    return resolve_path(path) if path else DEFAULT_HISTORY_DIR

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

@mcp.tool()
def get_failure_patterns() -> list[dict]:
    """Analyze failures and group them into known failure patterns."""

    report = PlaywrightReport(get_report_path())
    results = report.get_failure_evidence()

    return analyze_failure_patterns(results)

@mcp.tool()
def get_test_history(test_id: str, project: str | None = None) -> TestHistory:
    """Return how one test has done across past runs: how often it failed, and how.

    The test_id is the one reported by the other tools, e.g.
    "checkout.spec.ts > TC-C01: proceeds to payment". Results from every
    project are counted unless one is named.
    """

    return analyze_test_history(
        test_id=test_id,
        history_dir=get_history_dir(),
        project=project,
    )
