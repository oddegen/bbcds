# Repository Guide

BBCDS is a static Vite/React prototype for future browser-only video
moderation. Read `docs/implementation-status.md` before assuming a milestone is
implemented. Stable constraints live in `ARCHITECTURE.md`; testing policy lives
in `docs/testing.md`.

## Commands

- Install: `pnpm install`
- Develop: `pnpm dev`
- Main quality gate: `pnpm check`
- Chromium smoke test: `pnpm test:e2e`
- Model checks: `cd model && make check`

Use Node 24, pnpm 11, and the repository's configured tools. Install all
Playwright browsers only when `pnpm test:e2e:full` is required.

## Hard Boundaries

- Keep inference browser-only. Do not add a backend, external inference,
  uploads, analytics, service workers, or cross-origin isolation without
  explicit approval.
- Do not commit protected media, filenames, URLs, thumbnails, frame pixels,
  class probabilities, manifests, reports, logs, checkpoints, or model files.
- Ask before adding model/runtime dependencies or artifacts.
- Follow `ARCHITECTURE.md` and accepted ADRs. Record a new ADR only when an
  architecture decision changes.

## Change Discipline

- Search the repository before adding a file, abstraction, test, or command.
- Prefer the smallest direct change that satisfies a current requirement. Do
  not scaffold future milestones or add compatibility for unreleased internals.
- Keep one source of truth per topic and link to it instead of repeating it.
- Add a new file only for a distinct owned boundary or durable contract.
- Preserve unrelated work in a dirty tree and avoid broad formatting churn.

## Testing

- Extend the closest test and assert observable behavior through the narrowest
  stable boundary. Do not mirror the source tree or add tests for coverage.
- Do not assert source text, private calls, exact markup, or incidental counts.
  Artifact inspection is reserved for security/privacy properties that runtime
  tests cannot prove, such as omitted secrets or notebook outputs.
- Use benign, deterministic fixtures. Never add protected-content fixtures.
- For rendered UI changes, verify the real flow with Playwright in desktop and
  mobile viewports when layout or interaction can change.
- Run the focused check first, then `pnpm check`; run `model/make check` for
  model changes and Playwright for rendered frontend changes.

Before handoff, inspect `git status`, `git diff --stat`, and `git diff --check`.
Remove generated artifacts, redundant tests, stale documentation, and unrelated
formatting changes.
