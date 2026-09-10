from pydantic import BaseModel

class TestSummary(BaseModel):
    start_time: str
    duration_ms: float
    passed: int
    failed: int
    skipped: int
    flaky: int
    # Errors the run reports outside any test: a config that would not load, a
    # global setup that threw, a worker that died. They matter because the
    # counts above cannot show them -- a run that dies in global setup never
    # gets as far as a test, so it reports zero of everything and would
    # otherwise read as a clean run.
    errors: list[str] = []
