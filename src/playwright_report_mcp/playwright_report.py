import json
import re
from pathlib import Path
from playwright_report_mcp.models.failure import FailureEvidence
from playwright_report_mcp.models.test_result import TestResult, normalize_status
from playwright_report_mcp.models.test_summary import TestSummary

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

FAILURE_FIELDS = ("test_id", "title", "file", "status", "error")


def strip_ansi(text: str) -> str:
    """Remove terminal colour codes Playwright embeds in error messages."""

    return ANSI_ESCAPE.sub("", text)


class PlaywrightReport:
    """One Playwright JSON report, read as normalized test results.

    The single place that knows how Playwright's JSON is shaped: a stored run
    from the history directory is read exactly like the latest run.
    """

    def __init__(self, path: Path):
        self.path = path
        self._report: dict | None = None

    def load(self) -> dict:
        """Read the report, once per instance.

        Callers build a fresh `PlaywrightReport` per request, so the cache
        never hands out a stale run -- it only stops history from re-reading
        the same file for every question asked of it.
        """

        if self._report is None:
            with self.path.open("r", encoding="utf-8") as file:
                self._report = json.load(file)
        return self._report

    def get_started_at(self) -> str | None:
        """Return when the run started, which is what orders history."""

        return self.load().get("stats", {}).get("startTime")

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

    def get_test_results(self) -> list[TestResult]:
        """Return every test in the report, passed and failed alike.

        One entry per test per project: a spec that runs on chromium and
        firefox is two results, because they can disagree.
        """

        results: list[TestResult] = []
        self._collect(self.load().get("suites", []), results)
        return results

    def get_failed_tests(self) -> list[dict]:
        """Return the failed tests, trimmed to the fields that read well as text."""

        return [
            evidence.model_dump(include=set(FAILURE_FIELDS))
            for evidence in self.get_failure_evidence()
        ]

    def get_failure_evidence(self) -> list[FailureEvidence]:
        """Return everything the report says about each failed test.

        Deliberately wider than what `get_failed_tests` exposes: the run
        context (workers, parallelism, CI) is recorded too, because it says as
        much about a failure as the error message itself.
        """

        context = self._run_context(self.load().get("config", {}))
        return [
            FailureEvidence(**result.model_dump(), **context)
            for result in self.get_test_results()
            if result.status == "failed"
        ]

    def _run_context(self, config: dict) -> dict:
        """Extract the run-wide facts that individual failures are judged against."""

        metadata = config.get("metadata") or {}
        return {
            "workers": config.get("workers") or metadata.get("actualWorkers") or 1,
            "fully_parallel": bool(config.get("fullyParallel")),
            "ci": bool(metadata.get("ci")),
        }

    def _pick_error_message(self, test: dict) -> str | None:
        """Return the most detailed error message of a failed test.

        Playwright reports a terse message alongside a fuller one that carries
        the call log, so the longest message is the most useful for diagnosis.
        """

        messages = []
        for result in test.get("results", []):
            if result.get("error"):
                messages.append(result["error"].get("message"))
            for error in result.get("errors", []):
                messages.append(error.get("message"))
        messages = [message for message in messages if message]
        return strip_ansi(max(messages, key=len)) if messages else None

    def _build_result(self, spec: dict, suite: dict, test: dict) -> TestResult:
        results = test.get("results", []) or [{}]
        last_result = results[-1]
        attachments = last_result.get("attachments", []) or []
        trace = next((item for item in attachments if item.get("name") == "trace"), None)

        title = spec.get("title")
        file = spec.get("file") or suite.get("file")

        return TestResult(
            # File and title together, so the same test keeps the same id from
            # one run to the next and two files may share a title. The project
            # stays a field of its own: the same test failing on firefox only
            # is one test behaving differently, not a second test.
            test_id=f"{file} > {title}" if file else title,
            title=title,
            file=file,
            project=test.get("projectName"),
            status=normalize_status(test.get("status")),
            result_status=last_result.get("status"),
            error=self._pick_error_message(test),
            retries=max((result.get("retry", 0) for result in results), default=0),
            duration_ms=last_result.get("duration") or 0,
            timeout_ms=test.get("timeout") or 0,
            timed_out=any(result.get("status") == "timedOut" for result in results),
            attachments=[item.get("name") for item in attachments if item.get("name")],
            trace_path=trace.get("path") if trace else None,
        )

    def _collect(self, suites: list[dict], results: list[TestResult]) -> None:
        for suite in suites:
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    results.append(self._build_result(spec, suite, test))
            self._collect(suite.get("suites", []), results)
