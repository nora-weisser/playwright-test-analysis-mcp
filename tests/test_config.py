from pathlib import Path
from playwright_report_mcp.config import (
    DEFAULT_REPORT_PATH,
    PROJECT_ROOT,
    get_history_dir,
    get_report_path,
    resolve_path,
)


def test_relative_config_paths_are_read_from_the_project_root():
    """.mcp.json is shared, so its paths cannot depend on where Claude started."""

    assert resolve_path("data/history") == PROJECT_ROOT / "data" / "history"


def test_absolute_config_paths_are_left_alone():
    assert resolve_path("/somewhere/else/results.json") == Path("/somewhere/else/results.json")


def test_the_configured_paths_point_at_real_files(monkeypatch):
    """The defaults shipped in .mcp.json, checked against the repo."""

    monkeypatch.setenv("REPORT_PATH", "src/playwright_report_mcp/results.json")
    monkeypatch.setenv("HISTORY_DIR", "data/history")

    assert get_report_path().is_file()
    assert get_history_dir().is_dir()


def test_the_report_defaults_to_the_bundled_sample(monkeypatch):
    """No REPORT_PATH is not an error: the Inspector cannot supply one.

    It spawns servers with a fixed set of environment variables and drops
    everything else, so a default is the only thing that reaches the process.
    """

    monkeypatch.delenv("REPORT_PATH", raising=False)

    assert get_report_path() == DEFAULT_REPORT_PATH
    assert get_report_path().is_file()


def test_an_explicit_report_path_still_wins(monkeypatch):
    monkeypatch.setenv("REPORT_PATH", "/elsewhere/results.json")

    assert get_report_path() == Path("/elsewhere/results.json")
