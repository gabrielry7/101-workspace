# Live 101 commerce browser test plan

Seed: `tests/seed.spec.ts`. All targets are explicit loopback HTTP URLs and use the
built application with real PostgreSQL. No fake API response bodies are allowed.
Delay/drop tests use `route.fetch()` and the actual backend response. Every scenario
gets a new browser context and unique synthetic customer/key. No test is skipped.

1. Create a customer order through the rendered catalog; verify capability access
   and authenticated staff retrieval from the actual server.
2. Delay the create response after server processing and double-click submit;
   require one request/order.
3. Drop the response after real commit; retry in the page; require identical body,
   idempotency key and resulting order.
4. Submit one explicit checkout intent concurrently from two tabs; require one
   authoritative resource and successful replay.
5. Commit, drop response, reload, repeat the same purchase; require recovery of the
   original order. Current missing persistence must produce FAIL, not skip.
6. Disconnect the browser during submit; reconnect/retry; require the same key.
7. Hold actual food quote, empty cart, release quote; require zero displayed total.
8. Hold actual delivery quote for A, change to B, release; reject stale quote and
   emit no order request.
9. Deny both browser storages and remove randomUUID; ordinary ordering still works.
10. Delay an authenticated business-A response, select business B; discard A's
    records/actions and prove B's protected endpoint actually returns data.
11. Verify a supposed business-A staff authority cannot read B. The existing global
    token currently lacks this feature and must remain an explicit release failure.

Healer constraint: diagnose failing selectors/setup separately from business
failures. Never use fixme/skip/expected-failure to hide reload or tenant failures.
