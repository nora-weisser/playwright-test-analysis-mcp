# Playwright Report MCP

An MCP server that exposes Playwright JSON test reports as tools for LLM agents.

## Requirements

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js + npx — only for `mcp dev`, which launches the MCP Inspector

## 1. Install dependencies

From the repository root:

```bash
uv sync
```

This creates `.venv/` and installs the project in editable mode. Every command below is run through `uv run`, so you never need to activate the venv manually.

## 2. Produce a Playwright JSON report

The server reads a Playwright report produced by the `json` reporter. In your Playwright project:

```bash
npx playwright test --reporter=json > results.json
```

Or configure it permanently in `playwright.config.ts`:

```ts
export default defineConfig({
  reporter: [['json', { outputFile: 'results.json' }]],
});
```

The file must contain the standard top-level keys `config`, `suites`, `errors`, `stats`.

A sample report is bundled at `results.json` if you just want to try the server out.

## 3. Configure the paths

The server reads two settings, both configured in the `env` block of `.mcp.json`:

| Setting | Points at | Default |
|---|---|---|
| `REPORT_PATH` | the report of the latest run | the bundled sample, `src/playwright_report_mcp/results.json` |
| `HISTORY_DIR` | past runs, one report per run: `run-001.json`, `run-002.json`, ... | `data/history` |

```json
"env": {
  "REPORT_PATH": "src/playwright_report_mcp/results.json",
  "HISTORY_DIR": "data/history"
}
```

Relative paths are read from the repository root, so the same config works on any machine and whatever directory the client was started in. Absolute paths are used as given.

Both are read at every tool call, so you can regenerate the report, or drop a new run into the history, without restarting the server. Both have defaults pointing into the repository, so the server answers with no configuration at all — set them to work against your own project.

To run the server outside an MCP client, set them in the shell instead:

```bash
REPORT_PATH=src/playwright_report_mcp/results.json uv run playwright-report-mcp
```

## 4. Build up a history

`get_test_history` answers from the reports kept in `data/history`. After each run, copy the reporter's output in as the next number:

```bash
cp results.json data/history/run-002.json
```

Anything matching `run-*.json` is read, so generated runs and real ones are treated alike. One run is enough for the tool to work; three or more before a trend means anything.

## 5. Run the server

### Interactive development (MCP Inspector)

```bash
uv run mcp dev src/playwright_report_mcp/server.py
```

Opens the MCP Inspector in your browser, where you can list and invoke the tools by hand. Requires `npx`.

This reads the bundled sample report, because the Inspector cannot be given
`REPORT_PATH` from your shell: it spawns the server with a fixed set of
variables (`HOME`, `LOGNAME`, `PATH`, `SHELL`, `TERM`, `USER`) and drops the
rest, so exporting one has no effect. To point the Inspector at a different
report, use the **Environment Variables** fields in its own configuration panel.

Each way of starting the server takes its configuration from a different place:

| Launched by | Configuration comes from |
|---|---|
| MCP Inspector (`mcp dev`) | the Inspector's Environment Variables fields |
| Your shell (`mcp run`, `playwright-report-mcp`) | exported variables |
| Claude Code | the `env` block in `.mcp.json` |

### Plain stdio server

```bash
uv run playwright-report-mcp
```

or, equivalently:

```bash
uv run mcp run src/playwright_report_mcp/server.py
```

Speaks the MCP protocol over stdin/stdout. Useful for wiring into an MCP client, or for a quick smoke test:

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}\n' \
  | uv run playwright-report-mcp
