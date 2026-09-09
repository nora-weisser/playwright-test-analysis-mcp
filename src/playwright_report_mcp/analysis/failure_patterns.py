from collections import defaultdict
from playwright_report_mcp.models.failure import FailureEvidence

MAX_EXAMPLES = 3

# Checked in order, first hit wins, so the more specific patterns come first:
# "TimeoutError: locator.click: ..." carries both a locator and a timeout, and
# the timeout is the better description of it.
PATTERNS = {
    "locator-not-found": [
        "waiting for locator",
        "element(s) not found",
        "strict mode violation",
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
    examples are there to be read rather than taken as a diagnosis.
    """

    patterns: dict[str, list[FailureEvidence]] = defaultdict(list)

    for result in results:
        patterns[classify_failure(result.error)].append(result)

    output = []

    for pattern, failures in patterns.items():
        test_ids = list(dict.fromkeys(failure.test_id for failure in failures))

        examples = [failure.error for failure in failures if failure.error][:MAX_EXAMPLES]

        output.append({
            "pattern": pattern,
            "occurrences": len(failures),
            "affected_tests": len(test_ids),
            "test_ids": test_ids,
            "examples": examples,
        })

    return output
