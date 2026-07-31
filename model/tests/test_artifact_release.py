from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import tensorflow as tf
from jsonschema import ValidationError
from PIL import Image
from tensorflow import keras

from bbcds_model.artifact_release import (
    ArtifactReleaseError,
    sha256_file,
    validate_manifest_schema,
    validate_new_protected_path,
)
from bbcds_model.constants import LABELS
from bbcds_model.export_artifact import (
    CONVERSION_REPORT_FILENAME,
    artifact_filename,
    export_artifact,
    select_representative_samples,
    validate_parity_gates,
)
from bbcds_model.finalize_artifact import finalize_artifact
from bbcds_model.manifest import attach_training_columns
from bbcds_model.tensorflow_adapter import frozen_concrete_function
from bbcds_model.validation_report import (
    build_baseline_validation_report,
    protected_reference,
    write_report,
)

MODEL_ROOT = Path(__file__).parents[1]
BASELINE_SCHEMA = MODEL_ROOT / "baseline-validation.schema.json"
MANIFEST_SCHEMA = MODEL_ROOT / "manifest.schema.json"
APPROVED_AT = "2026-07-31T12:00:00+00:00"
RELEASE_ID = "synthetic-release"
MODEL_ID = "synthetic-model"
SEMANTIC_VERSION = "1.2.3"
QUANTIZATION_MODE = "int8-internal-float32-boundary"
RUNTIME_PACKAGE = "@litertjs/core"
RUNTIME_VERSION = "2.5.3"


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _make_checkpoint(path: Path) -> None:
    inputs = keras.Input(shape=(224, 224, 3), dtype=tf.float32, name="image")
    features = keras.layers.Rescaling(1 / 255)(inputs)
    features = keras.layers.GlobalAveragePooling2D()(features)
    outputs = keras.layers.Dense(4, activation="softmax", dtype=tf.float32)(features)
    keras.Model(inputs, outputs).save(path)


def _make_manifest(directory: Path) -> Path:
    rows: list[dict[str, object]] = []
    index = 0
    for split, count in (("train", 2), ("validation", 1), ("test", 1)):
        for label_id, label in enumerate(LABELS):
            for occurrence in range(count):
                image_path = directory / f"benign-{index}.png"
                pixels = np.full(
                    (8, 8, 3),
                    fill_value=(label_id * 50 + occurrence * 7 + 10),
                    dtype=np.uint8,
                )
                Image.fromarray(pixels, mode="RGB").save(image_path)
                rows.append(
                    {
                        "path": image_path.name,
                        "label": label,
                        "source_id": f"source-{index}",
                        "split": split,
                        "media_type": "image",
                        "license": "synthetic-test",
                        "sha256": sha256_file(image_path, description="synthetic image"),
                    }
                )
                index += 1
    manifest = directory / "dataset.csv"
    pd.DataFrame(rows).to_csv(manifest, index=False)
    return manifest


def _make_approved_report(directory: Path, manifest: Path, checkpoint: Path) -> Path:
    placeholder = "0" * 64
    per_class = [
        {"label": label, "support": 1, "precision": 1.0, "recall": 1.0, "f1": 1.0}
        for label in LABELS
    ]
    report = build_baseline_validation_report(
        report_id="synthetic-baseline",
        training_commit="0b92626ea18e",
        dataset_manifest_hash=sha256_file(manifest, description="manifest"),
        checkpoint_reference=protected_reference(
            kind="protected-file",
            uri="protected://synthetic/final.keras",
            sha256=sha256_file(checkpoint, description="checkpoint"),
        ),
        confusion_matrix_reference=protected_reference(
            kind="protected-file",
            uri="protected://synthetic/confusion.json",
            sha256=placeholder,
        ),
        split_name="validation",
        split_record_count=4,
        split_source_group_count=4,
        metrics={"macroF1": 1.0, "perClass": per_class},
        limitations=["Synthetic release-path test."],
        threshold_rationale="Synthetic fixed threshold.",
        calibration_status="exploratory",
        approval_status="approved",
        approver="test-owner",
        approved_at=APPROVED_AT,
        approval_notes="Synthetic approval.",
    )
    output = directory / "approved-baseline.json"
    write_report(report, output, schema_path=BASELINE_SCHEMA)
    return output


