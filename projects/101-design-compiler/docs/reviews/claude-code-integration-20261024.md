# Codex ↔ Claude Code: verified integration and restaurant pilot

2026-10-24, America/Bogota. **REAL TWO-WAY COMMUNICATION VERIFIED.
PILOT RETAINED FOR HUMAN REVIEW; NOT MERGED.**

Codex remains the orchestrator. Claude Code made and revised an actual CSS
change in an isolated worktree. No generator, architecture redesign, runtime
dependency, framework, hosted service, commit, merge or push was introduced.

## Review

- [Live local restaurant pilot](http://127.0.0.1:4334/b3/candidate-01/).
- [Desktop before](../../.tools/claude-code/before-review/desktop-journal.png) / [after](../../.tools/claude-code/after-review/desktop-journal.png).
- [Mobile before](../../.tools/claude-code/before-review/mobile-journal.png) / [after](../../.tools/claude-code/after-review/mobile-journal.png).
- [Mobile continuation before](../../.tools/claude-code/before-review/mobile-journal-followup.png) / [after](../../.tools/claude-code/after-review/mobile-journal-followup.png).
- [Final actual patch](../evidence/claude-code/20261024/pilot/2-changes.patch).
- [Setup and reusable interface](../../tooling/claude-code/README.md).

Astro preview is bound to localhost only. Restart with `npm run preview --
--host 127.0.0.1 --port 4334` in the pilot worktree. Screenshot pixels stay in
ignored `.tools`; the native viewport images above were visually inspected.
Human aesthetic approval has not been collected.

## Inspected environment and installation

Commands execute on local Windows x64 / PowerShell / Node **v24.21.0**, not a
Linux/cloud container. This Codex session enforces workspace-write permissions
and read-only `.git`. User-pasted launch flags do not change its host policy.
Required host approvals were used; no permission-bypass flag was given to Claude.

The existing architecture is Astro **7.3.7**, TypeScript/Zod, shared semantic
modules, media gates and composition/CSS. The target is
`src/pages/b3/[candidate].astro` → `ExperienceComposition.astro` and B3 loaders.
Existing Raven/Impeccable, Superdesign geometry preparation, B3 materialization,
browser observers/audits and the local Edge/CDP adapter were inspected/reused.
No applicable root/ancestor AGENTS.md or Claude invocation/resume bridge existed.

The inspected official native installer verified its binary checksum and
installed stable Claude Code **2.1.308** at
`C:/Users/gabri/.local/bin/claude.exe`, outside the repository. No global PATH
change was needed. Installed help, login help, flag parsing and auth status
were checked. `--max-turns` is accepted but hidden from ordinary help.

An initial real unauthenticated invocation returned exit 1, `is_error: true`,
zero tokens/cost and `Not logged in · Please run /login`. Its session ID alone
was correctly rejected as success. Local raw evidence remains in
`.tools/claude-code/unauthenticated-probe.json`.

After the user's malformed PowerShell attempt, Codex launched the supported
login directly. The CLI exited with **Login successful**. Fresh doctor checks
confirmed `authenticated: true`, `authMethod: claude.ai`. No further login is
required here. Credentials remain in the Claude user profile, never copied to
the repository. On another Windows machine use the full command:

```powershell
& "C:\Users\gabri\.local\bin\claude.exe" auth login
```

## Working communication and isolation

`tooling/claude-code/bridge.mjs` implements `doctor`, `start`, `feedback`,
`status`. Explicit tasks select prompt, criteria, text context and authorized
image paths. Task/session IDs, status/errors, original CLI stdout/stderr,
context/attachment hashes, usage/cost estimates and real Git patches/status
are retained under `.tools/claude-code/<task-id>/`.

Calls use official `-p --output-format json`; follow-ups use the returned ID
with `--resume` in the same worktree, without forking. Exit/error envelopes and
exact session identity are validated. Claude receives the frontend role and
restricted file tools, with no shell/browser/network/subagent tools or implicit
MCP servers. Codex runs checks and owns review/integration decisions.

Tasks use detached Git worktrees from HEAD
`24c4301c2a36fc5a023d3cd695030afc13a47f09`, protected by per-task exchange locks.
Uncommitted root work is not stashed, committed or silently copied. Reviewed
text snapshots are explicitly disclosed as such. Git registration required
host execution and exact command-scoped `safe.directory` for this administrator-
owned repository; no global Git trust setting changed.

Root AGENTS.md now routes natural-language Claude collaboration requests to
this bridge. Configuration, task examples, preparation, checks, explicit
evidence export and recovery are documented in the runbook.

## Genuine two-way smoke test

[Original responses, prompts and SHA-256 index](../evidence/claude-code/20261024/smoke/index.json).
Both processes exited 0 with successful result envelopes, no permission denials,
and session **`97f9d17e-6de6-411f-bdd6-ac22759328f4`**.

1. Codex assigned B3 restaurant-home analysis with a memory marker. Claude
   returned source-specific findings, disclosed unread CSS and made no edits.
2. Codex challenged the out-of-scope Carta recommendation and requested actual
   destination verification plus HOME-only findings. The feedback did not
   restate the marker. Claude read additional source, distinguished demo
   reservations from real booking, revised scope, and recalled **cedar-731**.

These are actual installed Claude Code responses. Parser/transport tests use
explicit fixtures and are not treated as model communication evidence.

## Actual restaurant implementation and revision

[Original exchanges and patches](../evidence/claude-code/20261024/pilot/index.json).
Both successful implementation exchanges used session
**`da67f25f-35f7-4aaa-a0e5-03be21a29129`**.

Worktree: `.tools/claude-worktrees/restaurant-journal-pilot-01`.
Only **`src/design/experience-refinement.css`** is modified there. The primary
checkout's renderer remains unchanged.

Claude received existing code/criteria and current media-neutral screenshots
from the existing Superdesign geometry export, whose source HTML hash matched
the baseline. Licensed photo/video pixels and external reference screenshots
were not uploaded. Codex inspected real-media renders locally. Vision permission
does not imply training permission; no account training preference was inferred.

Claude implemented one lead journal story, supporting desktop rows and responsive
tablet/mobile hierarchy in the existing shared Immersive/Journal composition.
Codex reviewed the actual diff/renders and measured excess page length, then
sent one critique. Claude revised image ratios and row spacing in the same
session. Markup, story order, copy, notices, controls, hero, fonts, palette,
media, rights and semantic modules were preserved.

| Viewport | Baseline | First pilot | Revised pilot |
|---|---:|---:|---:|
| 1440 × 1000 | 4546px | 4940px | **4670px** |
| 390 × 844 | 5664px | 6195px | **6147px** |

Desktop reached the pacing goal. Mobile remains longer than baseline and above
the suggested 6000px goal; this is disclosed rather than called aesthetic
approval. The pilot remains a reviewable draft. An attempted third delegation
was rejected by the call/spend reservation guard before CLI execution.

## Actual checks

[Logs, receipts and verification index](../evidence/claude-code/20261024/verification/index.json).

- Bridge tests **6/6 PASS**: literal transport, diagnostic retention, timeout,
  limit validation, error-envelope rejection and exact-session matching.
- Final pilot check: **306 files; 0 errors/warnings/hints**.
- Final build: validation PASS, **168 pages**.
- Final tests: **423/424 PASS**. Sole failure: historical H8
  `tests/lock-files.test.ts`, expected `LOCK_AUDIT_FILE_MISMATCH`, actual
  `LOCK_BROWSER_MISMATCH`. Earlier B3/Superdesign reports document this same
  environment mismatch. No test/lock/threshold was suppressed or changed.
- Initial isolated tests also exposed an omitted private B3 silent-video
  derivative. Preparation was corrected to copy the existing verified file,
  without regeneration. Subsequent/final runs leave only historical H8.
- Existing `observeDepthExperience` / `auditDepthExperience` passed at
  **360, 390, 768, 1024, 1440px**, in closed and expanded-story states: no
  overflow, audited small controls or contrast failures. Minimum computed
  audited contrast approximately **4.94:1**.
- At all five widths, keyboard skip focus/activation, navigation Space/Escape
  and story expansion passed. No observed runtime exceptions. Reduced-motion
  local renders. Actual enhanced skip href/focus target was verified.
- Existing Impeccable context allowed scoped incumbent refinement; the final
  changed-CSS mechanical detector returned **[]**.
- All **168 HTML pages** retain non-CSS markup after removing only intended
  inline CSS and normalizing stylesheet hashed URLs. Client JS and **13
  image/video payloads** are byte-identical. No new request/dependency/media.
- Target HTML grows **4469 bytes**, entirely inline CSS: 75,921 → 80,390 bytes;
  external CSS remains 4294 bytes. These are build checks, not cold-network
  Core Web Vitals or full WCAG certification.

The historical H4 server lacked JS/video MIME types, so an initial capture
missed client behavior. A local source overlay now serves correct types,
records source/overlay hashes and retains the browser sandbox. Historical
adapter/lock bytes are unchanged. Initial failed attempts remain recorded.

Edge mobile full-page screenshots sometimes omit pizza-image tiles despite
decoded pixels and visible styles. Full-page attempts were not accepted as
complete visual evidence. Native viewport hero/journal captures show the
photos correctly and were viewed; these are the delivered images. The in-app
browser inventory was unavailable, so no separate CUA live check is claimed.

## Limits and costs

Defaults: **4 calls/task, requested 8 CLI turns/call, 180 seconds/call,
$0.50 estimated API cost/call, $2 full-cap reservations/task**. Pilot overrides:
**2 calls, requested 12 turns, 240 seconds, $0.75/call, $1.50/task**.
Failed/timed-out calls consume their reservation. No auto-retries/agent loops
or implied global cross-task cap. CLI estimated caps can overshoot on in-flight
requests and are not invoice guarantees.

Reported `num_turns` is retained: the smoke follow-up reports 10 despite a
requested 8. Do not treat that field as proof of an independently enforced
exact count. Process timeout, explicit call reservations and the official
estimated-cost cap provide independent bounds.

Responses resolved `sonnet` to **`claude-sonnet-5-5`**. The tested resume path's
`total_cost_usd` is session-cumulative, confirmed by summed model usage.
Latest estimates: **$0.1291859 smoke + $0.2863916 pilot ≈ $0.416 total**.
Do not sum all four cumulative envelopes. Auth is `claude.ai`; list-price
estimates do not assert incremental subscription charges. No plan/credits were
purchased. New bridge calls disable nonessential traffic without changing
account model-training consent.

The integration has no authentication blocker. Remaining qualifications are
mobile pacing, inherited H8 environment mismatch, uncertified cold-network/full
accessibility behavior, and human visual choice. No pilot changes were merged
into the primary checkout.

Official sources checked against installed behavior:
[CLI](https://code.claude.com/docs/en/cli-reference),
[authentication](https://code.claude.com/docs/en/authentication),
[setup](https://code.claude.com/docs/en/setup),
[data use](https://code.claude.com/docs/en/data-usage),
[costs](https://code.claude.com/docs/en/costs),
[Codex instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
