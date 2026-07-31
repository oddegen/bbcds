---
name: bbcds-model-training
description: Use for BBCDS training, dataset manifests, validation evidence, model/data cards, or model-release preparation.
---

# BBCDS Model Training

Read `docs/implementation-status.md`, `ARCHITECTURE.md`, `model/README.md`, and
the relevant model contract before changing model work.

## Scope

- Baseline work covers Keras training, protected evidence, and model/data cards.
- Model-artifact work covers TFLite conversion, quantization, parity, checksums,
  and LiteRT.js compatibility.
- Do not add browser inference, workers, sampling, or video scanning during
  either model phase.

## Protected Evidence

- Never commit media, paths, filenames, URLs, raw probabilities, manifests,
  reports, logs, checkpoints, `.keras`, or `.tflite` files.
- Public evidence is limited to schemas used as durable contracts, aggregate
  summaries, opaque hashes, policies, and approved limitations.
- Use canonical labels from `model/labels.json` and validate source-group split
  isolation before training or approval.
- Keep preprocessing RGB, letterboxed `224x224`, float32 `[0,255]` unless a new
  evidenced release changes the contract.

## Keep the Release Path Lean

- `baseline-v1-policy.json` pins release-specific evidence; the baseline report
  schema is the approval contract. Do not create a schema for every internal
  JSON output.
- Add an evidence schema only when multiple producers/consumers need a durable
  versioned boundary. Otherwise validate the required fields at the owning CLI.
- Extend the nearest test. Prefer one end-to-end synthetic evidence fixture over
  separate schema, helper, and implementation tests for the same gate.
- Test canonical labels, isolation, hashes, aggregates, report validity,
  checkpoint recovery, and public-output privacy with small benign fixtures.
- Keep dataset downloads, pretrained weights, GPUs, full training, conversion,
  and device benchmarks out of pull-request tests.
