# ADR 0002: Use LiteRT.js And TFLite

Status: Accepted for future product phase.

Use LiteRT.js in the browser with a quantized `.tflite` artifact and float32 input/output boundaries. WASM is the baseline accelerator, WebGPU is accepted only when measured faster for the released model, and WebNN remains experimental.
