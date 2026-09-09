import json
import re
from pathlib import Path
from playwright_report_mcp.models.failure import FailureEvidence
from playwright_report_mcp.models.test_summary import TestSummary

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

FAILURE_FIELDS = ("test_id", "title", "file", "status", "error")


def strip_ansi(text: str) -> str:
    """Remove terminal colour codes Playwright embeds in error messages."""

    return ANSI_ESCAPE.sub("", text)


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
        """Return the failed tests, trimmed to the fields that read well as text."""

        return [
            evidence.model_dump(include=set(FAILURE_FIELDS))
            for evidence in self.get_failure_evidence()
        ]

    def get_failure_evidence(self) -> list[FailureEvidence]:
        """Return everything the report says about each failed test.

        Deliberately wider than what `get_failed_tests` exposes: the run
        context (workers, project, CI, retries) is recorded too, because it
        says as much about a failure as the error message itself.
        """

        report = self.load()
        context = self._run_context(report.get("config", {}))
        failures: list[FailureEvidence] = []
        self._collect_failures(report.get("suites", []), context, failures)
        return failures

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

    def _build_evidence(self, spec: dict, suite: dict, test: dict, context: dict) -> FailureEvidence:
        results = test.get("results", []) or [{}]
        last_result = results[-1]
        attachments = last_result.get("attachments", []) or []
        trace = next((item for item in attachments if item.get("name") == "trace"), None)

        title = spec.get("title")
        file = spec.get("file") or suite.get("file")
        timeout_ms = test.get("timeout") or 0

        return FailureEvidence(
            test_id=f"{file} > {title}" if file else title,
            title=title,
            file=file,
            project=test.get("projectName"),
            status=test.get("status"),
            result_status=last_result.get("status"),
            error=self._pick_error_message(test),
            retries=max((result.get("retry", 0) for result in results), default=0),
            duration_ms=last_result.get("duration") or 0,
            timeout_ms=timeout_ms,
            timed_out=any(result.get("status") == "timedOut" for result in results),
            attachments=[item.get("name") for item in attachments if item.get("name")],
            trace_path=trace.get("path") if trace else None,
            **context,
        )

    def _collect_failures(self, suites: list[dict], context: dict, failures: list[FailureEvidence]) -> None:
        for suite in suites:
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    if test.get("status") == "unexpected":
                        failures.append(self._build_evidence(spec, suite, test, context))
            self._collect_failures(suite.get("suites", []), context, failures)
