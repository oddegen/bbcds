# Implementation Status

This is the source of truth for current progress. `ARCHITECTURE.md` describes
the stable target rather than implementation state.

## Complete

- Repository foundation, CI, browser shell, model contracts, and training tools.
- Protected manifest preparation and resumable MobileNetV3-Small training.
- `baseline-v1` research approval with public model/data cards, a pinned policy,
  and a protected approved validation report retained outside Git.
- Local-file decoding, bounded anchor/refinement sampling, cancellable analysis
  orchestration, a dedicated module worker, protected result views, and the
  approved-manifest/model loading boundary.

## Next: Model Artifact

Produce a quantized `.tflite` artifact and retain checksums, preprocessing and
label contracts, Keras/TFLite parity, LiteRT.js compatibility, and benchmark
evidence. The current `0.43` threshold remains exploratory.

The protected conversion, parity, Chromium/WASM compatibility, benchmark, and
approval tooling is implemented. The browser flow uses a clearly marked demo
classifier when `/models/model-manifest-approved.json` is absent; demo results
never clear playback. The real release remains pending because the hash-pinned
dataset snapshot must be reacquired for representative calibration and
full-validation parity. Do not mark the artifact complete until the protected
manifest is approved.

## Not Implemented

Operational inference with a real artifact, direct URL analysis, calibrated
video-level confidence, cross-browser release coverage, and product benchmarks
remain pending. Do not present the demo flow as an operational detector.

Protected media, manifests, reports, logs, checkpoints, and model artifacts
must remain outside Git. Public evidence is limited to aggregate metrics,
opaque hashes, policies, contracts, and approved limitations.
