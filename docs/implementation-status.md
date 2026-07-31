# Implementation Status

This file is the source of truth for mutable implementation status. Keep
`README.md` and `ARCHITECTURE.md` focused on stable project and architecture
information.

## Current Status

- Foundation: complete. Repository foundation, model contract scaffold, docs,
  checks, CI, and agent guardrails are present.
- Model training workflow: ready. Protected manifest preparation, resumable
  Keras training, aggregate evidence generation, and the Colab runbook are
  implemented and tested.
- Model baseline: pending. No trained baseline model exists yet.
- Model artifact and later product work: pending.

The browser detection pipeline is not implemented yet. Do not assume model
loading, video scanning, worker inference, adaptive sampling, playback
restriction, benchmark collection, or direct CORS URL mode exists until the
matching milestone is marked complete here and has tests.

## Exit Gates

- Foundation: `pnpm check` succeeds and docs, CI, and agent guardrails are present.
- Model baseline: protected training process produces public-safe model/data cards and
  approved validation evidence.
- Model artifact: quantized `.tflite` artifact passes label, preprocessing, parity,
  checksum, and LiteRT compatibility gates.
- File scan MVP: a local benign video returns the public result shape without any
  inference network request.
- Worker lifecycle: cancel/restart tests pass and late worker responses are ignored by
  scan/request ID.
- Adaptive sampling: deterministic unit tests cover anchors, coverage, dedupe, refinement,
  caps, and early-exit rules.
- Restriction UX and URL mode: unsafe mock results pause, mute, and cover playback; CORS
  success/failure paths pass without a proxy.
- Performance hardening: benchmark reports include accelerator, device/browser metadata, video
  properties, sample counts, timings, long tasks, and bundle/model budgets.
- Evaluation and submission: known limitations, threshold evidence, benchmark methodology, and
  deliverables map to tested code or measured reports.

## Public-Safe Evidence Rules

Do not commit protected data, media, filenames, URLs, thumbnails, frame pixels,
class probabilities, checkpoints, `.tflite` files, or model artifacts.

Public commits may contain schemas, empty templates, aggregate metrics, opaque
hashes, public-safe evidence summaries, and approved limitations.
