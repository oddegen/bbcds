# BBCDS Model Card: MobileNetV3-Small Baseline V1

## Model Details

- Model name: BBCDS MobileNetV3-Small.
- Version: `baseline-v1`.
- Status: approved image-level research baseline; production calibration and
  video-level performance are not approved.
- Owner: BBCDS project.
- Training commit: `0b92626ea18e`.
- Dataset manifest hash:
  `46c18a29ac0436b6b7dfe72e9919cc6ad49fd29309bbe5bc3851b2ad3e122e95`.
- Checkpoint hash:
  `eaa36900095460cf8c1ccb78c968381277d61279cc69583d42e31d676fab2692`.
- Release policy: `model/baseline-v1-policy.json`.
- Approved report reference:
  `protected://model-runs/baseline-v1-validation-approved.json`.
- Approved report hash:
  `d7abe560e12346ce967e0ab70d488a55f31ebe1ded7d5f0e99a1b47176418d16`.
- Model family: project-owned MobileNetV3-Small initialized from ImageNet weights.
- Input contract: RGB, NHWC, `1 x 224 x 224 x 3`, float32 values in `[0,255]`.
- Runtime target: browser-only LiteRT.js in a dedicated worker.
- Release artifact: none. TFLite conversion and compatibility are the next milestone.

## Uses

BBCDS targets local, browser-only video review for a narrow visual
sexual-content taxonomy. This baseline only establishes image-level evidence;
it does not establish video sampling or policy performance.

Intended uses:

- Research and model-artifact conversion for the BBCDS prototype.
- Image-level evaluation against the accepted taxonomy.
- Future local classification of sampled video frames after artifact release.

Prohibited uses:

- Universal inappropriate-content detection or automated enforcement without
  human-review policy.
- Audio, text, violence, self-harm, drugs, hate, or identity classification.
- Production claims based on the exploratory threshold or image-only evidence.

## Taxonomy

Outputs use the canonical order from `model/labels.json`:

1. `Safe`
2. `Suggestive`
3. `Explicit`
4. `Explicit Illustration`

Consumers must use labels by name rather than undocumented output indexes.

## Training Data

- Dataset: research snapshot prepared from `deepghs/nsfw_detect`.
- Version: unversioned upstream snapshot accessed for the 2026-07-31 run.
- Accepted records: 27,803 from 28,000 scanned images.
- Splits: 22,242 train; 2,781 validation; 2,780 test.
- Label distribution: 11,134 Safe; 5,543 Suggestive; 5,559 Explicit;
  5,567 Explicit Illustration.
- Exclusions and grouping: 191 exact duplicates, 8 conflicting-cluster records,
  367 accepted near-duplicate clusters, 0 corrupt records, and 0 policy exclusions.
- Source groups: 27,395 with source-grouped split isolation.

The upstream repository declares MIT, but provenance, consent, and training
rights are not documented for every underlying image. This model is therefore
restricted to a research baseline and is not commercially cleared.

## Training Procedure

- Backbone initialization: ImageNet-pretrained MobileNetV3-Small.
- Input preparation: aspect-preserving RGB letterbox to 224 by 224; model-side
  MobileNetV3 preprocessing; float32 `[0,255]` input.
- Head training: batch size 64, up to 15 epochs, AdamW learning rate `3e-4`,
  weight decay `1e-4`, and class weighting.
- Fine-tuning: final 30 backbone layers eligible for training, batch-normalization
  layers frozen, up to 20 epochs, AdamW learning rate `1e-5`, and weight decay `1e-5`.
- Training controls: seed `20260731`; best-checkpoint restoration; early stopping
  after five unimproved validation-loss epochs; learning-rate reduction after two.
- Hardware/runtime: Google Colab GPU workflow; exact accelerator was not retained.
- Duration: not retained in the public-safe run metadata.

## Evaluation

- Evaluation date: 2026-07-31.
- Scope: image-level held-out validation for threshold selection and per-class evidence.
- Validation records/source groups: 2,781 / 2,773.
- Macro F1: `0.8644`.
- Binary policy at exploratory threshold `0.43`: precision `0.8277`, recall
  `0.9021`, F1 `0.8633`.
- Separate held-out test accuracy: `0.8640`; no approved test-set calibration or
  per-class report was retained.

| Label                 | Support | Precision | Recall |     F1 |
| --------------------- | ------: | --------: | -----: | -----: |
| Safe                  |   1,114 |    0.9088 | 0.8411 | 0.8737 |
| Suggestive            |     554 |    0.7934 | 0.9495 | 0.8644 |
| Explicit              |     556 |    0.9545 | 0.8309 | 0.8885 |
| Explicit Illustration |     557 |    0.7993 | 0.8654 | 0.8310 |

- Confusion-matrix reference: protected evidence hash
  `54bca56e23543360e098244a35751d3ebd6267cf4823668fc7d1b418a2da675b`.
- Calibration: exploratory. Threshold `0.43` is not a production calibration claim.
- Approval: completed by `project-owner` as an image-level research baseline
  for model-artifact conversion. The threshold remains exploratory.

## Bias, Risks, And Limitations

- Collection provenance, consent, demographic coverage, geography, and source-domain
  coverage are incompletely documented.
- Labels inherit upstream ambiguity and were not independently re-annotated under a
  documented multi-reviewer BBCDS protocol.
- Safe recall of `0.8411` indicates false-positive risk; Explicit recall of
  `0.8309` indicates false-negative risk.
- Image-level evaluation does not measure compression, motion blur, transitions,
  temporal context, sparse sampling, or video-level aggregation.
- Illustration performance does not establish coverage of every synthetic or
  stylized visual domain.

Mitigations are human review, conservative research-only use, protected error
analysis, held-out video evaluation, explicit threshold calibration, and parity
and browser benchmarks before any product claim.

## Governance And Maintenance

- Protected media, manifests, logs, reports, and model artifacts remain outside Git.
- Update owner and release approver: BBCDS project owner.
- Review cadence: at every dataset, taxonomy, preprocessing, threshold, or artifact change.
- Retraining triggers: material data-quality improvements, documented distribution
  shift, or failure to meet later video-level evidence gates.
- Deprecation: supersede this baseline when a fully evidenced replacement is approved.
- Rollback artifact: protected Keras checkpoint identified by the hash above.

A later `.tflite` release requires quantization, checksums, preprocessing and
label contracts, Keras/TFLite parity, LiteRT.js compatibility, and benchmark evidence.
