# Quantity and pickup capacity contracts

These are composable merchant settings, not hardcoded industry types. A bakery may
combine finite batches, made-to-order items and pickup windows. A salon's retail
stock can use finite quantities; service-resource booking needs additional work.

| Setting | Meaning | Admission rule |
|---|---|---|
| Quantity blank / `remaining=null` | Do not count units | Check item availability; no stock decrement |
| Quantity zero or positive | Available-to-sell units, not total physical units | Atomic conditional decrement; never negative |
| Item sold out | Merchant explicitly disables item | Reject new admissions |
| Ordering disabled | Merchant pauses orders | Reject new admissions; preserve accepted orders |
| Scheduled pickup | Merchant hours, lead time and order count per slot | Lock only the business and UTC slot being allocated; enforce capacity |
| Combined quantity and pickup | Both constraints apply | Commit all or roll back all |

An untracked quantity does not promise infinite production capacity. Scheduled
pickup counts **orders**, not units, prep minutes, stylists or chairs. No new
hidden demand pause is introduced. Existing technical request limits remain.

## Concurrent edits and checkout

Admission holds shared profile/item locks until its local transaction commits.
Manager settings edits take conflicting exclusive locks. If admission wins, its
order remains valid; the edit applies afterward. If the edit wins, admission sees
the new value before accepting. Quantity updates also check the version supplied
by staff: a stale count cannot overwrite stock consumed by a concurrent order.
A count entered by staff means **remaining available to sell**.

Finite quantity still serializes competing updates to the same stock row.
Scheduled pickup serializes the same slot through a PostgreSQL transaction-level
advisory lock; unrelated slots can run concurrently. Profile/policy read locks
coordinate edits, including creation of the first policy. Item locks are narrowed
to item rows rather than also locking their joined category/menu.

Reducing a slot's capacity preserves existing commitments, closes it to further
admissions when full, and does not cancel existing orders. Exact checkout retries
recover their order rather than allocating again.

Cancellation frees a pickup slot under the existing non-cancelled-order count.
It **does not automatically restore product quantity**: prepared goods may no
longer be resellable. Automatic hold expiry/restocking and unresolved-payment stock
reuse are not implemented capabilities. Staff must explicitly recount stock.

## Explicit future capabilities

Resource/duration/buffer overlap prevention, table allocation, workload-weighted
capacity, per-location/variant allocation and automatic inventory hold expiry are
not established by these tests. Existing reservation records do not implement
those guarantees. They require separate contracts and acceptance tests.

## Repeatable verification

`tests/test_capacity_profiles.py` requires real PostgreSQL via
`COMMERCE_PAYMENT_TEST_DATABASE_URL`; its fixture creates and drops unique test
schemas. With SQLite these concurrency cases explicitly skip and do not count as
passes. The operations tests also exercise the SQLite fallback separately.

For paired 30/100-user measurements, build a retained baseline wheel from the
previous revision, then run (from this project, with the harness toolchain ready):

```sh
COMMERCE_TOOLCHAIN=/path/to/toolchain /path/to/toolchain/venv/bin/python \
  adversarial/profile_benchmark.py \
  --baseline-wheel /path/to/retained-baseline.whl \
  --output /tmp/fresh-capacity-profile-run
```

The runner builds current source, uses two API workers plus a recovery worker,
creates fresh PostgreSQL schemas/provider ledgers for each block, runs untracked,
finite and combined scheduled profiles twice with reversed build order, captures
request/resource/SQL-lock timing and audits actual stock/order/payment effects.
Only loopback synthetic services are allowed. It stops its owned processes on exit.
Config files contain synthetic credentials: keep them private. Native receipts and
sanitized summaries are evidence; the presence of this command is not a test pass.
Shared-host/tmpfs results do not establish production capacity or storage durability.

P05 adds optional `--profiles scheduled` for focused paired qualification. P07
operation targets live in `adversarial/latency_contract.py` and are saved before
execution. Correctness and latency outcomes are separate; unmet revised latency
targets produce a nonzero benchmark exit even when every order is correct.
The harness uses a short **5-second payment lease** by default; the application
uses30seconds. Set `--payment-lease-seconds 30` for that application default, and
retain the chosen value when comparing builds. A short-lease stress run does not
qualify production settings. Targeted admission now validates/counts one requested
slot through the same calendar rules; public seven-day calendar output is retained.
