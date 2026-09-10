from pydantic import BaseModel

# Playwright names a test's outcome against its expectation ("expected",
# "unexpected"), which only reads well inside a single run. History compares
# runs to each other, so the outcome itself is the more useful name.
STATUS_NAMES = {
    "expected": "passed",
    "unexpected": "failed",
    "skipped": "skipped",
    "flaky": "flaky",
}


def normalize_status(status: str | None) -> str:
    """Return the plain outcome name for a Playwright test status."""

    return STATUS_NAMES.get(status or "", "unknown")


class TestResult(BaseModel):
    """One test, as one run saw it.

    The normalized shape every analysis starts from: failure evidence and
    test history are both built on top of this, so they agree on what a test
    is and on what happened to it.
    """

    test_id: str
    title: str | None = None
    file: str | None = None
    project: str | None = None
    status: str | None = None
    result_status: str | None = None
    error: str | None = None
    retries: int = 0
    duration_ms: float = 0.0
    timeout_ms: float = 0.0
    timed_out: bool = False
    attachments: list[str] = []
    trace_path: str | None = None
