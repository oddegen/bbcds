"""Protected baseline validation report construction."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from bbcds_model.constants import (
    INPUT_SHAPE,
    LABELS,
    MODEL_ARCHITECTURE,
    TAXONOMY_VERSION,
)


def protected_reference(*, kind: str, uri: str, sha256: str) -> dict[str, str]:
    return {"kind": kind, "uri": uri, "sha256": sha256}


def build_baseline_validation_report(
    *,
    report_id: str,
    training_commit: str,
    dataset_manifest_hash: str,
    checkpoint_reference: dict[str, str],
    confusion_matrix_reference: dict[str, str],
    split_name: str,
    split_record_count: int,
    split_source_group_count: int,
    metrics: dict[str, Any],
    limitations: list[str],
    threshold_rationale: str,
    calibration_status: str = "not-evaluated",
    calibration_notes: str = "Calibration was not evaluated for the baseline.",
    approval_status: str = "draft",
    approver: str | None = None,
    approved_at: str | None = None,
    approval_notes: str | None = None,
) -> dict[str, Any]:
    approval: dict[str, str] = {"status": approval_status}
    if approver is not None:
        approval["approver"] = approver
    if approved_at is not None:
        approval["approvedAt"] = approved_at
    if approval_notes is not None:
        approval["notes"] = approval_notes

    return {
        "schemaVersion": 1,
        "reportId": report_id,
        "createdAt": datetime.now(UTC).isoformat(),
        "trainingCommit": training_commit,
        "datasetManifestHash": dataset_manifest_hash,
        "taxonomyVersion": TAXONOMY_VERSION,
        "labels": list(LABELS),
        "model": {
            "architecture": MODEL_ARCHITECTURE,
            "inputShape": list(INPUT_SHAPE),
            "checkpointReference": checkpoint_reference,
            "thresholdRationale": threshold_rationale,
        },
        "evaluation": {
            "scope": "Image-level held-out evaluation for the accepted BBCDS taxonomy.",
            "split": {
                "name": split_name,
                "recordCount": split_record_count,
                "sourceGroupCount": split_source_group_count,
            },
            "metrics": {
                "macroF1": metrics["macroF1"],
                "perClass": metrics["perClass"],
                "confusionMatrixReference": confusion_matrix_reference,
            },
            "calibration": {
                "status": calibration_status,
                "notes": calibration_notes,
            },
            "limitations": limitations,
        },
        "approval": approval,
    }


def validate_baseline_report(report: dict[str, Any], *, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text())
    Draft202012Validator(schema).validate(report)


def write_report(report: dict[str, Any], output_path: Path, *, schema_path: Path) -> None:
    validate_baseline_report(report, schema_path=schema_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
