# M6b local release qualification

Run from `projects/101_restaurant_commerce_v4` on Linux x86_64 with Python 3.12,
`uv`, Node/npm, PostgreSQL server/client tools on PATH, libpq and Chromium (or an
installed Playwright Chromium). These are local prerequisites, not a paid service.
The selected deployment is the M6 hash-locked virtual environment, not an OCI image.
New bundles include a hash-locked pip26.2 wheel. The installer creates the environment
without ensurepip and runs that verified wheel directly, so the vulnerable bundled
installer is neither used nor left deployed. Older bundles without a locked pip wheel
must be repacked; already installed releases and rollback targets are not modified.

```bash
COMMERCE_BROWSER_EXECUTABLE=/usr/bin/chromium \
python3.12 security/check.py \
  --cache /tmp/commerce-security-tools \
  --run-dir /tmp/commerce-security-run-$(date +%s)
```

This single command downloads pinned free public tools and dependency wheels, checks
rule-pack hashes, builds and verifies the installed artifact, starts an isolated
loopback PostgreSQL/API/worker/monitor, seeds synthetic businesses and staff, runs
all tests and the bounded authenticated active scan, evaluates the gate and stops
only its own processes. The run directory must not already exist. It retains the
private database and evidence for investigation; it does not delete old runs or
other services. Allow about 20 minutes and several GB of free space. No production
credentials are loaded, no Wompi calls occur, and no messages or paid models run.

For an already prepared environment, `security/run.py --help` lists explicit tool,
rule, wheelhouse and cache paths. `--layers` supports diagnostic partial runs;
omitting any mandatory layer always fails the final gate. The bootstrap also accepts
`--test-python` and `--native-tools` to reuse explicitly selected local installations.
A moved Python environment with broken shebangs is not a working scanner.

## Gate contract

- A real HTTP ordering/replay/authorization baseline must pass against the verified
  installed wheel. Every source/config/test/workflow input is hashed; mid-run edits fail.
- Every pytest case must complete successfully, with no skips and native process
  exit zero. The gate requires named milestone regression modules, browser cases,
  and recorded use of actual PostgreSQL fixtures and the installed package.
- Semgrep CE scans runtime Python/JS, deployment scripts, security and adversarial
  tools and the receiver. Every inventoried source file must be scanned with zero
  parser errors. The scanner version and three rule pack hashes are checked.
- Trivy scans source secrets/configuration and the **installed deployment dependency
  inventory**, including packaging tools. Its advisory database must be at most
  48 hours old, and every installed package must appear in the native report.
- ZAP must complete the 16 selected HTTP rules, export the complete bounded header
  history, and prove active requests received HTTP200 from both staff and customer
  protected routes. A successful seed/login alone is insufficient. Limits: two
  threads, LOW strength, three minutes per rule, twelve minutes total. Hitting a
  rule/time/export limit fails qualification. Session-changing staff routes are
  excluded from the scan to preserve the principal; dedicated session/CSRF tests
  cover them. Customer coverage uses scoped order capabilities, not full login.
- Any actionable finding without an exact, current review blocks. Reviews bind
  rule, path, severity, layer and full owning-file plus matched-code hash; require
  owner, rationale and expiry. Changes or expiry require another review. Native
  scanner findings remain visible; a reviewed finding is not silently erased.
- A PASS is local qualification only. It never authorizes real money or a deployment.

Native reports and command receipts stay in the private run directory. `evidence/`
contains summaries plus raw local static reports: inspect before sharing, especially
if a secret scanner finds a real secret. Never publish `private-*`, PostgreSQL data,
ZAP session databases or browser traces without review. The workflow uploads only an
explicit summary/test allowlist, not arbitrary scanner output or runtime secrets.

## CI and remaining release boundaries

`.github/workflows/commerce-security.yml` pins action revisions and has read-only
repository permission. It is **manual-only** to preserve the current $0 restriction.
It has not been dispatched, and required branch protection is not configured by
this change. Once a free runner is confirmed, the repository owner can enable PR
triggers and require the `qualify` job before merge/release. Do not treat an unrun
workflow as CI proof. Its Linux/Python target must match the production runtime lock.

Not covered by this gate: exhaustive penetration testing; paid Strix/model scans;
OCI/host-OS image vulnerabilities; production TLS/edge configuration; external
callbacks/DOM ZAP rules; real provider refunds; physical old phones; production
restore/paging operations. Existing M6a recovery qualification and Wompi sandbox
reports remain separate evidence. Real-money, production and unqualified refund
writes remain blocked.
