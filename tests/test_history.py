from pathlib import Path
import pytest
from playwright_report_mcp.analysis.test_history import analyze_test_history
from playwright_report_mcp.history.loader import load_history

HISTORY_DIR = Path(__file__).parent / "fixtures" / "history"

CHECKOUT = "checkout.spec.ts > TC-C01: proceeds to payment"
CART = "cart.spec.ts > TC-R02: shows the item count"


def history(test_id: str = CHECKOUT, **kwargs):
    return analyze_test_history(test_id, HISTORY_DIR, **kwargs)


def test_history_loads_every_test_of_every_run():
    """Five runs of three tests, whether they passed or failed."""

    results = load_history(HISTORY_DIR)

    assert len(results) == 15
    assert {result.run_id for result in results} == {
        "run-001", "run-002", "run-003", "run-004", "run-005",
    }


def test_history_keeps_the_runs_in_order():
    runs = history().runs

    assert [run.run_id for run in runs] == [
        "run-001", "run-002", "run-003", "run-004", "run-005",
    ]


def test_history_counts_how_often_a_test_failed():
    summary = history()

    assert summary.total_runs == 5
    assert summary.passed == 3
    assert summary.failed == 2
    assert summary.skipped == 0
    assert summary.failure_rate == pytest.approx(0.4)


def test_a_skipped_run_counts_as_neither_pass_nor_failure():
    summary = history(CART)

    assert (summary.passed, summary.failed, summary.skipped) == (4, 0, 1)
    assert summary.failure_rate == 0.0


def test_history_says_what_each_failure_looked_like():
    """Two failures, two patterns -- so this test is not failing one way.

    The timeout reads as "locator-not-found": it timed out waiting for a
    locator, and the locator is the better description of it.
    """

    failures = [run for run in history().runs if run.status == "failed"]

    assert [run.failure_pattern for run in failures] == [
        "locator-not-found",
        "assertion-failure",
    ]
    assert failures[0].run_id == "run-003"


def test_passing_runs_carry_no_failure_pattern():
    passes = [run for run in history().runs if run.status == "passed"]

    assert all(run.failure_pattern is None for run in passes)


def test_a_failure_keeps_its_evidence():
    failure = history().runs[2]

    assert failure.started_at == "2026-09-03T09:00:00.000Z"
    assert failure.timed_out is True
    assert failure.trace_path == "test-results/run-003/trace.zip"
    assert "TimeoutError" in failure.error


def test_history_can_be_narrowed_to_one_project():
    assert history(project="chromium").total_runs == 5
    assert history(project="firefox").total_runs == 0


def test_an_unknown_test_has_an_empty_history():
    summary = history("nowhere.spec.ts > never ran")

    assert summary.total_runs == 0
    assert summary.failure_rate == 0.0
    assert summary.runs == []


def test_a_missing_history_directory_says_so():
    with pytest.raises(FileNotFoundError):
        load_history(HISTORY_DIR / "does-not-exist")
