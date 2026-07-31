# BBCDS

BBCDS is a browser-only video moderation prototype. The target product samples
video frames and runs local model inference without uploading video or scores.

The current repository contains the UI shell, model-training tools, and an
approved image-level research baseline. Browser inference and video scanning
are not implemented. See [implementation status](docs/implementation-status.md)
and [architecture](ARCHITECTURE.md).

## Development

Requirements: Node 24 and pnpm 11.17.0.

```sh
pnpm install
pnpm dev
```

Main checks:

```sh
pnpm check
pnpm test:e2e
```

Install Chromium first if Playwright reports it missing:

```sh
pnpm exec playwright install chromium
```

Model setup and commands are documented in [model/README.md](model/README.md).

## Repository Map

- `src`: current React shell.
- `tests/e2e`: browser smoke tests.
- `model`: model contracts and protected-workflow tooling.
- `docs/adr`: accepted architecture decisions.
- `docs/model-card.md` and `docs/data-card.md`: baseline evidence and limits.
- `PRIVACY.md` and `SECURITY.md`: product boundaries.
- `AGENTS.md`: concise repository rules for coding agents.
