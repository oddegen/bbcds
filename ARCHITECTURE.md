# Architecture

BBCDS is a browser-only video moderation prototype. This file is the agent-facing source of truth for the target product and technical contract.

## Product Target

The target product will accept a local video file or direct CORS-enabled video URL, sample frames under bounded budgets, classify selected frames locally, aggregate risk, and restrict playback when the configured policy threshold is crossed.

The public detection result must expose exactly:

- `contains_inappropriate_content`
- `confidence`

The selected model scope is visual sexual content represented by NSFWJS classes. Gore, general violence, self-harm, drugs, hate symbols, unsafe text, and audio moderation are out of scope unless a future ADR changes the model or policy.

## Current Implementation Status

The repository is currently at Phase 0: application foundation, documentation, checks, and CI. The video-detection pipeline is not implemented yet.

Do not assume model loading, video scanning, worker inference, adaptive sampling, playback restriction, benchmark collection, or direct CORS URL mode exists until the matching product phase is implemented and tested.

## Accepted Baseline

- Single Vite React TypeScript application.
- Static deployment; no application backend.
- Browser-only inference in the future product phase.
- NSFWJS MobileNetV2, 224 by 224 input, when model work begins.
- Dedicated module worker owns TensorFlow.js/model work.
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
- Sampling or threshold changes require tests and benchmark evidence.
- Model assets or runtime dependency changes require documentation updates and an ADR when they change an accepted decision.

## Implementation Boundary

Do not add model assets, worker protocol code, sampling logic, video extraction, public detection APIs, or restriction UI without matching tests and documentation updates.

## Dependency Direction

When implementation starts, dependencies must flow inward:

- UI may depend on feature orchestration and shared UI.
- Feature orchestration may depend on domain contracts and infrastructure clients.
- Domain logic must not import React, DOM APIs, TensorFlow.js, workers, or browser globals.
- Worker implementation must not import React or UI modules.

Future layers should map to these responsibilities:

- UI: React components, accessibility, progress, restriction controls, and user-facing errors.
- Feature orchestration: scan state, cancellation, scheduling coordination, and UI-facing use cases.
- Domain: pure sampling, aggregation, policy, state transitions, and typed contracts.
- Infrastructure: video metadata, frame extraction, worker client, storage/cache adapters, and performance recording.
- Worker implementation: TensorFlow.js, NSFWJS, backend selection, preprocessing, model lifecycle, and classification.

ESLint boundaries should enforce these rules once feature folders exist.

## Roadmap

- Phase 0: repository foundation. Exit gate: `pnpm check` succeeds and docs/CI/agent guardrails are present.
- Phase 1: file scan MVP. Exit gate: a local benign video returns the public result shape without any inference network request.
- Phase 2: robust worker lifecycle. Exit gate: cancel/restart tests pass and late worker responses are ignored by scan/request ID.
- Phase 3: adaptive sampling. Exit gate: deterministic unit tests cover anchors, coverage, dedupe, refinement, caps, and early-exit rules.
- Phase 4: restriction UX. Exit gate: unsafe mock results pause/mute/cover playback and remain keyboard accessible.
- Phase 5: direct CORS URL mode. Exit gate: CORS-enabled media succeeds and blocked origins fail without a proxy.
- Phase 6: performance hardening. Exit gate: benchmark reports include backend, device/browser metadata, video properties, sample counts, timings, long tasks, and bundle/model budgets.
- Phase 7: evaluation and submission. Exit gate: known limitations, threshold evidence, benchmark methodology, and deliverables map to tested code or measured reports.
