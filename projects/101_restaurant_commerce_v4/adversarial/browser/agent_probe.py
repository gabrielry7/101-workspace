"""Task-local stdio client for official Playwright Test Agent MCP tools."""

import argparse, json, select, subprocess, time, os, signal, re
from pathlib import Path


def rpc(proc, request, timeout=35):
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if select.select([proc.stdout], [], [], 1)[0]:
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server exited")
            msg = json.loads(line)
            if msg.get("id") == request.get("id"):
                return msg
    raise TimeoutError(str(request.get("method")))


def run(output, calls):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()

    def budget_expired(_signum, _frame):
        raise TimeoutError("Bounded MCP invocation exceeded 200 seconds")

    signal.signal(signal.SIGALRM, budget_expired)
    signal.alarm(200)
    with (output / "mcp-stderr.txt").open("w") as stderr:
        proc = subprocess.Popen(
            ["node", "node_modules/playwright/cli.js", "run-test-mcp-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        results = []
        try:
            results.append(
                rpc(
                    proc,
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {
                                "name": "101-local-test-agent",
                                "version": "1",
                            },
                        },
                    },
                )
            )
            proc.stdin.write(
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
                + "\n"
            )
            proc.stdin.flush()
            listing = rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            results.append(listing)
            (output / "mcp-progress.json").write_text(json.dumps(results, indent=2))
            for i, call in enumerate(calls, 3):
                results.append(
                    rpc(
                        proc,
                        {
                            "jsonrpc": "2.0",
                            "id": i,
                            "method": "tools/call",
                            "params": call,
                        },
                        timeout=90,
                    )
                )
                (output / "mcp-progress.json").write_text(json.dumps(results, indent=2))
                response = results[-1]
                rendered = str(response.get("result", {}))
                if (
                    response.get("error")
                    or response.get("result", {}).get("isError")
                    or "Error while running the seed test" in rendered
                ):
                    break
        finally:
            signal.alarm(0)
            # Stop only this invocation's process group, including debugger/browser children.
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            config = (
                json.loads(Path(os.environ["COMMERCE_RUN_CONFIG"]).read_text())
                if os.environ.get("COMMERCE_RUN_CONFIG")
                else {}
            )
            tool_results = results[2:]
            tool_errors = sum(
                bool(
                    x.get("error")
                    or x.get("result", {}).get("isError")
                    or "Error while running the seed test" in str(x.get("result", {}))
                )
                for x in tool_results
            )
            failed_tests = sum(
                int(n)
                for x in tool_results
                for n in re.findall(
                    r"(?m)^  (\d+) failed",
                    "\n".join(
                        c.get("text", "")
                        for c in x.get("result", {}).get("content", [])
                    ),
                )
            )
            (output / "mcp-native.json").write_text(
                json.dumps(
                    {
                        "command": [
                            "node",
                            "node_modules/playwright/cli.js",
                            "run-test-mcp-server",
                        ],
                        "version": "1.61.1",
                        "target": config.get("base_url"),
                        "revision": config.get("revision"),
                        "start_epoch": started,
                        "end_epoch": time.time(),
                        "rpc_response_count": len(results),
                        "executed_tool_calls": len(tool_results),
                        "tool_errors": tool_errors,
                        "failed_test_executions": failed_tests,
                        "execution": "COMPLETE"
                        if len(tool_results) == len(calls) and not tool_errors
                        else "PARTIAL",
                        "outcome": "FAIL"
                        if tool_errors or failed_tests
                        else "UNASSESSED",
                        "requested_calls": calls,
                        "results": results,
                    },
                    indent=2,
                )
            )
    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--calls")
    a = p.parse_args()
    run(a.output, json.loads(Path(a.calls).read_text()) if a.calls else [])
