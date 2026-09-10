from mcp.server import MCPServer
import os
from pathlib import Path
from playwright_report_mcp.analysis.failure_patterns import analyze_failure_patterns
from playwright_report_mcp.analysis.test_history import (
    analyze_test_history,
    rank_unstable_tests,
)
from playwright_report_mcp.models.history import TestHistory, TestStability
from playwright_report_mcp.models.test_summary import TestSummary
from playwright_report_mcp.playwright_report import PlaywrightReport

mcp = MCPServer("Playwright Report")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Where past runs are kept: one Playwright JSON report per run, named
# run-001.json, run-002.json, ... Copied there after a run, or generated.
DEFAULT_HISTORY_DIR = PROJECT_ROOT / "data" / "history"

# The report of the latest run. Defaulted, like the history directory, so the
# server answers on every launch path rather than only the configured one: the
# MCP Inspector spawns servers with a fixed set of environment variables
# (HOME, LOGNAME, PATH, SHELL, TERM, USER) and drops the rest, so REPORT_PATH
# cannot reach the process there however it is exported.
DEFAULT_REPORT_PATH = PROJECT_ROOT / "src" / "playwright_report_mcp" / "results.json"


def resolve_path(path: str) -> Path:
    """Read a configured path, relative ones counting from the project root.

    The paths come from .mcp.json, which is shared, so they should not be
    tied to one machine -- nor to the directory Claude Code happened to be
    started in.
    """

    configured = Path(path).expanduser()
    return configured if configured.is_absolute() else PROJECT_ROOT / configured

def get_report_path() -> Path:
    """Return the report to read, falling back to the bundled sample run."""

    path = os.getenv("REPORT_PATH")
    return resolve_path(path) if path else DEFAULT_REPORT_PATH

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
    """Return the tests that failed in the latest Playwright test run.

    Includes flaky tests, which failed and then passed on a retry; `status`
    says which is which.
    """

    report = PlaywrightReport(get_report_path())
    failures = report.get_failed_tests()
    return failures

@mcp.tool()
def get_failure_patterns() -> list[dict]:
    """Analyze failures and group them into known failure patterns.

    Flaky tests are analyzed too: the error a test failed with before it
    passed is the same kind of evidence as one it never recovered from.
    """

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


@mcp.tool()
def get_unstable_tests(limit: int = 10, project: str | None = None) -> list[TestStability]:
    """Return the tests that most often fail or flake across past runs.

    Where an investigation starts: every other tool needs a `test_id` you
    already know, so this is what finds one -- including for a test that is
    failing half the time but happened to pass in the latest run.

    One entry per test per project, worst first, each with how often it failed
    or flaked, what its errors looked like, and how it did most recently.
    Feed a `test_id` from here into `get_test_history` for the run-by-run
    detail. Tests that have never failed are not listed.
    """

    return rank_unstable_tests(
        history_dir=get_history_dir(),
        limit=limit,
        project=project,
    )
