# BBCDS

BBCDS is a browser-only video moderation prototype. The target product samples
video frames and runs local model inference without uploading video or scores.

The current repository contains the local-file scanning flow, model-pluggable
worker runtime, model-training tools, and an approved image-level research
baseline. Without an approved model artifact, scans finish in a clearly marked
demo state and never reveal playback. See
[implementation status](docs/implementation-status.md) and
[architecture](ARCHITECTURE.md).

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

### Install an approved browser model

Keep both files outside Git and place them under the ignored `public/models/`
directory before building:

```text
public/models/model-manifest-approved.json
public/models/{modelId}-{semanticVersion}.tflite
```

The worker derives the artifact filename from the manifest, verifies its size
and SHA-256, validates the browser tensor contract, and then enables LiteRT/WASM
inference. A missing manifest uses demo mode; a present but invalid release
fails closed.

## Repository Map

- `src`: React flow, analysis controller, worker, and domain contracts.
- `tests/e2e`: browser smoke tests.
- `model`: model contracts and protected-workflow tooling.
- `docs/adr`: accepted architecture decisions.
- `docs/model-card.md` and `docs/data-card.md`: baseline evidence and limits.
- `PRIVACY.md` and `SECURITY.md`: product boundaries.
- `AGENTS.md`: concise repository rules for coding agents.
