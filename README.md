# BBCDS

Browser-Based Content Detection System.

BBCDS is a browser-only video moderation prototype. This repository is currently at Phase 0: a production-oriented Vite React TypeScript foundation with strict checks, browser testing, CI, security guidance, architecture records, and agent instructions.

The detection pipeline is not implemented yet. Model release, LiteRT.js model loading, video scanning, worker inference, adaptive sampling, playback restriction, benchmark collection, and direct CORS URL mode are future product phases defined in `ARCHITECTURE.md`.

## Commands

- `pnpm install`
- `pnpm dev`
- `pnpm format:check`
- `pnpm lint`
- `pnpm typecheck`
- `pnpm test:unit`
- `pnpm build`
- `pnpm check`
- `pnpm test:e2e`

## Stack

- Runtime: static Vite React TypeScript app.
- Package manager: pnpm `11.17.0`.
- Node line: `24` LTS.
- Testing: Vitest, Testing Library, Playwright, axe.
- Quality: TypeScript strict mode, oxlint, ESLint, Prettier.

## Architecture

The product target and technical contract are documented in `ARCHITECTURE.md`. Accepted product decisions live in `docs/adr`.

Agent and contributor guidance:

- `AGENTS.md`: operating rules, required checks, and implementation guardrails.
- `docs/testing.md`: testing strategy and fixture policy.
- `docs/benchmarking.md`: benchmark methodology and report requirements.
- `docs/model-card.md`: model scope and limitations.
- `docs/data-card.md`: protected dataset governance template.
- `model/`: model contract, canonical labels, and future artifact manifest schema.
- `PRIVACY.md`: browser-only privacy requirements.
- `SECURITY.md`: security reporting and dependency expectations.

The implementation must remain browser-only: no server-side video processing, no external inference API, and no committed harmful-content fixtures.
