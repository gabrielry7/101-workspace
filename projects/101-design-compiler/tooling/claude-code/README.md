# Codex ↔ Claude Code

Small, optional orchestration tool for the existing 101 Astro frontend. No SDK,
runtime dependency, server or replacement design pipeline. Codex delegates to
the real local Claude CLI, reviews its implementation and owns acceptance.

Verified on 2026-10-24: authenticated `claude.ai` login, two genuine smoke
exchanges in one session, then an isolated restaurant CSS implementation and
one same-session revision. [Evidence and review](../../docs/reviews/claude-code-integration-20261024.md).

## Setup

Use Node 24 and Git. On this Windows machine Node is available at
`.tools/node-v24.21.0-win-x64/node.exe`. Claude Code's official native installer
installed **2.1.308** at `%USERPROFILE%/.local/bin/claude.exe` on 2026-10-24
(Bogotá). The bridge discovers this location without a global PATH change.
For another installation, set `CLAUDE_CODE_BIN` to an executable path, not a
shell command. Installation does not authenticate the user.

```powershell
& "$env:USERPROFILE/.local/bin/claude.exe" auth login
# Complete Anthropic's browser sign-in; never paste tokens into the repo/chat.
node tooling/claude-code/bridge.mjs doctor
node --test tooling/claude-code/bridge.test.mjs
```

Use `auth login --console` only if you intend Console/API billing. Otherwise
the official login defaults to a Claude subscription. Account entitlement and
network access still apply. Credentials and Claude transcripts live in the
user profile, outside Git; the bridge never reads their files. Doctor records
only logged-in status and auth method, omitting account identity.

This session executes commands on local Windows x64, not a Linux/cloud
container. The surrounding Codex host still controls sandbox/network and
approval permissions. Installing Claude does not change those permissions.
Local CLI availability alone does not prove authenticated model access.

## Delegate and iterate

Create an explicit JSON task with a new lowercase/hyphen ID:

```json
{
  "id": "restaurant-spacing-01",
  "mode": "implement",
  "prompt": "Improve spacing and visual hierarchy on /b3/candidate-01/. Edit existing shared Astro/CSS only. Explain your choices and risks.",
  "context": [
    "src/pages/b3/[candidate].astro",
    "src/components/composition/ExperienceComposition.astro",
    "src/design/experience-refinement.css"
  ],
  "criteria": ["Preserve all semantic content and links", "No mobile overflow", "No new client dependencies or external media"],
  "attachments": [".tools/claude-code/baseline/desktop.png", ".tools/claude-code/baseline/mobile.png"],
  "attachmentAuthorization": "Record the applicable permission for model vision before including media"
}
```

Do not treat that example authorization as an actual media grant. Select
references and screenshots according to existing 101 rights records and the
user's authorized scope. Context paths are explicitly selected text snapshots;
screenshots are copied into the isolated worktree and supplied as paths for
Claude's Read tool. URLs may be described in the prompt, but Claude has no
network/browser tool; Codex must fetch and review references separately.

```powershell
node tooling/claude-code/bridge.mjs start path/to/task.json
node tooling/claude-code/bridge.mjs status restaurant-spacing-01
# Write concrete critique to a local UTF-8 text file, then:
node tooling/claude-code/bridge.mjs feedback restaurant-spacing-01 path/to/feedback.txt
```

`start` makes a detached Git worktree at `.tools/claude-worktrees/<id>` from
committed HEAD. It does not stash, commit, merge, push, reset or overwrite the
primary checkout. Uncommitted user work stays in place and is not silently
copied. Reviewed selected context snapshots may describe newer main-checkout
content; this is explicitly disclosed to Claude. Select any additional dirty
source changes individually before porting them into an experiment.
This Codex session's sandbox makes `.git` read-only, so registering a new
worktree requires an approved host execution. The local administrator-owned
repository also triggers Git's ownership check outside the sandbox; the bridge
passes an exact, command-scoped `safe.directory` for the root/worktree rather
than changing global Git trust. These host constraints also apply to `start`.

Each exchange invokes `claude -p --output-format json`; follow-ups use
`--resume <returned-session-id>` in the same worktree, with no fork flag. The
bridge rejects mismatched session IDs, nonzero exits, error responses,
unparseable responses, timeouts and absent session IDs. No agent-to-agent
loop runs automatically. Calls are explicitly initiated by Codex.

Artifacts under ignored `.tools/claude-code/<id>/` include task/context and
attachment hashes, prompts, original CLI JSON, stderr, state, per-call Git
patch and status. Newly created source files remain in the worktree and are
listed by status; inspect those files too. CLI responses include result text,
session ID, reported usage and estimated cost. A `responded` state means a
valid Claude response, not a verified design. Output is not automatically
committed to an evidence directory because prompts may contain private context.

## Limits and permissions

