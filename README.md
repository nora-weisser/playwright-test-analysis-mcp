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

A sample report is bundled at [results.json](src/playwright_report_mcp/results.json) if you just want to try the server out.

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

### Connect it to a client

Register the server with Claude Desktop:

```bash
uv run mcp install src/playwright_report_mcp/server.py
```

Or add it manually to an MCP client config (e.g. `claude_desktop_config.json`):

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

`--directory` matters: it makes `uv` resolve this project's venv and lets `load_dotenv()` find the `.env` file.

## Tools

| Tool | Description |
|------|-------------|
| `get_test_summary` | Summary of the latest run: `start_time`, `duration_ms`, `passed`, `failed`, `skipped`, `flaky`. |
| `get_failures` | List of failed tests, each with `title`, `file`, `status` and the first `error` message. |

## Running the tests

`pytest` and `pytest-asyncio` are installed, but the repository has no test files yet, so this currently collects 0 tests:

```bash
uv run pytest
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `REPORT_PATH environment variable is not set.` | Create `.env` in the repo root, or export `REPORT_PATH` in the shell that starts the server. |
| `FileNotFoundError` on a tool call | `REPORT_PATH` points at a file that doesn't exist — use an absolute path. |
| `KeyError: 'stats'` | The JSON isn't a Playwright `json`-reporter report (e.g. it's an HTML report or a raw blob). |
| `mcp dev` fails to start | Install Node.js so `npx` is available, or use `mcp run` instead. |
