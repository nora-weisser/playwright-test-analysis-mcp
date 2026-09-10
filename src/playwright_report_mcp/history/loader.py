from pathlib import Path
from playwright_report_mcp.analysis.failure_patterns import classify_failure
from playwright_report_mcp.models.history import TestRunResult
from playwright_report_mcp.playwright_report import PlaywrightReport

RUN_GLOB = "run-*.json"


def load_run(path: Path) -> list[TestRunResult]:
    """Read one stored run as history entries.

    The parsing is `PlaywrightReport`'s job -- history only adds which run a
    result came from, and what its error looked like, so that question does
    not have to be re-asked later.
    """

    report = PlaywrightReport(path)
    started_at = report.get_started_at()

    return [
        TestRunResult(
            **result.model_dump(),
            run_id=path.stem,
            started_at=started_at,
            failure_pattern=(
                classify_failure(result.error)
                if result.status in {"failed", "flaky"}
                else None
            ),
        )
        for result in report.get_test_results()
    ]


def load_history(history_dir: Path) -> list[TestRunResult]:
    """Read every stored run, oldest first.

    Runs are named run-001.json, run-002.json, ..., so sorting the filenames
    keeps the history in the order the runs happened. Where the files came
    from -- a real browser or a generated fixture -- makes no difference here.
    """

    if not history_dir.is_dir():
        raise FileNotFoundError(f"History directory not found: {history_dir}")

    history: list[TestRunResult] = []

    for path in sorted(history_dir.glob(RUN_GLOB)):
        history.extend(load_run(path))

    return history
