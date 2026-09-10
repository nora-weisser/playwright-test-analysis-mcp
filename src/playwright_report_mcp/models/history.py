from pydantic import BaseModel
from playwright_report_mcp.models.test_result import TestResult


class TestRunResult(TestResult):
    """One test's result in one stored run.

    Same normalized result as any other, tagged with the run it came from so
    it can be placed on a timeline.
    """

    run_id: str
    started_at: str | None = None
    failure_pattern: str | None = None


class TestHistory(BaseModel):
    """How one test has behaved across the stored runs."""

    test_id: str
    project: str | None = None
    total_runs: int
    passed: int
    failed: int
    skipped: int
    flaky: int
    failure_rate: float
    runs: list[TestRunResult]


class TestStability(BaseModel):
    """How reliably one test has behaved, on one project, across the runs.

    The counting unit is the test *and* the project it ran on: the same spec
    can be solid on chromium and hopeless on firefox, and averaging the two
    describes neither.
    """

    test_id: str
    project: str | None = None
    total_runs: int
    passed: int
    failed: int
    flaky: int
    skipped: int
    # Failures and flakes together, over the runs: "how often did this test
    # not simply pass". A flake is a failure that got a second chance, so
    # leaving it out understates a test that never passes first time.
    instability_rate: float
    last_status: str | None = None
    failure_patterns: list[str] = []
