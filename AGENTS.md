# AGENTS.md

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

## Future Product Invariants

- One frame/classification in flight.
- Request and scan identifiers on async worker communication.
- Explicit cleanup for workers, object URLs, ImageBitmap instances, tensors, and cached resources.
- No negative early exit before required coverage.
- Sampling, label-order, preprocessing, quantization, or threshold changes require tests and benchmark evidence.
