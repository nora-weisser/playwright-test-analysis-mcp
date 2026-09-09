from collections import defaultdict
from playwright_report_mcp.models.failure import FailureEvidence

# Checked in order, first hit wins, so the more specific patterns come first:
# "TimeoutError: locator.click: ..." carries both a locator and a timeout, and
# the locator is the better description of it.
PATTERNS = {
    "locator-ambiguous": [
        "strict mode violation",
    ],
    "locator-not-found": [
        "waiting for locator",
        "waiting for getby",
        "element(s) not found",
    ],
    "timing-or-waiting": [
        "timeout",
        "timeouterror",
    ],
    "network-failure": [
        "net::err_",
        "econnrefused",
        "network",
    ],
    "setup-failure": [
        "enoent",
        "no such file or directory",
        "cannot find module",
        "eacces",
    ],
    "assertion-failure": [
        "expected:",
        "received:",
        "expect(",
    ],
}


def classify_failure(error: str | None) -> str:
    """Name the pattern an error message looks like, or "unknown"."""

    if not error:
        return "unknown"

    error_lower = error.lower()

    for pattern, indicators in PATTERNS.items():
        for indicator in indicators:
            if indicator in error_lower:
                return pattern

    return "unknown"


def analyze_failure_patterns(results: list[FailureEvidence]) -> list[dict]:
    """Group failures by the pattern their error message resembles.

    A pattern names what an error looks like, not why the test failed, so the
    errors are there to be read rather than taken as a diagnosis.
    """

    patterns: dict[str, list[FailureEvidence]] = defaultdict(list)

    for result in results:
        patterns[classify_failure(result.error)].append(result)

    output = []

    for pattern, failures in patterns.items():
        # One entry per affected test rather than per failure, so a test that
        # failed the same way on two projects reads as one problem on two
        # browsers instead of two unrelated problems.
        by_test: dict[str, list[FailureEvidence]] = defaultdict(list)
        for failure in failures:
            by_test[failure.test_id].append(failure)

        output.append({
            "pattern": pattern,
            "occurrences": len(failures),
            "affected_tests": len(by_test),
            "failures": [
                {
                    "test_id": test_id,
                    "projects": list(dict.fromkeys(
                        run.project for run in runs if run.project
                    )),
                    "errors": list(dict.fromkeys(
                        run.error for run in runs if run.error
                    )),
                }
                for test_id, runs in by_test.items()
            ],
        })

    return output
