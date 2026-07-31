# Benchmarking

No product benchmark exists yet.

The model-artifact release gate includes a record-only Chromium/WASM baseline:
runtime initialization, model compilation, 10 warmups, and 50 measured
inferences over a deterministic benign synthetic tensor. It records aggregate
minimum, p50, p95, and maximum inference time with runtime, browser, platform,
artifact hash, and tensor-contract metadata. It has no latency pass threshold
and is not a product or video-pipeline performance claim.

Future benchmark reports must include app version, model version, model artifact, quantization mode, device/browser metadata, accelerator, video metadata, sample counts, timings, long tasks, optional memory, and the final decision.

Do not claim performance without recorded device, browser, accelerator, codec, resolution, duration, and sample count. WebGPU must be accepted only when measured end-to-end frame cost is better than the WASM baseline for the same model and browser profile.
