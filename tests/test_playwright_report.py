from pathlib import Path
import pytest
from playwright_report_mcp.analysis.failure_patterns import analyze_failure_patterns
from playwright_report_mcp.playwright_report import PlaywrightReport, strip_ansi

REPORT_PATH = Path(__file__).parent.parent / "src" / "playwright_report_mcp" / "results.json"


def report() -> PlaywrightReport:
    return PlaywrightReport(REPORT_PATH)


def test_summary_reads_the_run_stats():
    summary = report().get_summary()

    assert summary.passed == 5
    assert summary.failed == 10


def test_failed_tests_are_trimmed_to_the_readable_fields():
    failures = report().get_failed_tests()

    assert set(failures[0]) == {
        "test_id", "title", "file", "project", "status", "error",
    }


def test_the_same_test_failing_on_two_projects_stays_distinguishable():
    """Otherwise the two are identical rows and read as a repeated failure."""

    failures = report().get_failed_tests()
    repeated = [f for f in failures if f["test_id"].startswith("cart.spec.ts > TC-R01")]

    assert len(repeated) == 2
    assert {f["project"] for f in repeated} == {"chromium", "firefox"}


def test_every_failed_test_entry_is_collected():
    """Ten failures across six specs -- one spec fails on two projects."""

    failures = report().get_failure_evidence()

    assert len(failures) == 10
    assert len({failure.test_id for failure in failures}) == 8


def test_evidence_carries_the_run_context():
    evidence = report().get_failure_evidence()[0]

    assert evidence.project == "chromium"
    assert evidence.timed_out is True
    assert evidence.timeout_ms == 30000
    assert evidence.workers == 1
    assert "screenshot" in evidence.attachments


def test_error_messages_have_their_colour_codes_removed():
    evidence = report().get_failure_evidence()[0]

    assert "\x1b[" not in evidence.error


def test_strip_ansi_leaves_plain_text_alone():
    assert strip_ansi("Timeout of 30000ms exceeded.") == "Timeout of 30000ms exceeded."


def test_a_missing_report_names_the_file_it_looked_for(tmp_path):
    """The configured path is the likeliest thing to be wrong, so say which."""

    missing = tmp_path / "nowhere.json"

    with pytest.raises(RuntimeError, match=str(missing)):
        PlaywrightReport(missing).get_summary()


def test_a_truncated_report_is_reported_as_bad_json(tmp_path):
    cut_short = tmp_path / "results.json"
    cut_short.write_text('{"stats": {"star')

    with pytest.raises(RuntimeError, match="not valid JSON"):
        PlaywrightReport(cut_short).get_summary()


def test_json_that_is_not_a_playwright_report_says_so(tmp_path):
    """Previously a bare KeyError: 'stats' with no hint of the cause."""

    wrong_file = tmp_path / "results.json"
    wrong_file.write_text('{"hello": 1}')

    with pytest.raises(RuntimeError, match="not a Playwright JSON report"):
        PlaywrightReport(wrong_file).get_summary()


# A run whose problems are mostly flakes: one outright failure and two tests
# that failed and then passed on a retry. The bundled sample has no flakes.
FLAKY_REPORT_PATH = Path(__file__).parent / "fixtures" / "flaky-run.json"


def flaky_report() -> PlaywrightReport:
    return PlaywrightReport(FLAKY_REPORT_PATH)


def test_flaky_tests_are_reported_alongside_outright_failures():
    """A run whose only problems are flakes still has problems to report."""

    failures = flaky_report().get_failed_tests()
    flaky = [failure for failure in failures if failure["status"] == "flaky"]

    assert len(flaky) == 2
    assert {failure["test_id"] for failure in flaky} == {
        "cart.spec.ts > TC-R01: persists the cart",
        "smoke.spec.ts > TC-S02: a todo can be added",
    }


def test_a_flake_stays_distinguishable_from_a_failure():
    """Both are reported, so `status` is what tells them apart."""

    failures = flaky_report().get_failed_tests()

    assert {failure["status"] for failure in failures} == {"failed", "flaky"}


def test_a_passing_test_is_still_left_out():
    """Widening the filter must not turn this into "every test"."""

    failures = flaky_report().get_failed_tests()

    assert len(failures) == 3
    assert "dashboard.spec.ts > TC-D01: loads widgets" not in {
        failure["test_id"] for failure in failures
    }


def test_a_flakes_error_is_classified_like_any_other():
    """The error a test failed with before passing is evidence like any other."""

    patterns = analyze_failure_patterns(flaky_report().get_failure_evidence())
    pattern_of = {
        failure["test_id"]: entry["pattern"]
        for entry in patterns
        for failure in entry["failures"]
    }

    assert pattern_of["cart.spec.ts > TC-R01: persists the cart"] == "assertion-failure"
    assert pattern_of["smoke.spec.ts > TC-S02: a todo can be added"] == "locator-not-found"


def test_a_run_with_no_flakes_is_unaffected():
    """The bundled sample has none, so its failure list must not change."""

    failures = report().get_failed_tests()

    assert len(failures) == 10
    assert all(failure["status"] == "failed" for failure in failures)
