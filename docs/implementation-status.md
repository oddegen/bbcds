# Implementation Status

This is the source of truth for current progress. `ARCHITECTURE.md` describes
the stable target rather than implementation state.

## Complete

- Repository foundation, CI, browser shell, model contracts, and training tools.
- Protected manifest preparation and resumable MobileNetV3-Small training.
- `baseline-v1` research approval with public model/data cards, a pinned policy,
  and a protected approved validation report retained outside Git.

## Next: Model Artifact

Produce a quantized `.tflite` artifact and retain checksums, preprocessing and
label contracts, Keras/TFLite parity, LiteRT.js compatibility, and benchmark
evidence. The current `0.43` threshold remains exploratory.

## Not Implemented

Model loading, browser inference, workers, video scanning, adaptive sampling,
playback restriction, direct URL analysis, and product benchmarks remain
pending. Do not present the current shell as an operational detector.

Protected media, manifests, reports, logs, checkpoints, and model artifacts
must remain outside Git. Public evidence is limited to aggregate metrics,
opaque hashes, policies, contracts, and approved limitations.
