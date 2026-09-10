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
