# S03 policy and optional loyalty boundary

Run `adversarial/security_expansion.py` on a fresh owned output directory. It builds
and installs the actual application wheel, creates private loopback PostgreSQL,
runs a baseline order, stops its own application for the explicit optional schema
upgrade, then restarts two API workers with loyalty configuration enabled. No
existing database is upgraded. Public incentive enrollment remains disabled.

`loyalty_security.py` uses the existing trusted Stage3 simulated checkout and
normalized refund-observation seams to create earned-point histories. Preview and
allocation attacks go through actual HTTP staff authorization and the installed
application. This proves neither public customer identity nor Wompi partial refunds.
No external payment, messaging, model, or scanning service is invoked.

The installed ZAP rule inventory is mapped by `zap_policy.py`. Every rule has a
reason; unknown or missing selected rules fail setup rather than silently changing
coverage. The expanded profile adds directory browsing (0), hidden files (40035),
and user-agent differences (10104). Native progress includes request counts;
`Complete` with zero messages is reported as `NOT RUN`. In particular GET-for-POST
(10058) is supplemented by actual GET-with-JSON requests to both POST-only loyalty
routes, asserting HTTP405 and unchanged database state. That independent test is
not relabeled as native ZAP execution.

References: [ZAP rule registry](https://github.com/zaproxy/zaproxy/blob/main/docs/scanners.md),
[GET for POST](https://www.zaproxy.org/docs/alerts/10058/),
[hidden files](https://www.zaproxy.org/docs/alerts/40035/),
[user-agent fuzzer](https://www.zaproxy.org/docs/alerts/10104/).

Boundaries: LOW strength, two scanner threads, three-minute maximum per rule,
twelve-minute maximum scan, explicit native completion/export checks. OAST,
metadata callbacks, redirects, other database engines and unavailable TLS-edge
checks stay excluded with reasons. DOM browser testing, full login/session scans,
resource-exhaustion testing and real deployment ingress remain separate work.
Optional configuration mutation routes are excluded from this bounded scan to
protect its frozen published fixtures; existing configuration regression tests
run on PostgreSQL. Only optional preview and refund allocation receive new active
scanner fixtures in this slice.

Every denied request must leave the protected financial and loyalty tables
unchanged. Positive preview must remain hypothetical. Exact allocation replay and
four simultaneous submissions must converge on one allocation and a reconciled
wallet. A changed replay must be rejected. Generated bodies retain their adversarial
values; only URL identifiers are rebound to real records. These checks supplement,
rather than substitute for, the scanner's native alerts.

The command is intentionally not a full release-stack rerun. `--no-scan` is for
reproduction and always leaves S03 incomplete. Raw alerts remain visible; source-bound,
unexpired reviews can qualify known low findings but cannot erase them.