def _make_policy(
    directory: Path, *, manifest: Path, checkpoint: Path, approved_report: Path
) -> Path:
    policy = {
        "schemaVersion": 1,
        "releaseId": RELEASE_ID,
        "modelId": MODEL_ID,
        "semanticVersion": SEMANTIC_VERSION,
        "trainingCommit": "0b92626ea18e",
        "datasetManifestHash": sha256_file(manifest, description="manifest"),
        "checkpointHash": sha256_file(checkpoint, description="checkpoint"),
        "approvedBaselineReportHash": sha256_file(
            approved_report, description="approved report"
        ),
        "labels": list(LABELS),
        "input": {
            "shape": [1, 224, 224, 3],
            "dtype": "float32",
            "range": [0, 255],
            "colorSpace": "RGB",
            "layout": "NHWC",
            "resize": "aspect-preserving-letterbox",
            "modelPreprocessing": "MobileNetV3",
        },
        "output": {"shape": [1, 4], "dtype": "float32", "semantics": "probabilities"},
        "quantization": {
            "mode": QUANTIZATION_MODE,
            "representativeSplit": "train",
            "representativeSampleCount": 8,
            "samplesPerLabel": 2,
            "uniqueSourceGroups": True,
            "seed": 7,
        },
        "parity": {
            "split": "validation",
            "threshold": 0.43,
            "minimumTop1Agreement": 0.0,
            "maximumMacroF1Drop": 1.0,
            "maximumBinaryPrecisionDrop": 1.0,
            "maximumBinaryRecallDrop": 1.0,
        },
        "runtime": {
            "package": RUNTIME_PACKAGE,
            "version": RUNTIME_VERSION,
            "accelerator": "wasm",
            "browser": "chromium",
            "warmupIterations": 10,
            "measuredIterations": 50,
        },
        "thresholdsVersion": "baseline-v1-exploratory",
    }
    output = directory / "artifact-policy.json"
    _write_json(output, policy)
    return output


def _compatibility_report(artifact: Path) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "releaseId": RELEASE_ID,
        "modelId": MODEL_ID,
        "semanticVersion": SEMANTIC_VERSION,
        "artifact": {
            "sha256": sha256_file(artifact, description="artifact"),
            "sizeBytes": artifact.stat().st_size,
        },
        "runtime": {
            "package": RUNTIME_PACKAGE,
            "version": RUNTIME_VERSION,
            "accelerator": "wasm",
        },
        "browser": {"name": "chromium", "version": "test", "platform": "test"},
        "tensorContract": {
            "inputShape": [1, 224, 224, 3],
            "inputDType": "float32",
            "outputShape": [1, 4],
            "outputDType": "float32",
        },
        "benchmark": {
            "runtimeInitializationMs": 1.0,
            "modelCompilationMs": 2.0,
            "warmupIterations": 10,
            "measuredIterations": 50,
            "inferenceMs": {"minimum": 3.0, "p50": 4.0, "p95": 5.0, "maximum": 6.0},
        },
        "compatibility": {
            "runtimeInitialized": True,
            "modelCompiled": True,
            "inferenceCompleted": True,
            "resourcesReleased": True,
            "passed": True,
        },
    }


