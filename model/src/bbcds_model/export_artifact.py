"""CLI orchestration for protected TFLite artifact export."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tensorflow import keras

from bbcds_model.artifact_policy import validate_artifact_policy
from bbcds_model.artifact_release import (
    ArtifactReleaseError,
    read_json_object,
    require_equal,
    sha256_bytes,
    sha256_file,
    validate_new_protected_path,
    write_private_bytes,
    write_private_json,
)
from bbcds_model.artifact_service import (
    convert_model,
    evaluate_parity,
    inspect_tflite,
    select_representative_samples,
    validate_keras_contract,
    validate_parity_gates,
)
from bbcds_model.constants import LABELS
from bbcds_model.manifest import (
    attach_training_columns,
    load_training_manifest,
    split_manifest,
)
from bbcds_model.release_provenance import collect_provenance
from bbcds_model.validation_report import validate_baseline_report

CONVERSION_REPORT_FILENAME = "artifact-conversion-parity.json"


def artifact_filename(policy: Mapping[str, Any]) -> str:
    return f"{policy['modelId']}-{policy['semanticVersion']}.tflite"


def _validate_baseline_binding(
    *,
    policy: Mapping[str, Any],
    approved_report: Mapping[str, Any],
    approved_report_path: Path,
    checkpoint_path: Path,
    manifest_path: Path,
) -> None:
    bindings = (
        (
            sha256_file(approved_report_path, description="approved baseline report"),
            policy["approvedBaselineReportHash"],
            "approved baseline report SHA-256",
        ),
        (
            sha256_file(checkpoint_path, description="Keras checkpoint"),
            policy["checkpointHash"],
            "checkpoint SHA-256",
        ),
        (
            sha256_file(manifest_path, description="protected manifest"),
            policy["datasetManifestHash"],
            "dataset manifest SHA-256",
        ),
    )
    for actual, expected, description in bindings:
        require_equal(actual, expected, description=description)
    try:
        report_bindings = (
            (approved_report["approval"]["status"], "approved", "baseline approval status"),
            (approved_report["trainingCommit"], policy["trainingCommit"], "training commit"),
            (
                approved_report["datasetManifestHash"],
                policy["datasetManifestHash"],
                "baseline manifest hash",
            ),
            (
                approved_report["model"]["checkpointReference"]["sha256"],
                policy["checkpointHash"],
                "baseline checkpoint reference",
            ),
            (approved_report["labels"], list(LABELS), "baseline labels"),
        )
        for actual, expected, description in report_bindings:
            require_equal(actual, expected, description=description)
    except (KeyError, TypeError) as error:
        raise ArtifactReleaseError(
            "Approved baseline report is missing required fields"
        ) from error


def export_artifact(
    *,
    policy_path: Path,
    approved_baseline_report_path: Path,
    checkpoint_path: Path,
    manifest_path: Path,
    output_directory: Path,
    schema_path: Path,
    repository_root: Path,
    batch_size: int = 32,
) -> dict[str, Any]:
    policy = validate_artifact_policy(
        read_json_object(policy_path, description="artifact policy")
    )
    approved_report = read_json_object(
        approved_baseline_report_path, description="approved baseline report"
    )
    try:
        validate_baseline_report(approved_report, schema_path=schema_path)
    except Exception as error:
        raise ArtifactReleaseError("Approved baseline report is invalid") from error
    _validate_baseline_binding(
        policy=policy,
        approved_report=approved_report,
        approved_report_path=approved_baseline_report_path,
        checkpoint_path=checkpoint_path,
        manifest_path=manifest_path,
    )
    try:
        manifest = load_training_manifest(
            manifest_path, verify_files=True, verify_hashes=True
        )
    except (OSError, ValueError) as error:
        raise ArtifactReleaseError(
            "Protected training manifest or media is invalid"
        ) from error
    prepared = attach_training_columns(manifest, manifest_dir=manifest_path.parent)
    calibration, calibration_digest = select_representative_samples(
        prepared,
        samples_per_label=policy["quantization"]["samplesPerLabel"],
        seed=policy["quantization"]["seed"],
    )
    try:
        model = keras.models.load_model(checkpoint_path)
    except Exception as error:
        raise ArtifactReleaseError("Keras checkpoint could not be loaded") from error
    validate_keras_contract(model)
    model_content = convert_model(model, calibration)
    interpreter, tensor_contract = inspect_tflite(model_content)
    validation = split_manifest(prepared, policy["parity"]["split"])
    parity = evaluate_parity(
        model,
        interpreter,
        validation,
        batch_size=batch_size,
        seed=policy["quantization"]["seed"],
        threshold=policy["parity"]["threshold"],
    )
    gate_results = validate_parity_gates(parity, policy)
    report = {
        "schemaVersion": 1,
        **{
            field: policy[field]
            for field in (
                "releaseId",
                "modelId",
                "semanticVersion",
                "trainingCommit",
                "datasetManifestHash",
                "checkpointHash",
                "approvedBaselineReportHash",
            )
        },
        "artifact": {
            "sha256": sha256_bytes(model_content),
            "sizeBytes": len(model_content),
        },
        "quantization": {
            "mode": policy["quantization"]["mode"],
            "representativeSampleCount": len(calibration),
            "representativeSourceGroupCount": int(
                calibration["source_id"].nunique()
            ),
            "representativeSubsetHash": calibration_digest,
            "samplesPerLabel": {
                label: int((calibration["label"] == label).sum())
                for label in LABELS
            },
        },
        "tensorContract": tensor_contract,
        "parity": parity,
        "gates": {**gate_results, "passed": True},
        "provenance": collect_provenance(
            policy_path=policy_path, repository_root=Path(__file__).parents[3]
        ),
    }
    validate_new_protected_path(output_directory, repository_root=repository_root)
    output_created = False
    filename = artifact_filename(policy)
    try:
        os.mkdir(output_directory, mode=0o700)
        output_created = True
        write_private_bytes(output_directory / filename, model_content)
        write_private_json(output_directory / CONVERSION_REPORT_FILENAME, report)
    except BaseException:
        if output_created:
            for output_name in (filename, CONVERSION_REPORT_FILENAME):
                (output_directory / output_name).unlink(missing_ok=True)
            output_directory.rmdir()
        raise
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export and evaluate a protected TFLite artifact."
    )
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--approved-baseline-report", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    repository_root = Path(__file__).parents[3]
    try:
        report = export_artifact(
            policy_path=args.policy,
            approved_baseline_report_path=args.approved_baseline_report,
            checkpoint_path=args.checkpoint,
            manifest_path=args.manifest,
            output_directory=args.output_directory,
            schema_path=repository_root / "model" / "baseline-validation.schema.json",
            repository_root=repository_root,
            batch_size=args.batch_size,
        )
    except ArtifactReleaseError as error:
        raise SystemExit(f"Artifact export failed: {error}") from error
    print(
        json.dumps(
            {
                "releaseId": report["releaseId"],
                "artifact": report["artifact"],
                "parity": report["parity"],
                "gates": report["gates"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
