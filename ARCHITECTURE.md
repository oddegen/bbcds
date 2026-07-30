# Architecture

BBCDS is a browser-only video moderation prototype. This file documents the
stable product target, technical contract, and architecture constraints.
Mutable implementation status lives in `docs/phase-status.md`.

## Product Target

The target product will accept a local video file or direct CORS-enabled video URL, sample frames under bounded budgets, classify selected frames locally, aggregate risk, and restrict playback when the configured policy threshold is crossed.

The service should return:

```json
{
  "contains_inappropriate_content": true,
  "confidence": 0.87
}
```

The selected model scope is visual sexual content represented by the four-class taxonomy: `Safe`, `Suggestive`, `Explicit`, and `Explicit Illustration`. Gore, general violence, self-harm, drugs, hate symbols, unsafe text, and audio moderation are out of scope unless a future ADR changes the model or policy.

## Status Tracking

Current implementation status is tracked in `docs/phase-status.md`.

Do not assume model loading, video scanning, worker inference, adaptive
sampling, playback restriction, benchmark collection, or direct CORS URL mode
exists until the matching product phase is marked complete there and has tests.

## Accepted Baseline

- Single repository with a Vite React TypeScript app and isolated model contract/tooling area.
- Static deployment; no application backend.
- Browser-only inference in the future product phase.
- Project-owned MobileNetV3-Small, 224 by 224 input, when model work begins.
- Quantized `.tflite` artifact with float32 input/output boundaries.
- LiteRT.js runtime with WASM baseline, measured WebGPU acceleration, and WebNN as experimental only.
- Dedicated module worker owns LiteRT.js, preprocessing, model lifecycle, and tensor lifecycle.
- One frame/classification in flight.
- Hybrid adaptive sampling with anchors, coverage, refinement, and bounded caps.
- Vitest, Playwright, accessibility checks, CI, and benchmark artifacts.

## Hard Invariants

- Inference must stay browser-only: no server-side video processing, external inference API, frame upload, score upload, analytics path, or object-store upload.
- Worker communication must include request and scan identifiers so late async results cannot mutate a newer scan.
- Exactly one frame/classification may be in flight.
- Positive early exit is allowed only with confirming evidence; negative early exit is not allowed before required whole-video coverage completes.
- Workers, object URLs, `ImageBitmap` instances, tensors, timers, abort controllers, and cached resources must have explicit cleanup paths.
- Public tests and fixtures must not commit harmful-content videos, source video files, thumbnails, frame pixels, filenames, URLs, or class probabilities.
- Sampling, label-order, preprocessing, quantization, or threshold changes require tests and benchmark evidence.
- Model artifacts or runtime dependency changes require documentation updates and an ADR when they change an accepted decision.

## Implementation Boundary

Do not add model artifacts, worker protocol code, sampling logic, video extraction, public detection APIs, or restriction UI without matching tests and documentation updates.

## Dependency Direction

When implementation starts, dependencies must flow inward:

- UI may depend on feature orchestration and shared UI.
- Feature orchestration may depend on domain contracts and infrastructure clients.
- Domain logic must not import React, DOM APIs, LiteRT.js, workers, or browser globals.
- Worker implementation must not import React or UI modules.

Future layers should map to these responsibilities:

- UI: React components, accessibility, progress, restriction controls, and user-facing errors.
- Feature orchestration: scan state, cancellation, scheduling coordination, and UI-facing use cases.
- Domain: pure sampling, aggregation, policy, state transitions, and typed contracts.
- Infrastructure: video metadata, frame extraction, worker client, storage/cache adapters, and performance recording.
- Worker implementation: LiteRT.js, accelerator selection, preprocessing, model lifecycle, tensor lifecycle, and classification.

ESLint boundaries should enforce these rules once feature folders exist.

## Roadmap

- Phase 0: repository foundation and model contract scaffold. Exit gate: `pnpm check` succeeds and docs/CI/agent guardrails are present.
- Phase 1: model baseline. Exit gate: protected training process produces model/data cards and approved validation evidence.
- Phase 2: `.tflite` release artifact. Exit gate: quantized artifact passes label, preprocessing, parity, checksum, and LiteRT compatibility gates.
- Phase 3: file scan MVP. Exit gate: a local benign video returns the public result shape without any inference network request.
- Phase 4: robust worker lifecycle. Exit gate: cancel/restart tests pass and late worker responses are ignored by scan/request ID.
- Phase 5: adaptive sampling. Exit gate: deterministic unit tests cover anchors, coverage, dedupe, refinement, caps, and early-exit rules.
- Phase 6: restriction UX and direct CORS URL mode. Exit gate: unsafe mock results pause/mute/cover playback and CORS success/failure paths pass without a proxy.
- Phase 7: performance hardening. Exit gate: benchmark reports include accelerator, device/browser metadata, video properties, sample counts, timings, long tasks, and bundle/model budgets.
- Phase 8: evaluation and submission. Exit gate: known limitations, threshold evidence, benchmark methodology, and deliverables map to tested code or measured reports.
