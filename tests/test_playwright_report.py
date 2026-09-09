from pathlib import Path
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

    assert set(failures[0]) == {"test_id", "title", "file", "status", "error"}


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
