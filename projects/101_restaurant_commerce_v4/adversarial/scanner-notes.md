# Native security scanners

`run.sh` invokes `scanners.py` after the real application baseline and other HTTP
layers. To rerun only these layers against an existing disposable environment:

```sh
python adversarial/scanners.py --config RUN/config.json --output RUN/scanners
```

The config is private synthetic test configuration, not an evidence artifact to
publish. The runner refuses a non-loopback ZAP target. Use a fresh output folder;
failed attempts are evidence and must not be overwritten. A nonzero runner exit
means at least one layer failed, was incomplete, or was blocked. Review each
layer's execution status separately from its security outcome.

Portable tool bootstrapping is included: Semgrep CE 1.182.1 (isolated Python 3.12
venv), Trivy 0.76.1, ZAP 2.17.0, and Temurin JRE 17.0.21+9. Public archive
checksums are pinned in the runner. Downloads, native versions, commands, UTC
start/end times and exit codes are recorded. `uv` and network access are required
for a fresh setup. `COMMERCE_TOOLCHAIN`, `COMMERCE_TRIVY_CACHE`, and `TMPDIR` can
point to task-owned disk directories when `/tmp` has a quota. Rule registries and
vulnerability databases can change; preserve reports and source hash inventories.

ZAP imports the live OpenAPI specification, seeds all four existing web pages,
and proves successful staff-token and order-capability access before scanning.
M4 has named, scoped staff sessions but no full customer login; the
suite does not simulate those missing features into existence. Active attacks
use an explicit HTTP rule list, a loopback context, two threads, LOW strength,
one minute per rule and five minutes overall. External callback, DOM-browser,
and unrelated database-engine rules are excluded. Native 100% at the time
budget is PARTIAL, not completion. Message IDs, a bounded native HTTP history
sample, protected-route success counts, rule progress, alerts and API calls are
retained. Missing Firefox profile warnings from ZAP startup are not execution of
a DOM-browser rule; DOM scanning is explicitly outside the selected policy.
For a narrow customer follow-up, set `zap_focus_customer: true` in a private
copy of the run config. The same rule policy then scans only the freshly seeded
customer order URL with recursion disabled. Header exports cover up to 10,000
history records; summaries identify counts as lower bounds if that cap is reached.

Semgrep scans source Python/JavaScript. Its `avoid-sqlalchemy-text` finding in
`migrations.py` is retained in native output and the raw scanner outcome remains
FAIL. Review shows the identifiers and declarations come from the constant
`CUSTOMER_SAFETY_COLUMNS` mapping, not request input. This is an audit finding,
not a reproduced SQL injection. No blanket suppression was added.

Trivy scans the disposable source for secrets and configuration, and the actual
installed runtime's frozen dependencies for known vulnerabilities. The optional
`adversarial/Dockerfile` supplies a concrete configuration target. It is a
proposed disposable image, not a tested production artifact. A built-container
scan requires a `container_image_archive` config path: without one it is BLOCKED
and runtime probes are retained. The native app run is not a substitute for a
container build or scan. To build the optional image, a container engine is
required; mount the config readable by UID 10001 and provide reachable owned
PostgreSQL/provider endpoints. Its two-worker entrypoint uses only the installed
commerce package and `adversarial/runtime.py`.

Strix remains BLOCKED without explicit model spending authorization and a hard
budget/configuration. The runner never starts paid model calls. Credentials
being present elsewhere does not establish authorization or provider health.
No scanner finding or absence of findings establishes readiness for real money.
