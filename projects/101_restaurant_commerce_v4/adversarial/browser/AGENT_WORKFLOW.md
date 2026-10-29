# Official Playwright Test Agent workflow

Tooling is pinned to `@playwright/test`1.61.1. Generated official Codex role
instructions are under `.codex/agents/`; the exact installation command is
`npx playwright init-agents --loop=codex` from this task-local package.

`agent_probe.py` speaks MCP stdio to the real
`node node_modules/playwright/cli.js run-test-mcp-server`. It invokes the official
planner setup/snapshot/save-plan tools, generator setup/browser actions/read-log/
write-test tools, and healer test-run/debug tools. The Codex session applies the
roles; this is not an autonomous paid-model invocation. Native RPC transcripts and
failed-run traces remain in each run's browser-agents output.

The official healer's suggestion to mark persistent failures `test.fixme()` is
explicitly overridden by the user's instruction. Missing reload recovery and
staff isolation remain normal failing tests with nonzero exit status. Selector or
setup repairs must preserve the acceptance condition and be documented.

The browser suite talks to a real running backend. Interception delays or drops
actual fetched responses; it never fabricates application response bodies. All
browser requests are constrained to the configured loopback origin. Each test
records live HTTP coverage, uses new synthetic data and has no retries/skips.
