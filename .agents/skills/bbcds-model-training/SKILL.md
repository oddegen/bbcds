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

## Model Test Rules

- Apply the repository-wide rules in `AGENTS.md` and `docs/testing.md`; the
  items below are model-specific additions.
- Test contracts likely to regress: canonical labels, preprocessing, manifest
  validation, source isolation, deduplication, metrics, checkpoint recovery,
  evidence privacy, and executable report validation.
- Use small synthetic, benign fixtures. Never add protected examples, model
  weights, source metadata, or realistic harmful-content fixtures.
- Seed Python, NumPy, and TensorFlow randomness used by a test. Do not require a
  GPU, download pretrained weights, call remote datasets, or depend on a
  previous test.
- Exercise the real loader, validator, or training boundary where affordable.
  Replace only the expensive model or remote boundary with a minimal fake.
- Assert exact values for deterministic policy logic and schema fields. Use
  explicit tolerances for floating-point parity and metrics.
- Do not duplicate schema-only tests when an evidence-writing integration test
  already validates the generated report against that schema.
- Keep full training, dataset downloads, browser compatibility, and device
  benchmarks out of pull-request tests. Validate those in the protected release
  workflow and retain aggregate evidence.
