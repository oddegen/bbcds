# Testing

## Current Checks

- Unit tests verify the app renders.
- Playwright verifies the app loads and has no obvious accessibility violations.
- `check:model` verifies model assets are handled intentionally.
- `check:bundle` verifies the built app stays under the initial JS budget.

## Future Product Phase

Add deterministic tests for sampling, aggregation, worker stale-response handling, cancellation, backend fallback, network privacy assertions, and resource cleanup.
