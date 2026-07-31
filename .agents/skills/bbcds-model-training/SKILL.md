---
name: bbcds-model-training
description: Use when adding or changing BBCDS model training, dataset manifests, baseline validation evidence, model cards, data cards, or model-release preparation. Keeps work public-safe and scoped to the current product milestone.
---

# BBCDS Model Training

Before model-training changes, read `docs/implementation-status.md`,
`ARCHITECTURE.md`, `model/README.md`, and the relevant schema in `model/`.

## Keep Scope Tight

- Baseline training: Keras model training, protected validation evidence, and
  model/data cards. Do not add `.tflite`, LiteRT.js, browser worker, or video
  scanning.
- Model release: `.tflite` export, quantization, parity, metadata, checksums,
  and LiteRT compatibility.
- Product runtime: browser inference, workers, sampling, restriction UX, and
  benchmarks.

## Public-Safe Rules

Never commit protected media, filenames, URLs, thumbnails, frame pixels, raw
probabilities, checkpoints, `.keras`, `.tflite`, or sensitive manifests. Commit
only schemas, templates, code, aggregate summaries, opaque hashes, and approved
limitations.

## Implementation Rules

- Prefer small, named modules over scaffolding a full ML platform.
- Use canonical labels from `model/labels.json`; do not invent snake-case
  variants in repo contracts.
- Validate source-group split isolation before training.
- Keep preprocessing contract RGB, letterboxed `224x224`, float32 `[0,255]`.
- Add tests only for contracts likely to regress: labels, manifest validation,
  leakage, metrics, and schema-compatible reports.
