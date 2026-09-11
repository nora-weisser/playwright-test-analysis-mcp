"""Where the server reads its reports from.

Two settings, `REPORT_PATH` and `HISTORY_DIR`, each with a default pointing
into the repository so the server answers with no configuration at all. Both
are read at every call rather than once at import, so a regenerated report or
a newly dropped run is picked up without restarting the server.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Where past runs are kept: one Playwright JSON report per run, named
# run-001.json, run-002.json, ... Copied there after a run, or generated.
DEFAULT_HISTORY_DIR = PROJECT_ROOT / "data" / "history"

# The report of the latest run. Defaulted, like the history directory, so the
# server answers on every launch path rather than only the configured one: the
# MCP Inspector spawns servers with a fixed set of environment variables
# (HOME, LOGNAME, PATH, SHELL, TERM, USER) and drops the rest, so REPORT_PATH
# cannot reach the process there however it is exported.
DEFAULT_REPORT_PATH = PROJECT_ROOT / "src" / "playwright_report_mcp" / "results.json"


def resolve_path(path: str) -> Path:
    """Read a configured path, relative ones counting from the project root.

    The paths come from .mcp.json, or the shell, or the Inspector -- none of
    which can be assumed to have started the server from the repository.
    """

    configured = Path(path).expanduser()
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


def get_report_path() -> Path:
    """Return the report to read, falling back to the bundled sample run."""

    path = os.getenv("REPORT_PATH")
    return resolve_path(path) if path else DEFAULT_REPORT_PATH


def get_history_dir() -> Path:
    """Return the history directory, overridable for a different checkout."""

    path = os.getenv("HISTORY_DIR")
    return resolve_path(path) if path else DEFAULT_HISTORY_DIR