def test_exports_quantized_artifact_and_finalizes_aggregate_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    checkpoint = tmp_path / "final.keras"
    _make_checkpoint(checkpoint)
    manifest = _make_manifest(tmp_path)
    approved_report = _make_approved_report(tmp_path, manifest, checkpoint)
    policy = _make_policy(
        tmp_path,
        manifest=manifest,
        checkpoint=checkpoint,
        approved_report=approved_report,
    )
    output_directory = tmp_path / "protected-release"
    monkeypatch.setattr(
        "bbcds_model.export_artifact.validate_new_protected_path",
        lambda *args, **kwargs: None,
    )
    report = export_artifact(
        policy_path=policy,
        approved_baseline_report_path=approved_report,
        checkpoint_path=checkpoint,
        manifest_path=manifest,
        output_directory=output_directory,
        schema_path=BASELINE_SCHEMA,
        repository_root=tmp_path / "repository",
        batch_size=2,
    )
    policy_value = json.loads(policy.read_text(encoding="utf-8"))
    artifact = output_directory / artifact_filename(policy_value)
    conversion_report = output_directory / CONVERSION_REPORT_FILENAME
    assert artifact.is_file()
    assert report["tensorContract"]["quantizedInternalTensorCount"] > 0
    assert report["gates"]["passed"] is True
    assert report["provenance"]["policyHash"] == sha256_file(
        policy, description="policy"
    )
    assert stat.S_IMODE(artifact.stat().st_mode) == 0o600
    assert stat.S_IMODE(conversion_report.stat().st_mode) == 0o600

    compatibility = tmp_path / "compatibility.json"
    _write_json(compatibility, _compatibility_report(artifact))
    approved_manifest = tmp_path / "approved-artifact-manifest.json"
    monkeypatch.setattr(
        "bbcds_model.finalize_artifact.validate_new_protected_path",
        lambda *args, **kwargs: None,
    )
    manifest_value, summary = finalize_artifact(
        policy_path=policy,
        artifact_path=artifact,
        conversion_report_path=conversion_report,
        compatibility_report_path=compatibility,
        approved_baseline_report_path=approved_report,
        approver="project-owner",
        output_path=approved_manifest,
        schema_path=MANIFEST_SCHEMA,
        repository_root=tmp_path / "repository",
        approved_at=APPROVED_AT,
    )
    validate_manifest_schema(manifest_value, schema_path=MANIFEST_SCHEMA)
    assert summary["artifact"]["sha256"] == sha256_file(
        artifact, description="artifact"
    )
    assert stat.S_IMODE(approved_manifest.stat().st_mode) == 0o600
    stdout = capsys.readouterr().out.lower()
    assert all(fragment not in stdout for fragment in ("benign-", "source-", "probabilit"))

    tampered_conversion = json.loads(json.dumps(report))
    tampered_conversion["provenance"]["policyHash"] = "0" * 64
    _write_json(conversion_report, tampered_conversion)
    with pytest.raises(ArtifactReleaseError, match="policy hash"):
        finalize_artifact(
            policy_path=policy,
            artifact_path=artifact,
            conversion_report_path=conversion_report,
            compatibility_report_path=compatibility,
            approved_baseline_report_path=approved_report,
            approver="project-owner",
            output_path=tmp_path / "must-not-exist.json",
            schema_path=MANIFEST_SCHEMA,
            repository_root=tmp_path / "repository",
            approved_at=APPROVED_AT,
        )
    _write_json(conversion_report, report)

    tampered = _compatibility_report(artifact)
    tampered["compatibility"]["resourcesReleased"] = False
    _write_json(compatibility, tampered)
    with pytest.raises(ArtifactReleaseError, match="resourcesreleased"):
        finalize_artifact(
            policy_path=policy,
            artifact_path=artifact,
            conversion_report_path=conversion_report,
            compatibility_report_path=compatibility,
            approved_baseline_report_path=approved_report,
            approver="project-owner",
            output_path=tmp_path / "must-not-exist.json",
            schema_path=MANIFEST_SCHEMA,
            repository_root=tmp_path / "repository",
            approved_at=APPROVED_AT,
        )


