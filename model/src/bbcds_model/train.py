"""Command-line entrypoint for protected baseline training."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight
from tensorflow import keras

from bbcds_model.classifier import build_classifier
from bbcds_model.constants import CLASS_TO_ID, LABELS
from bbcds_model.dataset import make_all_datasets
from bbcds_model.evaluate import classification_report
from bbcds_model.manifest import count_source_groups, sha256_file, split_manifest
from bbcds_model.validation_report import (
    build_baseline_validation_report,
    protected_reference,
    write_report,
)

DEFAULT_SEED = 20260731
ResumeStage = Literal["new", "head", "fine-tune"]


def set_reproducibility(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


def calculate_class_weights(manifest: pd.DataFrame) -> dict[int, float]:
    training = manifest[manifest["split"] == "train"].copy()
    classes = np.arange(len(LABELS))
    weights = compute_class_weight(
        class_weight="balanced",
        classes=classes,
        y=training["label"].map(CLASS_TO_ID).to_numpy(),
    )
    return {int(class_id): float(weight) for class_id, weight in zip(classes, weights, strict=True)}


def build_callbacks(
    output_dir: Path,
    *,
    monitor: str = "val_loss",
    resume: bool = False,
) -> list[keras.callbacks.Callback]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return [
        keras.callbacks.BackupAndRestore(
            backup_dir=output_dir / "training-state",
            delete_checkpoint=True,
        ),
        keras.callbacks.ModelCheckpoint(
            output_dir / "best.keras",
            monitor=monitor,
            save_best_only=True,
        ),
        keras.callbacks.EarlyStopping(monitor=monitor, patience=5, restore_best_weights=True),
        keras.callbacks.ReduceLROnPlateau(monitor=monitor, factor=0.3, patience=2, min_lr=1e-7),
        keras.callbacks.CSVLogger(output_dir / "training.csv", append=resume),
        keras.callbacks.TensorBoard(log_dir=output_dir / "tensorboard"),
    ]


def resolve_training_commit(repository_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short=12", "HEAD"],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    if result.returncode == 0 and len(commit) >= 7:
        return commit
    raise RuntimeError("Unable to resolve git commit; pass --training-commit explicitly")


def collect_predictions(
    model: keras.Model,
    dataset: tf.data.Dataset,
) -> tuple[np.ndarray, np.ndarray]:
    labels: list[np.ndarray] = []
    probabilities: list[np.ndarray] = []

    for images, batch_labels in dataset:
        labels.append(batch_labels.numpy())
        probabilities.append(model.predict(images, verbose=0))

    return np.concatenate(labels).astype("int32"), np.concatenate(probabilities)


def find_backbone(model: keras.Model) -> keras.Model:
    nested_models = [layer for layer in model.layers if isinstance(layer, keras.Model)]
    if len(nested_models) != 1:
        raise RuntimeError("Expected exactly one nested backbone model")
    return nested_models[0]


def restore_training_model(
    *,
    output_dir: Path,
    resume: bool,
) -> tuple[keras.Model, keras.Model, ResumeStage]:
    head_model_path = output_dir / "head-final.keras"
    fine_tune_model_path = output_dir / "fine-tune-final.keras"
    existing = [path for path in (head_model_path, fine_tune_model_path) if path.exists()]

    if existing and not resume:
        raise FileExistsError("Training checkpoints exist; pass --resume or choose a new output directory")
    if resume:
        checkpoints: tuple[tuple[Path, ResumeStage], ...] = (
            (fine_tune_model_path, "fine-tune"),
            (head_model_path, "head"),
        )
        for path, stage in checkpoints:
            if not path.is_file():
                continue
            try:
                model = keras.models.load_model(path)
                return model, find_backbone(model), stage
            except (OSError, TypeError, ValueError):
                continue
        if existing:
            raise RuntimeError("No valid completed training checkpoint could be loaded")

    model, backbone = build_classifier()
    return model, backbone, "new"


def write_baseline_evidence(
    *,
    output_dir: Path,
    manifest_path: Path,
    manifest: pd.DataFrame,
    validation_ds: tf.data.Dataset,
    model: keras.Model,
    final_model_path: Path,
    training_commit: str,
) -> dict[str, Any]:
    validation_labels, validation_probabilities = collect_predictions(model, validation_ds)
    metrics = classification_report(validation_labels, validation_probabilities)
    validation_manifest = split_manifest(manifest, "validation")

    protected_evidence_dir = output_dir / "protected-evidence"
    protected_evidence_dir.mkdir(parents=True, exist_ok=True)
    confusion_matrix_path = protected_evidence_dir / "validation-confusion-matrix.json"
    confusion_matrix_path.write_text(
        json.dumps(
            {
                "split": "validation",
                "confusionMatrix": metrics["confusionMatrix"],
                "threshold": metrics["threshold"],
                "binaryPolicy": metrics["binaryPolicy"],
            },
            indent=2,
        )
        + "\n"
    )

    report = build_baseline_validation_report(
        report_id=f"baseline-{training_commit}",
        training_commit=training_commit,
        dataset_manifest_hash=sha256_file(manifest_path),
        checkpoint_reference=protected_reference(
            kind="protected-file",
            uri=f"protected://model-runs/{final_model_path.name}",
            sha256=sha256_file(final_model_path),
        ),
        confusion_matrix_reference=protected_reference(
            kind="protected-file",
            uri="protected://model-runs/validation-confusion-matrix.json",
            sha256=sha256_file(confusion_matrix_path),
        ),
        split_name="validation",
        split_record_count=len(validation_manifest),
        split_source_group_count=count_source_groups(manifest, "validation"),
        metrics=metrics,
        limitations=[
            "Draft baseline evidence generated from image-level validation only.",
            "Video-level sampling behavior is not evaluated by this training run.",
        ],
        threshold_rationale="Policy threshold is selected on the validation split for baseline evidence.",
        calibration_status="exploratory",
        calibration_notes="Validation threshold selection is exploratory until approved release evidence exists.",
    )
    report_path = output_dir / "baseline-validation-draft.json"
    write_report(
        report,
        report_path,
        schema_path=Path(__file__).parents[2] / "baseline-validation.schema.json",
    )
    return {
        "validationReportPath": str(report_path),
        "confusionMatrixReference": report["evaluation"]["metrics"]["confusionMatrixReference"],
    }


def train_baseline(
    *,
    manifest_path: Path,
    output_dir: Path,
    seed: int,
    batch_size: int,
    head_epochs: int,
    fine_tune_epochs: int,
    fine_tune_layers: int,
    training_commit: str,
    resume: bool = False,
) -> dict[str, Any]:
    set_reproducibility(seed)
    final_model_path = output_dir / "final.keras"
    metadata_path = output_dir / "run-metadata.json"
    if resume and final_model_path.is_file() and metadata_path.is_file():
        try:
            metadata = dict(json.loads(metadata_path.read_text()))
            keras.models.load_model(final_model_path)
            return metadata
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    train_ds, validation_ds, test_ds, manifest = make_all_datasets(
        manifest_path,
        batch_size=batch_size,
        seed=seed,
    )

    model, backbone, restored_stage = restore_training_model(
        output_dir=output_dir,
        resume=resume,
    )
    class_weights = calculate_class_weights(manifest)

    if restored_stage == "new":
        model.compile(
            optimizer=keras.optimizers.AdamW(learning_rate=3e-4, weight_decay=1e-4),
            loss=keras.losses.SparseCategoricalCrossentropy(),
            metrics=[keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
        )
        model.fit(
            train_ds,
            validation_data=validation_ds,
            epochs=head_epochs,
            class_weight=class_weights,
            callbacks=build_callbacks(output_dir / "head", resume=resume),
        )
        model.save(output_dir / "head-final.keras")

    if restored_stage != "fine-tune":
        backbone.trainable = True
        fine_tune_from = max(0, len(backbone.layers) - fine_tune_layers)
        for index, layer in enumerate(backbone.layers):
            layer.trainable = index >= fine_tune_from
            if isinstance(layer, keras.layers.BatchNormalization):
                layer.trainable = False

        model.compile(
            optimizer=keras.optimizers.AdamW(learning_rate=1e-5, weight_decay=1e-5),
            loss=keras.losses.SparseCategoricalCrossentropy(),
            metrics=[keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
        )
        model.fit(
            train_ds,
            validation_data=validation_ds,
            epochs=fine_tune_epochs,
            class_weight=class_weights,
            callbacks=build_callbacks(output_dir / "fine-tune", resume=resume),
        )
        model.save(output_dir / "fine-tune-final.keras")

    output_dir.mkdir(parents=True, exist_ok=True)
    model.save(final_model_path)
    test_metrics = model.evaluate(test_ds, return_dict=True)
    evidence = write_baseline_evidence(
        output_dir=output_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        validation_ds=validation_ds,
        model=model,
        final_model_path=final_model_path,
        training_commit=training_commit,
    )

    run_metadata: dict[str, Any] = {
        "seed": seed,
        "batchSize": batch_size,
        "headEpochs": head_epochs,
        "fineTuneEpochs": fine_tune_epochs,
        "fineTuneLayers": fine_tune_layers,
        "resumeRequested": resume,
        "restoredStage": restored_stage,
        "labels": list(LABELS),
        "classWeights": class_weights,
        "finalModelPath": str(final_model_path),
        "testMetrics": test_metrics,
        "evidence": evidence,
    }
    (output_dir / "run-metadata.json").write_text(json.dumps(run_metadata, indent=2) + "\n")
    return run_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the BBCDS baseline classifier")
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Protected training CSV manifest",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("runs/mobilenet-v3-small-v1"))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--head-epochs", type=int, default=15)
    parser.add_argument("--fine-tune-epochs", type=int, default=20)
    parser.add_argument("--fine-tune-layers", type=int, default=30)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from durable checkpoints in the output directory",
    )
    parser.add_argument(
        "--training-commit",
        default=None,
        help="Git commit recorded in the protected validation report",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_baseline(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        seed=args.seed,
        batch_size=args.batch_size,
        head_epochs=args.head_epochs,
        fine_tune_epochs=args.fine_tune_epochs,
        fine_tune_layers=args.fine_tune_layers,
        training_commit=args.training_commit or resolve_training_commit(Path(__file__).parents[3]),
        resume=args.resume,
    )
