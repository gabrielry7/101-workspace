# 101 collaboration

Codex is the primary orchestrator and owns architecture, requirements, code
review, verification and integration decisions. Preserve uncommitted user work.
Do not merge or push agent work automatically.

When asked to ask Claude, collaborate with Claude Code, or iterate with Claude
on an existing page, use the real CLI bridge documented in
[tooling/claude-code/README.md](tooling/claude-code/README.md).
Run its doctor first, create an explicit scoped task JSON, invoke `start`,
inspect its actual response and worktree diff, then use `feedback` with the
same task ID. Never substitute a Codex subagent or mocked response for Claude.
If authentication fails, report the exact blocker and user login command.

Claude acts as a frontend design/development specialist. Keep changes in the
existing shared Astro/CSS renderer and semantic business modules. Preserve
media gates, fictional labels, credits, navigation, accessibility, mobile
usability, reduced motion and performance. Reuse existing design references
and `scripts/lib/local-browser.ts` for screenshots. Do not create a new
generator, pipeline, framework or service.

Before delegation, review selected context and media vision permissions;
exclude credentials and unrelated private material. Claude worktrees start at
committed HEAD. Disclose differences from a dirty working tree; never copy
uncommitted user changes without reviewing and explicitly selecting them.
Each task has bounded calls, turns, time and estimated spend. Codex runs
builds, tests, browser/accessibility/performance checks, reviews screenshots,
and retains the implementation for user review. A successful CLI response is
not evidence that a design passes quality checks.
