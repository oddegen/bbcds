# AGENTS.md

## Agent Quickstart

- Read `docs/implementation-status.md` before making implementation-status assumptions.
- Install dependencies with `pnpm install`.
- Run the app with `pnpm dev`.
- Use `pnpm check` as the primary handoff validation.
- Use `pnpm test:e2e` for the default Chromium browser smoke test. Run `pnpm exec playwright install chromium` first if Chromium is missing.
- Use `pnpm test:e2e:full` only when all Playwright browsers are installed with `pnpm exec playwright install`.
- Edit the UI shell in `src/App.tsx` and `src/index.css`.
- Add unit tests beside source files as `src/*.test.tsx`.
- Add browser tests in `tests/e2e`.
- Keep model contracts in `model`.
- Record accepted architecture decisions in `docs/adr` and testing strategy in `docs/testing.md`.

## Ground Rules

- Use official setup, install, and generation commands where available.
- Follow `ARCHITECTURE.md` and `docs/adr` for product decisions.
- Keep inference browser-only: no server-side video processing and no external inference API.
- Ask before adding network calls, analytics, service workers, cross-origin isolation headers, model/runtime dependencies, model artifacts, or external processing paths.
- Do not commit harmful-content fixtures, source video files, thumbnails, frame pixels, filenames, URLs, or class probabilities.

## Skill Usage

- Use a skill when the user names it, the task clearly matches its domain, or it materially improves correctness for the requested change.
- Read the selected skill's `SKILL.md` before acting, then follow its workflow instead of improvising a parallel process.
- Prefer the most specific applicable skill. Do not load unrelated skills just because they are available.
- State which skill is being used when it changes the implementation, validation, or final reporting workflow.
- If multiple skills apply, use them in task order: build or refactor first, then validate or audit.

### Frontend Testing Debugging

Use `frontend-testing-debugging` for rendered frontend work: UI bugs, interaction failures, responsive layout issues, console/runtime errors, visual QA, local app smoke tests, and targeted improvements to visible app surfaces.

When using it:

- Define the target flow before validation, for example `app loads -> first meaningful screen renders -> primary interaction works`.
- Use the Browser plugin path when it is available. If it is not available, use Playwright and record that Browser was unavailable.
- For non-trivial UI changes, verify page identity, nonblank render, absence of framework error overlays, console health, screenshot evidence, and at least one interaction proof.
- Check desktop and one mobile-sized viewport when the change affects layout, wrapping, spacing, or responsiveness.
- A passing build is not enough for a rendered UI change; validate the actual browser behavior.

### React Best Practices

Use `react-best-practices` when writing, reviewing, or refactoring React components, state/effect logic, data flow, client-side fetching, bundle-sensitive code, or performance-sensitive UI.

When using it:

- Prefer direct imports over broad barrel imports.
- Lazy-load heavy modules only when the feature is activated.
- Keep effect dependencies primitive and stable where practical.
- Do not define components inside components.
- Derive state during render when possible instead of mirroring it through effects.
- Avoid memoization unless it removes measurable work or prevents a real render problem.
- Apply browser-only constraints from `ARCHITECTURE.md`; ignore server-side recommendations that do not fit this static Vite app.

### Skill Selection Examples

- UI bug, visual regression, local browser smoke test, or layout issue: use `frontend-testing-debugging`.
- React component/API refactor or performance-sensitive React work: use `react-best-practices`.
- New visual screen or substantial redesign: use `frontend-app-builder`, then `frontend-testing-debugging`.
- Accessibility or design audit requested by the user: use `web-design-guidelines`.
- Docs, prose, voice, or tone audit requested by the user: use `writing-guidelines`.

## Required Checks

Before finishing code changes, run the most targeted check plus:

- `pnpm format:check`
- `pnpm lint`
- `pnpm typecheck`
- `pnpm test:unit`
- `pnpm build`

Run `pnpm check` before broader handoff when practical.

## Test Authoring

- Before writing a test, search the existing suite and identify the behavior,
  risk, and test layer already covering the area. Extend the closest test when
  that keeps the failure focused.
- Add a test when a behavior, contract, security boundary, or prior defect is
  likely to regress. Do not add tests only to increase coverage or mirror the
  source tree.
- Test through the narrowest stable public boundary that proves the behavior.
  Prefer unit tests for pure logic, integration tests for owned boundaries, and
  browser tests for critical user flows.
- Assert observable outcomes and invariants, not private calls, source text,
  exact markup structure, generated file ordering, or incidental counts.
- A defect fix should include a regression test that fails without the fix when
  practical.
- Keep tests deterministic and hermetic. Seed randomness, use temporary
  directories, control time, and do not depend on test order, external
  networks, shared accounts, or machine-specific state.
- Use real production code with the smallest realistic fixture. Mock only
  external or expensive boundaries; do not mock the behavior under test.
- Avoid duplicate coverage. Extend or parameterize the closest existing test,
  and share setup only after genuine repetition appears.
- Keep one clear reason for failure per test. Prefer focused assertions over
  broad snapshots. Use tolerances for floating-point and timing-sensitive
  values.
- Do not test static schemas, configuration text, or generated artifacts when
  an executable path already validates the same contract. Artifact tests are
  justified for security, compatibility, or release gates that runtime tests
  cannot cover.
- After adding stronger coverage, remove tests that became redundant or
  implementation-coupled. Do not retain both versions for reassurance.
- Run the targeted test first, then the required repository checks. Document
  any check that cannot run and why. In the handoff, state the behavior and risk
  covered rather than only reporting the test count.

## Future Product Invariants

- One frame/classification in flight.
- Request and scan identifiers on async worker communication.
- Explicit cleanup for workers, object URLs, ImageBitmap instances, tensors, and cached resources.
- No negative early exit before required coverage.
- Sampling, label-order, preprocessing, quantization, or threshold changes require tests and benchmark evidence.
