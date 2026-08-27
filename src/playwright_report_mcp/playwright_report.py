import json
from pathlib import Path
from playwright_report_mcp.models.test_summary import TestSummary
class PlaywrightReport:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict:
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def get_summary(self) -> "TestSummary":
        report = self.load()
        stats = report["stats"]
        return TestSummary(
            start_time=stats["startTime"],
            duration_ms=stats["duration"],
            passed=stats["expected"],
            failed=stats["unexpected"],
            skipped=stats["skipped"],
            flaky=stats["flaky"],
        )

    def get_failed_tests(self) -> list[dict]:
        report = self.load()
        failures = []
        self._collect_failures(report.get("suites", []), failures)
        return failures

    def _collect_failures(self, suites: list[dict], failures: list[dict]) -> None:
        for suite in suites:
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    if test.get("status") == "unexpected":
                        error_message = None
                        for result in test.get("results", []):
                            if result.get("error"):
                                error_message = result["error"].get("message")
                                break
                        failures.append({
                            "title": spec.get("title"),
                            "file": spec.get("file") or suite.get("file"),
                            "status": test.get("status"),
                            "error": error_message,
                        })
            self._collect_failures(suite.get("suites", []), failures)
