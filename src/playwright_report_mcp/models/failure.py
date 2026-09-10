from playwright_report_mcp.models.test_result import TestResult


class FailureEvidence(TestResult):
    """Everything the report tells us about one failed test.

    A `TestResult` plus the context of the run it failed in (workers,
    parallelism, CI), because a failure often only makes sense against the run
    it happened in.
    """

    workers: int = 1
    fully_parallel: bool = False
    ci: bool = False
