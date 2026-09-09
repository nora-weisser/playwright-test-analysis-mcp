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

## 3. Configure the report path

Create a `.env` file in the repository root pointing at that report (absolute path recommended):

```
REPORT_PATH=/absolute/path/to/results.json
```

To use the bundled sample instead:

```
REPORT_PATH=/absolute/path/to/playwright-test-analysis-mcp/src/playwright_report_mcp/results.json
```

`REPORT_PATH` is read at every tool call, so you can regenerate the report without restarting the server. If it is unset, tool calls fail with `REPORT_PATH environment variable is not set.`

## 4. Run the server

### Interactive development (MCP Inspector)

```bash
uv run mcp dev src/playwright_report_mcp/server.py
```

Opens the MCP Inspector in your browser, where you can list and invoke the tools by hand. Requires `npx`.

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

The repository ships a project-scoped `.mcp.json`, so no setup is needed beyond `uv sync`:

```json
{
  "mcpServers": {
    "playwright-report": {
      "command": "uv",
      "args": ["run", "playwright-report-mcp"]
    }
  }
}
```

Claude Code launches MCP servers with the working directory set to the project root, so `uv` resolves this project's venv and `load_dotenv()` finds `.env` without any absolute paths.

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

`--directory` matters here: outside this repository, it is what makes `uv` resolve this project's venv and find `.env`.

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

Quit Claude Desktop completely (Cmd-Q, not just closing the window) and reopen it, then check the tools icon in the chat input for the server and its two tools. Per-server logs land in `~/Library/Logs/Claude/mcp-server-playwright-report.log`.

Avoid `uv run mcp install src/playwright_report_mcp/server.py`. It writes an entry that runs the server through `--with mcp[cli]` in an isolated environment and without `--directory`, so this project's package is never importable and the server fails to start with `ModuleNotFoundError: No module named 'playwright_report_mcp'`.

## Tools

| Tool | Description |
|------|-------------|
| `get_test_summary` | Summary of the latest run: `start_time`, `duration_ms`, `passed`, `failed`, `skipped`, `flaky`. |
| `get_failures` | List of failed tests, each with `test_id`, `title`, `file`, `status` and the most detailed `error` message. |

## Running the tests

```bash
uv run pytest
```

The suite covers the report parsing: reading the run stats, trimming failures to the readable fields, and preserving the run context recorded alongside each failure.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `REPORT_PATH environment variable is not set.` | Create `.env` in the repo root, or export `REPORT_PATH` in the shell that starts the server. |
| `FileNotFoundError` on a tool call | `REPORT_PATH` points at a file that doesn't exist — use an absolute path. |
| `KeyError: 'stats'` | The JSON isn't a Playwright `json`-reporter report (e.g. it's an HTML report or a raw blob). |
| `mcp dev` fails to start | Install Node.js so `npx` is available, or use `mcp run` instead. |
| `ModuleNotFoundError: No module named 'playwright_report_mcp'` | The client config runs `uv` without `--directory` from outside the repository. Use one of the configs above. |
| Server missing from `/mcp` in Claude Code | Servers load at startup — restart the session, and approve the project-scoped server when prompted. |
