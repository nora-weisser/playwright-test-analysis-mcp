from pydantic import BaseModel

class TestSummary(BaseModel):
    start_time: str
    duration_ms: float
    passed: int
    failed: int
    skipped: int
    flaky: int
