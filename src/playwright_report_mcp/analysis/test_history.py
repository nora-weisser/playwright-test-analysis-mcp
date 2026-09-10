from collections import Counter, defaultdict
from pathlib import Path
from playwright_report_mcp.history.loader import load_history
from playwright_report_mcp.models.history import (
    TestHistory,
    TestRunResult,
    TestStability,
)


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


def rank_unstable_tests(
    history_dir: Path,
    limit: int = 10,
    project: str | None = None,
) -> list[TestStability]:
    """Return the tests that most often fail or flake, worst first.

    This is where an investigation starts: `get_test_history` needs a
    `test_id`, and until now the only source of those was the latest run's
    failures -- so a test that fails half the time but happened to pass today
    could not be asked about at all.

    Tests that have never failed or flaked are left out. They are the
    majority, they are not what anyone is looking for here, and listing them
    would bury the few that matter.
    """

    results = load_history(history_dir)

    if project is not None:
        results = [result for result in results if result.project == project]

    grouped: dict[tuple[str, str | None], list[TestRunResult]] = defaultdict(list)
    for result in results:
        grouped[(result.test_id, result.project)].append(result)

    ranked = []

    for (test_id, test_project), runs in grouped.items():
        counts = Counter(result.status for result in runs)
        unstable = counts["failed"] + counts["flaky"]

        if not unstable:
            continue

        ranked.append(TestStability(
            test_id=test_id,
            project=test_project,
            total_runs=len(runs),
            passed=counts["passed"],
            failed=counts["failed"],
            flaky=counts["flaky"],
            skipped=counts["skipped"],
            instability_rate=unstable / len(runs),
            # load_history returns the runs oldest first, so this is the most
            # recent -- it answers "is it still broken?", which decides
            # whether the rate above is history or a live problem.
            last_status=runs[-1].status,
            failure_patterns=sorted(
                {run.failure_pattern for run in runs if run.failure_pattern}
            ),
        ))

    # Worst first, then by outright failures, so a test that never recovers
    # outranks one that flakes at the same rate. The id breaks ties, so the
    # order does not wander between calls.
    ranked.sort(key=lambda test: (-test.instability_rate, -test.failed, test.test_id))

    return ranked[:limit]