def test_representative_selection_rejects_inadequate_or_reused_sources(tmp_path: Path) -> None:
    rows = [
        {
            "path": "synthetic.png",
            "label": label,
            "source_id": "shared-source",
            "split": "train",
            "media_type": "image",
            "license": "synthetic-test",
            "sha256": f"{index + 1:064x}",
        }
        for index, label in enumerate(LABELS)
    ]
    prepared = attach_training_columns(pd.DataFrame(rows), manifest_dir=tmp_path)
    with pytest.raises(ArtifactReleaseError, match="inadequate representative coverage"):
        select_representative_samples(prepared, samples_per_label=2, seed=7)


def test_parity_gate_rejects_metric_regression() -> None:
    policy = {
        "parity": {
            "minimumTop1Agreement": 0.98,
            "maximumMacroF1Drop": 0.01,
            "maximumBinaryPrecisionDrop": 0.01,
            "maximumBinaryRecallDrop": 0.01,
        }
    }
    parity = {
        "top1Agreement": 0.97,
        "keras": {"macroF1": 0.9, "binaryPrecision": 0.9, "binaryRecall": 0.9},
        "tflite": {"macroF1": 0.8, "binaryPrecision": 0.8, "binaryRecall": 0.8},
    }
    with pytest.raises(ArtifactReleaseError, match="parity gates"):
        validate_parity_gates(parity, policy)


def test_tensorflow_adapter_rejects_unvalidated_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("bbcds_model.tensorflow_adapter.tf.__version__", "2.17.0")
    with pytest.raises(ArtifactReleaseError, match="does not support"):
        frozen_concrete_function(object())  # type: ignore[arg-type]


def test_protected_output_rejects_worktree_temporary_and_existing_paths(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    temporary = tmp_path / "temporary"
    protected = tmp_path / "protected"
    for directory in (repository, temporary, protected):
        directory.mkdir()
    for output, message in (
        (repository / "release", "Git worktree"),
        (temporary / "release", "temporary storage"),
    ):
        with pytest.raises(ArtifactReleaseError, match=message):
            validate_new_protected_path(
                output,
                repository_root=repository,
                temporary_root=temporary,
            )
    existing = protected / "release"
    existing.mkdir()
    with pytest.raises(ArtifactReleaseError, match="refusing to overwrite"):
        validate_new_protected_path(
            existing,
            repository_root=repository,
            temporary_root=temporary,
        )


def test_manifest_schema_is_release_neutral(tmp_path: Path) -> None:
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    reusable_schema = tmp_path / "reusable-schema.json"
    _write_json(reusable_schema, schema)
    valid_shape = {
        "schemaVersion": 1,
        "releaseId": "next-release",
        "modelId": "next-model",
        "semanticVersion": "2.0.0",
        "artifact": {"sha256": "0" * 64, "sizeBytes": 1},
        "trainingCommit": "abcdefg",
        "datasetManifestHash": "1" * 64,
        "labels": list(LABELS),
        "input": {
            "shape": [1, 224, 224, 3],
            "dtype": "float32",
            "range": [0, 255],
            "colorSpace": "RGB",
            "layout": "NHWC",
            "resize": "aspect-preserving-letterbox",
            "modelPreprocessing": "MobileNetV3",
        },
        "output": {"shape": [1, 4], "dtype": "float32", "semantics": "probabilities"},
        "quantizationMode": "future-quantization-mode",
        "thresholdsVersion": "next-thresholds",
        "runtime": {
            "package": "future-runtime",
            "minimumVersion": "3.0.0",
            "accelerator": "future-accelerator",
        },
        "evidence": {
            "approvedBaselineReportHash": "2" * 64,
            "conversionReportHash": "3" * 64,
            "compatibilityReportHash": "4" * 64,
        },
        "approval": {
            "status": "approved",
            "approvedAt": APPROVED_AT,
            "approver": "owner",
        },
    }
    validate_manifest_schema(valid_shape, schema_path=reusable_schema)
    valid_shape["semanticVersion"] = "not-semver"
    with pytest.raises(ValidationError):
        validate_manifest_schema(valid_shape, schema_path=reusable_schema)
