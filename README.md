# BBCDS

Browser-Based Content Detection System: a browser-only video moderation
prototype target for local frame sampling and local model inference.

## Overview

BBCDS is designed to accept a local video file or direct CORS-enabled video URL,
sample frames under bounded browser budgets, classify selected frames locally,
aggregate risk, and restrict playback when policy thresholds are crossed.

Implementation status is tracked in `docs/implementation-status.md`. Architecture and
accepted product decisions are documented in `ARCHITECTURE.md` and `docs/adr`.

The implementation must remain browser-only: no server-side video processing,
no external inference API, and no committed harmful-content fixtures.

## Requirements

- Node `24`
- pnpm `11.17.0`

## Quickstart

```sh
pnpm install
pnpm dev
```

## Verification

```sh
pnpm check
pnpm test:e2e
```

`pnpm test:e2e` runs the Chromium browser project, matching CI. If Chromium is
missing, install it with:

```sh
pnpm exec playwright install chromium
```

For full local browser coverage, install every Playwright browser and run:

```sh
pnpm exec playwright install
pnpm test:e2e:full
```

## Commands

- `pnpm dev`: start the Vite dev server.
- `pnpm format:check`: check Prettier formatting.
- `pnpm lint`: run oxlint and ESLint.
- `pnpm typecheck`: run TypeScript project checks.
- `pnpm test:unit`: run Vitest once.
- `pnpm build`: typecheck and build the static app.
- `pnpm check`: run the main quality gate.
- `pnpm test:e2e`: run Chromium Playwright tests.
- `pnpm test:e2e:full`: run all configured Playwright projects.

## Repository Map

- `src/App.tsx` and `src/index.css`: current UI shell.
- `src/*.test.tsx`: unit and component tests.
- `tests/e2e`: Playwright browser tests.
- `model`: model contract, canonical labels, and manifest schemas.
- `docs/adr`: accepted architecture decision records.
- `docs/testing.md`: testing strategy and fixture policy.
- `docs/implementation-status.md`: mutable implementation status.
- `AGENTS.md`: agent operating rules and required checks.

## Architecture

The product target and technical contract are documented in `ARCHITECTURE.md`.
Accepted product decisions live in `docs/adr`.

Additional documentation:

- `docs/implementation-status.md`: current implementation status.
- `docs/testing.md`: testing strategy and fixture policy.
- `docs/benchmarking.md`: benchmark methodology and report requirements.
- `docs/model-card.md`: model scope and limitations.
- `docs/data-card.md`: protected dataset governance template.
- `PRIVACY.md`: browser-only privacy requirements.
- `SECURITY.md`: security reporting and dependency expectations.
- `CONTRIBUTING.md`: local contribution workflow.

## Stack

- Runtime: static Vite React TypeScript app.
- Testing: Vitest, Testing Library, Playwright, axe.
- Quality: TypeScript strict mode, oxlint, ESLint, Prettier.
