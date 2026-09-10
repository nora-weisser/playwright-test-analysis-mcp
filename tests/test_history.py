import json
from pathlib import Path
import pytest
from playwright_report_mcp.analysis.test_history import (
    analyze_test_history,
    rank_unstable_tests,
)
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


# --- ranking the unstable tests -------------------------------------------

def write_run(directory: Path, name: str, tests: list[tuple]) -> None:
    """Write one minimal report, each test given as (file, title, status, error).

    Only the fields the loader reads -- enough to rank a run without carrying
    a full Playwright report per case.
    """

    status_names = {"passed": "expected", "failed": "unexpected"}
    suites = []

    for file, title, status, error in tests:
        attempt = {
            "status": "passed" if status == "passed" else "failed",
            "duration": 100.0,
            "retry": 0,
            "attachments": [],
            "errors": [{"message": error}] if error else [],
        }
        # A flake is a failure followed by a passing retry.
        attempts = [attempt] + (
            [{"status": "passed", "duration": 50.0, "retry": 1,
              "attachments": [], "errors": []}]
            if status == "flaky" else []
        )
        suites.append({
            "title": file,
            "file": file,
            "specs": [{
                "title": title,
                "file": file,
                "tests": [{
                    "timeout": 30000,
                    "projectName": "chromium",
                    "status": status_names.get(status, status),
                    "results": attempts,
                }],
            }],
        })

    (directory / name).write_text(json.dumps({
        "config": {"workers": 1, "metadata": {}},
        "suites": suites,
        "errors": [],
        "stats": {
            "startTime": "2026-09-01T09:00:00.000Z", "duration": 1000.0,
            "expected": 0, "skipped": 0, "unexpected": 0, "flaky": 0,
        },
    }))


@pytest.fixture
def unstable_history(tmp_path):
    """Four runs of four tests, each failing at a different rate."""

    boom = "Error: expect(received).toBeVisible()\n  - waiting for locator('.x')\n"
    for index, statuses in enumerate([
        # always,  often,   flaky,   never
        ("failed", "failed", "flaky", "passed"),
        ("failed", "passed", "flaky", "passed"),
        ("failed", "failed", "passed", "passed"),
        ("failed", "passed", "passed", "passed"),
    ], start=1):
        write_run(tmp_path, f"run-00{index}.json", [
            ("a.spec.ts", "always fails", statuses[0], boom if statuses[0] != "passed" else None),
            ("b.spec.ts", "often fails", statuses[1], boom if statuses[1] != "passed" else None),
            ("c.spec.ts", "flakes", statuses[2], boom if statuses[2] != "passed" else None),
            ("d.spec.ts", "always passes", statuses[3], None),
        ])
    return tmp_path


def test_unstable_tests_are_ranked_worst_first(unstable_history):
    ranked = rank_unstable_tests(unstable_history)

    assert [test.test_id for test in ranked] == [
        "a.spec.ts > always fails",
        "b.spec.ts > often fails",
        "c.spec.ts > flakes",
    ]
    assert [test.instability_rate for test in ranked] == [1.0, 0.5, 0.5]


def test_a_test_that_never_failed_is_not_listed(unstable_history):
    """The majority of tests, and never what anyone is looking for here."""

    ranked = rank_unstable_tests(unstable_history)

    assert "d.spec.ts > always passes" not in {test.test_id for test in ranked}


def test_a_failure_outranks_a_flake_at_the_same_rate(unstable_history):
    """Both are unstable at 0.5; the one that never recovers matters more."""

    ranked = {test.test_id: test for test in rank_unstable_tests(unstable_history)}
    often, flaky = ranked["b.spec.ts > often fails"], ranked["c.spec.ts > flakes"]

    assert often.instability_rate == flaky.instability_rate
    assert (often.failed, often.flaky) == (2, 0)
    assert (flaky.failed, flaky.flaky) == (0, 2)


def test_flakes_count_as_not_passing(unstable_history):
    """A test that only ever passes on a retry is not a healthy test."""

    flaky = next(
        test for test in rank_unstable_tests(unstable_history)
        if test.test_id == "c.spec.ts > flakes"
    )

    assert (flaky.flaky, flaky.passed) == (2, 2)
    assert flaky.instability_rate == pytest.approx(0.5)


def test_ranking_says_how_the_test_did_most_recently(unstable_history):
    """A high rate means something different if the test passed today."""

    ranked = {test.test_id: test for test in rank_unstable_tests(unstable_history)}

    assert ranked["a.spec.ts > always fails"].last_status == "failed"
    assert ranked["b.spec.ts > often fails"].last_status == "passed"


def test_ranking_carries_the_failure_patterns(unstable_history):
    always = rank_unstable_tests(unstable_history)[0]

    assert always.failure_patterns == ["locator-not-found"]


def test_the_ranking_can_be_limited(unstable_history):
    assert len(rank_unstable_tests(unstable_history, limit=2)) == 2


def test_the_ranking_can_be_narrowed_to_one_project(unstable_history):
    assert rank_unstable_tests(unstable_history, project="chromium")
    assert rank_unstable_tests(unstable_history, project="firefox") == []


def test_ranking_counts_each_project_separately():
    """A test solid on one browser and broken on another is not one average."""

    ranked = rank_unstable_tests(HISTORY_DIR)

    assert [(test.test_id, test.project, test.total_runs) for test in ranked] == [
        (CHECKOUT, "chromium", 5),
    ]
