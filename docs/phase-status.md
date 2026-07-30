# Phase Status

This file is the source of truth for mutable implementation status. Keep
`README.md` and `ARCHITECTURE.md` focused on stable project and architecture
information.

## Current Status

- Phase 0: complete. Repository foundation, model contract scaffold, docs,
  checks, CI, and agent guardrails are present.
- Phase 1: pending. No trained baseline model exists yet.
- Phase 2 and later: pending.

The browser detection pipeline is not implemented yet. Do not assume model
loading, video scanning, worker inference, adaptive sampling, playback
restriction, benchmark collection, or direct CORS URL mode exists until the
matching phase is marked complete here and has tests.

## Phase Exit Gates

- Phase 0: `pnpm check` succeeds and docs, CI, and agent guardrails are present.
- Phase 1: protected training process produces public-safe model/data cards and
  approved validation evidence.
- Phase 2: quantized `.tflite` artifact passes label, preprocessing, parity,
  checksum, and LiteRT compatibility gates.
- Phase 3: a local benign video returns the public result shape without any
  inference network request.
- Phase 4: cancel/restart tests pass and late worker responses are ignored by
  scan/request ID.
- Phase 5: deterministic unit tests cover anchors, coverage, dedupe, refinement,
  caps, and early-exit rules.
- Phase 6: unsafe mock results pause, mute, and cover playback; CORS
  success/failure paths pass without a proxy.
- Phase 7: benchmark reports include accelerator, device/browser metadata, video
  properties, sample counts, timings, long tasks, and bundle/model budgets.
- Phase 8: known limitations, threshold evidence, benchmark methodology, and
  deliverables map to tested code or measured reports.

## Public-Safe Evidence Rules

Do not commit protected data, media, filenames, URLs, thumbnails, frame pixels,
class probabilities, checkpoints, `.tflite` files, or model artifacts.

Public commits may contain schemas, empty templates, aggregate metrics, opaque
hashes, public-safe evidence summaries, and approved limitations.
