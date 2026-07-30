# BBCDS Model Card

No model is bundled yet. This file is the public template for the protected
model card that must accompany the first approved baseline and every later
model release.

## Model Details

- Model name:
- Version:
- Status:
- Owner:
- Training commit:
- Dataset manifest hash:
- Model family: project-owned MobileNetV3-Small.
- Input contract: RGB, NHWC, `1 x 224 x 224 x 3`, float32 values in `[0,255]`.
- Runtime target: browser-only LiteRT.js in a dedicated worker.
- Release artifact: none in this repository yet.

## Uses

BBCDS targets local, browser-only video review for a narrow visual sexual-content
taxonomy. The public result shape is documented in `ARCHITECTURE.md`; confidence
is a documented heuristic until calibrated on a held-out video set.

Intended users:

- Product engineers integrating local video review.
- Reviewers validating model behavior against the accepted taxonomy.
- Release approvers checking evidence before artifact publication.

Direct use:

- Classify sampled video frames locally in the browser.
- Aggregate frame evidence into the documented public result shape.

Prohibited use:

- Do not use as universal inappropriate-content detection.
- Do not use for automated enforcement without human-review policy.
- Do not use for audio, text, violence, self-harm, drugs, hate, or identity
  classification.

## Taxonomy

The canonical label order is defined in `model/labels.json`:

- `Safe`
- `Suggestive`
- `Explicit`
- `Explicit Illustration`

Policy code must consume labels by name and must not rely on undocumented output
indexes.

## Training Data

Complete this section from the protected data card:

- Dataset name:
- Dataset version:
- Dataset manifest hash:
- Split counts:
- Label distribution:
- Collection summary:
- Exclusions:

Do not include protected media paths, source filenames, URLs, thumbnails, frame
pixels, or class probabilities.

## Training Procedure

Complete this section only from the protected training process:

- Backbone initialization:
- Head-training configuration:
- Fine-tuning configuration:
- Early-stopping criteria:
- Random seed handling:
- Hardware and runtime:
- Training duration:
- Checkpoint reference:

## Evaluation

Completed cards must summarize held-out evidence without exposing protected
records or raw class vectors:

- Evaluation split:
- Evaluation date:
- Sample count:
- Factors evaluated:
- Metrics:
- Macro F1:
- Per-class precision/recall/F1:
- Confusion matrix reference:
- Threshold rationale:
- Calibration status:
- Known failure modes:
- Approval status:

Detailed validation metadata belongs in a report that conforms to
`model/baseline-validation.schema.json`.

## Bias, Risks, And Limitations

Completed cards must document:

- Known collection and label bias.
- Under-supported factors or labels.
- Image-level versus video-level evaluation limits.
- Sparse-sampling risk.
- False-positive and false-negative consequences.
- Recommended mitigations.

## Governance

- Protected media and source identifiers must remain outside the public repo.
- Dataset entries must preserve source-group isolation across splits.
- Reviews must include provenance, label quality, annotator safety, and scope
  limitations.
- Public documentation may reference opaque hashes and protected artifact
  locations, but must not reveal sensitive content or source identities.

## Maintenance

- Update owner:
- Review cadence:
- Retraining trigger:
- Deprecation policy:
- Rollback artifact:

A later `.tflite` release must include checksums, preprocessing contract, parity
evidence, LiteRT compatibility evidence, benchmark evidence, and an updated
model manifest.
