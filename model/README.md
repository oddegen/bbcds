# Model

This directory owns the model contract for the future LiteRT.js moderation runtime.

No model artifact is bundled yet. Do not commit training data, protected dataset manifests, source media, extracted frames, thumbnails, benchmark exports, checkpoints, or `.tflite` files.

## Training Tooling

The `src/bbcds_model` package contains public-safe training code for the
protected baseline process. It expects a local CSV manifest with paths to
protected image files and trains an ImageNet-pretrained MobileNetV3-Small
classifier with the repository's canonical four-class taxonomy.

Set up the Python environment from this directory:

```sh
uv sync
```

For a clean rebuild:

```sh
rm -rf .venv
uv sync --python 3.11
```

Run ML checks:

```sh
make check
```

Run a protected training job:

```sh
make train MANIFEST=/path/to/protected/dataset.csv
```

The training command records the current Git commit in the protected validation
report. If the command runs outside a Git checkout, pass
`--training-commit <commit>` through `uv run python -m bbcds_model.train`.

The training manifest is a protected input and must not be committed. A
public-safe shape example lives at `examples/training-manifest.example.csv`.
Required columns are:

- `path`
- `label`
- `source_id`
- `split`
- `media_type`
- `license`
- `sha256`

Relative paths are resolved from the manifest file's directory. The loader
verifies file existence, SHA-256 hashes, canonical labels, required splits, and
source-group isolation before training.

Training outputs under `runs`, checkpoints, reports, `.keras`, and `.tflite`
files are ignored because they may contain protected evidence or model
artifacts. Public commits may contain only approved aggregate summaries, opaque
hashes, and completed card text.

Each completed training run writes an ignored `baseline-validation-draft.json`
and protected aggregate evidence under the run directory. Review that draft
against `baseline-validation.schema.json` before copying approved summaries into
public model and data cards.

The public-safe evidence contract is defined by:

- `labels.json`: canonical label order.
- `dataset-manifest.schema.json`: protected dataset metadata shape.
- `baseline-validation.schema.json`: protected validation report shape.
- `manifest.schema.json`: future `.tflite` release manifest shape.

Future releases must provide a quantized MobileNetV3-Small `.tflite` artifact with float32 input/output boundaries, checksums, label order, preprocessing contract, model card, data card, parity evidence, LiteRT compatibility evidence, protected evaluation evidence, and benchmark evidence.

The canonical label order is defined in `labels.json`. Policy code must not rely on undocumented output indexes.
