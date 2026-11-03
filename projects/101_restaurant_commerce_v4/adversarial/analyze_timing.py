"""Summarize observed timings without assigning unexplained time to the database."""

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def stats(values):
    if not values:
        return {"count": 0}
    v = sorted(values)

    def pct(p):
        return v[min(len(v) - 1, max(0, __import__("math").ceil(len(v) * p) - 1))]

    return {
        "count": len(v),
        "mean": sum(v) / len(v),
        "p50": pct(0.5),
        "p95": pct(0.95),
        "p99": pct(0.99),
        "max": v[-1],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    a = p.parse_args()
    allrows = []
    for path in (a.directory / "environment/timing").glob("*.jsonl"):
        allrows.extend(json.loads(line) for line in path.read_text().splitlines())
    supplemental = a.directory / "blocked-tables.jsonl"
    table_samples = (
        [json.loads(line) for line in supplemental.read_text().splitlines()]
        if supplemental.exists()
        else []
    )
    results = []
    for block in json.loads((a.directory / "execution.json").read_text()):
        name = block["condition"]
        pg = [
            json.loads(line)
            for line in (a.directory / (name + "-postgres.jsonl")).read_text().splitlines()
        ]
        for phase in json.loads((a.directory / name / "summary.json").read_text()):
            start = datetime.fromisoformat(phase["start"]).timestamp() * 1e9
            end = datetime.fromisoformat(phase["end"]).timestamp() * 1e9
            rows = [
                r for r in allrows if start <= r["utc_ns"] <= end and r["route"].endswith("/orders")
            ]
            # Replay shares a route, but has no provider call. Report these populations separately.
            populations = {}
            for label, pop in [
                ("all_order_posts", rows),
                (
                    "provider_checkouts",
                    [r for r in rows if any(s["name"] == "provider_executor" for s in r["spans"])],
                ),
            ]:
                fields = defaultdict(list)
                for r in pop:
                    fields["request_ms"].append(r["total_ms"])
                    totals = defaultdict(float)
                    for s in r["spans"]:
                        totals[s["name"]] += s["duration_ms"]
                    fields["sql_count"].append(
                        sum(s["name"].startswith("sql_") for s in r["spans"])
                    )
                    for key in [
                        "sql_execute",
                        "sql_error",
                        "connection_acquire",
                        "commit_including_flush",
                        "provider_executor",
                        "endpoint_dispatch_wait",
                        "endpoint",
                    ]:
                        fields[key + "_ms"].append(totals[key])
                    # Commit contains SQL; exclude it from the remainder calculation.
                    fields["unattributed_endpoint_ms"].append(
                        max(
                            0,
                            totals["endpoint"]
                            - totals["sql_execute"]
                            - totals["sql_error"]
                            - totals["connection_acquire"]
                            - totals["provider_executor"],
                        )
                    )
                populations[label] = {k: stats(v) for k, v in fields.items()}
            samples = [r for r in pg if start <= r["utc_ns"] <= end]
            table_waits = Counter()
            covered = [r for r in table_samples if start <= r["utc_ns"] <= end]
            for r in covered if table_samples else samples:
                table_waits.update(r.get("blocked_statement_tables", {}))
            waits = Counter()
            for r in samples:
                for state in r["states"]:
                    if state["state"] == "active":
                        waits[str(state["wait_event_type"]) + ":" + str(state["wait_event"])] += (
                            state["n"]
                        )
            results.append(
                {
                    "condition": name,
                    "phase": phase["profile"],
                    "outcome": phase["outcome"],
                    "client": phase["counts"],
                    "database_audit": phase["database_audit"],
                    "timing": populations,
                    "postgres": {
                        "samples": len(samples),
                        "table_observer_samples": len(covered) if table_samples else len(samples),
                        "blocked_table_connection_samples": dict(table_waits),
                        "blocked_samples": sum(r["blocked_connections"] > 0 for r in samples),
                        "max_blocked": max((r["blocked_connections"] for r in samples), default=0),
                        "active_connection_samples_by_wait": dict(waits),
                    },
                }
            )
    protocol = json.loads((a.directory / "protocol.json").read_text())
    enabled = {row[0]: row[1] for row in protocol["conditions"]}
    gaps = []
    if len(results) != len(protocol["conditions"]) * len(protocol["phases"]):
        gaps.append("Not all planned phases executed")
    for row in results:
        if row["postgres"]["samples"] < 10:
            gaps.append(row["condition"] + ": insufficient PostgreSQL samples")
        if enabled[row["condition"]] and not row["timing"]["provider_checkouts"]:
            gaps.append(row["condition"] + ": missing checkout timing")
    assessment = {
        "execution": "PARTIAL" if gaps else "COMPLETE",
        "outcome": "PASS" if not gaps and all(r["outcome"] == "PASS" for r in results) else "FAIL",
        "coverage_gaps": gaps,
        "phases": len(results),
    }
    (a.directory / "timing-assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
    (a.directory / "analysis.json").write_text(json.dumps(results, indent=2) + "\n")
    for r in results:
        if r["phase"] == "warmup":
            continue
        op = next(x for x in r["client"]["operations"] if x["name"] == "checkout")
        print(
            r["condition"],
            r["phase"],
            r["outcome"],
            "checkouts",
            r["client"]["completed_checkouts"],
            "p50/p95/p99",
            *[op[k] for k in ["p50_ms", "p95_ms", "p99_ms"]],
        )
        print(
            " spans:",
            {
                k: round(v["mean"], 2)
                for k, v in r["timing"]["provider_checkouts"].items()
                if v.get("count")
            },
        )
        print(" pg:", r["postgres"])

    if assessment["outcome"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