```

You should get back a JSON-RPC result with `"serverInfo":{"name":"Playwright Report",...}`.

### Connect it to Claude Code

The project is wired up by a project-scoped `.mcp.json`, so no setup is needed beyond `uv sync`:

```json
{
  "mcpServers": {
    "playwright-report": {
      "command": "uv",
      "args": ["run", "playwright-report-mcp"],
      "env": {
        "REPORT_PATH": "src/playwright_report_mcp/results.json",
        "HISTORY_DIR": "data/history"
      }
    }
  }
}
```

Claude Code launches MCP servers with the working directory set to the project root, so `uv` resolves this project's venv without any absolute paths.

Start a session with `claude` from the repository root and approve the server when prompted — project-scoped servers need a one-time approval. Servers are loaded at startup, so a session that was already running won't see it until you restart.

Verify the connection with `/mcp` inside the session, or from a terminal:

```bash
claude mcp list
```

You want `playwright-report: uv run playwright-report-mcp - ✔ Connected`. Then just ask, e.g. *"how many tests failed in the last Playwright run?"*.

To register it for every project instead of only this one, or to keep it out of version control:

```bash
claude mcp add playwright-report -s user -- uv --directory /absolute/path/to/playwright-test-analysis-mcp run playwright-report-mcp
```

`--directory` matters here: outside this repository, it is what makes `uv` resolve this project's venv. Pass the paths too, with `-e REPORT_PATH=... -e HISTORY_DIR=...`, since a user-scoped entry has no `.mcp.json` behind it.

### Connect it to Claude Desktop

Add the server to `claude_desktop_config.json` (`~/Library/Application Support/Claude/` on macOS):

```json
{
  "mcpServers": {
    "playwright-report": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/playwright-test-analysis-mcp",
        "run",
        "playwright-report-mcp"
      ]
    }
  }
}
```

Quit Claude Desktop completely (Cmd-Q, not just closing the window) and reopen it, then check the tools icon in the chat input for the server and its tools. Per-server logs land in `~/Library/Logs/Claude/mcp-server-playwright-report.log`.

Avoid `uv run mcp install src/playwright_report_mcp/server.py`. It writes an entry that runs the server through `--with mcp[cli]` in an isolated environment and without `--directory`, so this project's package is never importable and the server fails to start with `ModuleNotFoundError: No module named 'playwright_report_mcp'`.

## Tools

| Tool | Description |
|------|-------------|
| `get_test_summary` | Summary of the latest run: `start_time`, `duration_ms`, `passed`, `failed`, `skipped`, `flaky`. |
| `get_failures` | List of failed tests, each with `test_id`, `title`, `file`, `project`, `status` and the most detailed `error` message. One entry per test per project. Flaky tests are included — they failed before they passed — and `status` tells them from outright failures. |
| `get_failure_patterns` | The run's failures grouped by what their error messages look like, e.g. `locator-not-found`, `assertion-failure`. |
| `get_unstable_tests` | The tests that most often fail or flake across past runs, worst first: `instability_rate`, the counts behind it, the `failure_patterns` seen, and `last_status`. One entry per test per project. Takes a `limit` (default 10), optionally a `project`. |
| `get_test_history` | How one test has done across past runs: `total_runs`, `passed`, `failed`, `failure_rate`, and every run with the pattern it failed on. Takes a `test_id`, optionally a `project`. |

The first four answer about the latest run or the history in general;
`get_test_history` needs a `test_id`. `get_unstable_tests` is where you get
one — including for a test that fails half the time but happened to pass in
the latest run, which the failure tools would not mention at all.

## Running the tests

```bash
uv run pytest
```

The suite covers the report parsing (run stats, trimmed failures, the run context recorded alongside each failure), the history built from the five fixture runs in `tests/fixtures/history`, and the tools themselves, called over an in-memory MCP client.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Tools answer about the wrong tests | With `REPORT_PATH` unset the server reads the bundled sample report. Set it to your own run. |
| `No Playwright report at ...` | The path in the message is what `REPORT_PATH` resolved to. Relative paths are read from the repository root, not the working directory. |
| `... is not a Playwright JSON report` | The file isn't `json`-reporter output (e.g. an HTML report or a raw blob). |
| `mcp dev` fails to start | Install Node.js so `npx` is available, or use `mcp run` instead. |
| `ModuleNotFoundError: No module named 'playwright_report_mcp'` | The client config runs `uv` without `--directory` from outside the repository. Use one of the configs above. |
| Server missing from `/mcp` in Claude Code | Servers load at startup — restart the session, and approve the project-scoped server when prompted. |
