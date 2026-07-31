# Model Training

BBCDS trains a protected image classifier baseline. The public repository
contains reproducible tooling and evidence schemas, but not protected media,
training manifests, checkpoints, raw probabilities, or model artifacts.

## Workflow

1. Create a protected CSV manifest outside Git using
   `model/examples/training-manifest.example.csv` as the shape reference.
2. Keep labels exactly aligned with `model/labels.json`.
3. Use source-grouped splits: one `source_id` must appear in only one split.
4. Run `uv run python -m bbcds_model.train --manifest /protected/dataset.csv`
   from `model/`.
5. Review the generated `baseline-validation-draft.json` under the ignored run
   directory.
6. Confirm the report is compatible with
   `model/baseline-validation.schema.json`.
7. Copy only approved public-safe summaries into `docs/model-card.md` and
   `docs/data-card.md`.

## Contract

- Architecture: MobileNetV3-Small.
- Input: RGB, `1 x 224 x 224 x 3`, float32, `[0,255]`.
- Preprocessing: aspect-preserving letterbox to 224 by 224; MobileNetV3
  preprocessing remains inside the Keras model.
- Output: four float32 probabilities ordered as `Safe`, `Suggestive`,
  `Explicit`, `Explicit Illustration`.

## Current Boundary

This tooling stops at Keras training and protected validation evidence. TFLite
export, post-training quantization, metadata embedding, LiteRT.js compatibility
testing, browser inference, and video sampling belong to later milestones unless
an ADR changes the roadmap.
