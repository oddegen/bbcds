# Model

This directory owns model training and release contracts. No model artifact is
bundled. Protected data, manifests, reports, logs, checkpoints, `.keras`, and
`.tflite` files must stay outside Git.

## Setup and Checks

```sh
uv sync --frozen
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
- `baseline-v1-artifact-policy.json`: pinned conversion, parity, and runtime gates.
- `manifest.schema.json`: approved TFLite artifact manifest.

## Export And Approve An Artifact

The release tooling is implemented, but no artifact is approved or bundled.
Run conversion in Colab so the gated dataset remains ephemeral and the full
validation split is available:

```sh
uv run python -m bbcds_model.export_artifact \
  --policy baseline-v1-artifact-policy.json \
  --approved-baseline-report /durable/protected/baseline-validation-approved.json \
  --checkpoint /durable/protected/final.keras \
  --manifest /path/to/protected/dataset.csv \
  --output-directory /durable/protected/artifact-release-1.0.0
```

After transferring the artifact to durable protected local storage, run the
real Chromium/WASM check from the repository root:

```sh
pnpm model:compat -- \
  --policy model/baseline-v1-artifact-policy.json \
  --artifact /durable/protected/bbcds-mobilenetv3-small-1.0.0.tflite \
  --output /durable/protected/litert-compatibility.json
```

Approve only the exact artifact covered by both reports:

```sh
uv run python -m bbcds_model.finalize_artifact \
  --policy baseline-v1-artifact-policy.json \
  --artifact /durable/protected/bbcds-mobilenetv3-small-1.0.0.tflite \
  --conversion-report /durable/protected/artifact-conversion-parity.json \
  --compatibility-report /durable/protected/litert-compatibility.json \
  --approved-baseline-report /durable/protected/baseline-validation-approved.json \
  --approver project-owner \
  --output /durable/protected/model-manifest-approved.json
```

All outputs must be new paths outside the Git worktree and system temporary
storage. Commands print aggregate evidence only and refuse to overwrite output.