Defaults in `config.json`: **4 calls/task, 8 turns/call, 180 seconds/call,
$0.50 estimated API cost/call, $2/task**. A task's `limits` object may override
these with positive finite values. Default model is `sonnet`; no paid plan or
credits are purchased. API spend estimates differ from subscription quota or
actual invoices and the CLI can exceed its estimated cap on an in-flight
request. Leave budget headroom. Every attempt reserves its full call cap in
the task total, including failed/timed-out attempts; reported usage is retained
separately. No automatic retry. No global cross-task spend cap is implied.
`total_cost_usd` is session-cumulative on the tested resume path; the bridge
retains that reported estimate and computes an incremental estimate separately.
Do not sum successive cumulative totals. Subscription quota/billing is separate.
`--max-turns` is passed to Claude, and its reported `num_turns` is retained.
The smoke follow-up reported 10 despite a requested 8; do not interpret that
field as an independently enforced exact turn count. Outer call reservations,
process timeout and the CLI estimated-cost cap provide independent bounds.

The bridge requires official restricted mode, restricts tools to
Read/Glob/Grep for analysis and adds Edit/Write for implementation, explicitly
allows those tools, disables implicit MCP servers and user/project setting
sources, and supplies the frontend role directly. It gives Claude no Bash,
network, browser or agent-spawning tools. Restricted mode confines file tools
to its working directory and honors managed policies; it is not an OS security
boundary. No dangerous permission-bypass flag is used. Codex runs shell checks.
The CLI still maintains its ordinary user-profile authentication/session state.
New bridge invocations disable nonessential CLI traffic through its documented
environment setting. This does not change the account's model-training consent.

Per-task exclusive locks prevent simultaneous exchanges. A process-tree timeout
uses Windows taskkill, falling back to direct process termination if denied.
If the parent crashes, inspect the real processes and artifacts first; only
after confirming Claude stopped may an operator remove `exchange.lock` and
change `running` to `error` in local state. Reserved budget remains consumed.
Do not blindly resume a running or unknown session.

## Verification and restaurant pilot

```powershell
node tooling/claude-code/bridge.mjs start tooling/claude-code/smoke-task.json
# Inspect the real answer. Ask for the previously remembered marker WITHOUT
# restating it, and critique one concrete finding in a feedback text file.
node tooling/claude-code/bridge.mjs feedback restaurant-analysis-smoke feedback.txt
```

Require two successful original CLI responses, identical session IDs, a
relevant follow-up and actual memory of the marker. Preserve both transcripts.
Local transport tests are explicitly not evidence of a Claude exchange.
`probe.mjs` is a diagnostic real unauthenticated invocation; a rejection and
its returned session ID are explicitly not smoke-test success.

For a pilot, build the current baseline, then reuse the existing Edge adapter:

```powershell
npm run build
node tooling/claude-code/capture.mjs dist /b3/candidate-01/ .tools/claude-code/baseline
```

The capture wrapper overlays JavaScript/video/image MIME types on a local copy
of the historical H4 server so B3 module scripts execute, and bounds media
readiness. It records source/overlay hashes and retains the browser sandbox;
the frozen adapter/lock files are unchanged. Capture failures are not passes.
Delivered `desktop.png` / `mobile.png` are native hero viewports, with
`*-journal.png` and `*-journal-followup.png` section views plus scroll receipts.
This avoids observed Edge full-page mobile tile omissions; full-page captures
with missing photo regions are not accepted as complete visual evidence.

Start an implementation task only after successful smoke communication. Inspect
the diff and untracked files. In the retained worktree install locked existing
dependencies with `npm ci` if needed, then run `npm test`, `npm run check`,
`npm run build` and relevant B3/quality checks. Existing private B3 media inputs
may require explicitly authorized preparation; do not copy credentials or
invent replacement assets. Capture the worktree's built `dist` using the same
capture script and viewports. Review desktop/mobile images, keyboard navigation,
contrast, overflow, media gates and page/request/client-JS budgets using existing
101 audit tooling. Compare unchanged content/bindings and links. Send one
specific follow-up if warranted. Keep the worktree for user review; do not merge.

On this existing same-host B3 setup, `node tooling/claude-code/prepare-worktree.mjs
<task-id>` can instead materialize the existing hash-verified 14-file B2 package
and the already-reviewed B3 silent-video derivative, then junction the installed
Node/dependencies/pinned browser as the existing B3 materializer does. It copies
no credentials and downloads nothing. Run this after Claude's edit, inspect the
receipt, and use `node tooling/claude-code/verify-worktree.mjs <task-id> <label>`
to retain logs from the existing test/check/build commands. Failed checks stay
failed; the known historical H8 browser mismatch is not suppressed.

`node tooling/claude-code/export-evidence.mjs <task-id> <project-directory>`
explicitly exports selected task prompts/responses/patches and a SHA-256 index.
Review context before export; private runtime/media and Claude profile
transcripts are not exported. Runtime artifacts stay ignored until this action.

Official references checked during implementation:
[CLI flags and resume](https://code.claude.com/docs/en/cli-reference),
[authentication](https://code.claude.com/docs/en/authentication),
[native setup](https://code.claude.com/docs/en/setup),
[Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
Installed help and actual flag parsing are checked too: 2.1.308 accepts
`--max-turns` but hides it from ordinary `--help`.
