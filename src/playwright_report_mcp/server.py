from mcp.server import MCPServer
from playwright_report_mcp.analysis.failure_patterns import analyze_failure_patterns
from playwright_report_mcp.analysis.test_history import (
    analyze_test_history,
    rank_unstable_tests,
)
from playwright_report_mcp.config import get_history_dir, get_report_path
from playwright_report_mcp.models.history import TestHistory, TestStability
from playwright_report_mcp.models.test_summary import TestSummary
from playwright_report_mcp.playwright_report import PlaywrightReport

mcp = MCPServer("Playwright Report")

@mcp.tool()
def get_test_summary() -> TestSummary:
    """Return summary of the latest Playwright test run.
    """

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
    """

    return analyze_test_history(
        test_id=test_id,
        history_dir=get_history_dir(),
        project=project,
    )


@mcp.tool()
def get_unstable_tests(limit: int = 10, project: str | None = None) -> list[TestStability]:
    """Return the tests that most often fail or flake across past runs.

    One entry per test per project, worst first, each with how often it failed
    or flaked, what its errors looked like, and how it did most recently.
    """

    return rank_unstable_tests(
        history_dir=get_history_dir(),
        limit=limit,
        project=project,
    )
