from pydantic import BaseModel


class FailureEvidence(BaseModel):
    """Everything the report tells us about one failed test.

    Wider than what `get_failed_tests` exposes: the run context (workers,
    project, CI, retries) is recorded alongside the error message, because a
    failure often only makes sense against the run it happened in.
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
    workers: int = 1
    fully_parallel: bool = False
    ci: bool = False
    attachments: list[str] = []
    trace_path: str | None = None
