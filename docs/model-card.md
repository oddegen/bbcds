# Model Card

No model is bundled yet.

The accepted future prototype model is a project-owned MobileNetV3-Small model with 224 by 224 input, released as a quantized `.tflite` artifact for LiteRT.js.

The canonical label order is defined in `model/labels.json`:

- `Safe`
- `Suggestive`
- `Explicit`
- `Explicit Illustration`

The policy scope is limited to visual sexual content represented by those labels. It must not be described as universal inappropriate-content detection.

Future model releases must include a completed model card, data card, checksums, label/preprocessing contract, parity evidence, protected evaluation evidence, and benchmark evidence.
