# Model

This directory owns the model contract for the future LiteRT.js moderation runtime.

No model artifact is bundled yet. Do not commit training data, protected dataset manifests, source media, extracted frames, thumbnails, benchmark exports, checkpoints, or `.tflite` files.

Future releases must provide a quantized MobileNetV3-Small `.tflite` artifact with float32 input/output boundaries, checksums, label order, preprocessing contract, model card, data card, parity evidence, LiteRT compatibility evidence, protected evaluation evidence, and benchmark evidence.

The canonical label order is defined in `labels.json`. Policy code must not rely on undocumented output indexes.
