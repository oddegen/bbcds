# Architecture

BBCDS targets local video moderation in a static browser application. Current
progress lives in `docs/implementation-status.md`; accepted decisions live in
`docs/adr`.

## Product Contract

The future product accepts a local video or direct CORS-enabled video URL,
samples frames under bounded budgets, classifies them locally, aggregates risk,
and restricts playback when policy thresholds are crossed.

```json
{
  "contains_inappropriate_content": true,
  "confidence": 0.87
}
```

The visual taxonomy is `Safe`, `Suggestive`, `Explicit`, and
`Explicit Illustration`. Audio and unrelated safety categories are out of
scope.

## Accepted Architecture

- Static Vite/React application with no application backend.
- Project-owned MobileNetV3-Small with RGB `224x224` input.
- Quantized TFLite release with float32 input/output boundaries.
- LiteRT.js in a dedicated module worker; WASM is the baseline accelerator.
- Hybrid bounded sampling with anchors, coverage, and suspicious-region
  refinement.

## Hard Invariants

- No video, frame, score, or inference request leaves the browser.
- Exactly one frame/classification is in flight.
- Worker messages carry scan and request identifiers; stale responses are
  ignored.
- Negative results require whole-video coverage. Positive early exit requires
  confirming evidence.
- Workers, URLs, bitmaps, tensors, timers, controllers, and cached resources
  have explicit cleanup paths.
- Public fixtures contain no source media, thumbnails, frame pixels, filenames,
  URLs, or raw class probabilities.
- Label order, preprocessing, quantization, sampling, and threshold changes
  require tests and benchmark evidence.

## Dependency Direction

UI depends on feature orchestration; orchestration depends on domain contracts
and infrastructure. Domain code does not import React, DOM APIs, LiteRT.js,
workers, or browser globals. Worker code does not import UI modules.

Do not add a model artifact, runtime dependency, public detection API, worker
protocol, sampling implementation, or restriction flow without its matching
tests and documentation. Use an ADR when an accepted architecture decision
changes.
