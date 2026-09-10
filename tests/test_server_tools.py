from pathlib import Path
import pytest
from mcp import Client
from playwright_report_mcp.server import (
    DEFAULT_REPORT_PATH,
    PROJECT_ROOT,
    get_history_dir,
    get_report_path,
    mcp,
    resolve_path,
)

HISTORY_DIR = Path(__file__).parent / "fixtures" / "history"
CHECKOUT = "checkout.spec.ts > TC-C01: proceeds to payment"


@pytest.fixture(autouse=True)
def history_dir(monkeypatch):
    """Point the server at the fixture runs rather than the real history."""

    monkeypatch.setenv("HISTORY_DIR", str(HISTORY_DIR))


@pytest.mark.asyncio
async def test_get_test_history_answers_over_mcp():
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool("get_test_history", {"test_id": CHECKOUT})

    assert result.is_error is False
    assert result.structured_content is not None

    history = result.structured_content
    assert history["total_runs"] == 5
    assert history["failed"] == 2
    assert history["failure_rate"] == pytest.approx(0.4)
    assert [run["status"] for run in history["runs"]] == [
        "passed", "passed", "failed", "passed", "failed",
    ]


@pytest.mark.asyncio
async def test_get_test_history_is_listed_as_a_tool():
    async with Client(mcp, raise_exceptions=True) as client:
        tools = await client.list_tools()

    assert "get_test_history" in {tool.name for tool in tools.tools}


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


@pytest.mark.asyncio
async def test_get_test_summary_works_with_nothing_configured(monkeypatch):
    """The whole server answers out of the box -- the bug this fixes."""

    monkeypatch.delenv("REPORT_PATH", raising=False)
    monkeypatch.delenv("HISTORY_DIR", raising=False)

    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool("get_test_summary", {})

    assert result.is_error is False
    assert result.structured_content["passed"] == 5


@pytest.mark.asyncio
async def test_get_unstable_tests_answers_over_mcp():
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool("get_unstable_tests", {})

    assert result.is_error is False

    tests = result.structured_content["result"]
    assert [test["test_id"] for test in tests] == [CHECKOUT]
    assert tests[0]["instability_rate"] == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_the_id_from_get_unstable_tests_works_in_get_test_history():
    """The point of the tool: it hands the next one something to ask about."""

    async with Client(mcp, raise_exceptions=True) as client:
        unstable = await client.call_tool("get_unstable_tests", {"limit": 1})
        test_id = unstable.structured_content["result"][0]["test_id"]

        history = await client.call_tool("get_test_history", {"test_id": test_id})

    assert history.structured_content["total_runs"] == 5
    assert history.structured_content["failed"] == 2


@pytest.mark.asyncio
async def test_get_unstable_tests_is_listed_as_a_tool():
    async with Client(mcp, raise_exceptions=True) as client:
        tools = await client.list_tools()

    assert "get_unstable_tests" in {tool.name for tool in tools.tools}


@pytest.mark.asyncio
async def test_get_test_summary_surfaces_run_errors(monkeypatch):
    """A run that died in global setup must not answer as an all-zero success."""

    monkeypatch.setenv(
        "REPORT_PATH", str(Path(__file__).parent / "fixtures" / "global-setup-failure.json")
    )

    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool("get_test_summary", {})

    summary = result.structured_content
    assert summary["failed"] == 0
    assert "ECONNREFUSED" in summary["errors"][0]
