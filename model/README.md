# Model

This directory owns model training and release contracts. No model artifact is
bundled. Protected data, manifests, reports, logs, checkpoints, `.keras`, and
`.tflite` files must stay outside Git.

## Setup and Checks

```sh
uv sync
make check
```

For a computer without a suitable GPU, use
[`notebooks/train-colab.ipynb`](notebooks/train-colab.ipynb) with the
[training guide](../docs/model-training.md).

## Prepare and Train

```sh
uv run python -m bbcds_model.prepare_manifest \
  --dataset-root /path/to/protected/nsfw_dataset_v1 \
  --output /path/to/protected/dataset.csv \
  --profile deepghs-nsfw-detect \
  --seed 20260731

uv run python -m bbcds_model.train \
  --manifest /path/to/protected/dataset.csv \
  --resume
```

The manifest loader validates files, hashes, canonical labels, required splits,
and source-group isolation. The preparation profile verifies images, removes
exact duplicates, groups perceptual near-duplicates, excludes conflicting
groups, and writes an adjacent protected aggregate audit.

Training records the current Git commit. When running outside a Git checkout,
pass `--training-commit <commit>` to the training command.

## Finalize a Baseline

```sh
uv run python -m bbcds_model.finalize_baseline \
  --policy baseline-v1-policy.json \
  --manifest /path/to/protected/dataset.csv \
  --audit /path/to/protected/dataset.audit.json \
  --draft /path/to/protected/baseline-validation-draft.json \
  --checkpoint /path/to/protected/final.keras \
  --confusion-matrix /path/to/protected/validation-confusion-matrix.json \
  --approver project-owner \
  --output /durable/protected/baseline-validation-approved.json
```

The command binds every protected input to the pinned policy, validates the
report contract, recomputes manifest aggregates and source isolation, checks
the threshold and artifact references, and prints only aggregate evidence. It
refuses Git-worktree, temporary, or existing outputs and creates the approved
report with owner-only permissions (`0600`).

## Public Contracts

- `labels.json`: canonical label order.
- `dataset-manifest.schema.json`: protected training-manifest shape.
- `baseline-validation.schema.json`: validation and approval report.
- `baseline-v1-policy.json`: pinned hashes and gates for this release.
- `manifest.schema.json`: future TFLite release manifest.

The next milestone is a quantized MobileNetV3-Small TFLite artifact with label,
preprocessing, checksum, parity, LiteRT.js compatibility, and benchmark
evidence.
