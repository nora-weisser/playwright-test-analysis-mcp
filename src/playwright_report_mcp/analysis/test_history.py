from collections import Counter
from pathlib import Path
from playwright_report_mcp.history.loader import load_history
from playwright_report_mcp.models.history import TestHistory


def analyze_test_history(
    test_id: str,
    history_dir: Path,
    project: str | None = None,
) -> TestHistory:
    """Summarize how one test has behaved across the stored runs.

    One entry per project the test ran on, so a test running on two browsers
    contributes two results to a single run. Pass `project` to ask about one
    browser instead of all of them.

    An unknown `test_id` is not an error: it comes back as an empty history,
    which is the honest answer when nothing has been recorded under that name.
    """

    runs = [
        result
        for result in load_history(history_dir)
        if result.test_id == test_id
        and (project is None or result.project == project)
    ]

    counts = Counter(result.status for result in runs)
    total = len(runs)
    failed = counts["failed"]

    return TestHistory(
        test_id=test_id,
        project=project,
        total_runs=total,
        passed=counts["passed"],
        failed=failed,
        skipped=counts["skipped"],
        flaky=counts["flaky"],
        failure_rate=failed / total if total else 0.0,
        runs=runs,
    )
