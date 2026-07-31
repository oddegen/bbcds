"""Approve protected baseline evidence against a pinned release policy."""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

import pandas as pd
from jsonschema import ValidationError

from bbcds_model.constants import LABELS, REQUIRED_TRAINING_SPLITS
from bbcds_model.manifest import load_training_manifest, sha256_file
from bbcds_model.validation_report import validate_baseline_report

APPROVAL_NOTE = (
    "Approved as the BBCDS research baseline for model-artifact conversion; "
    "evidence is image-level only, and the exploratory threshold is not a "
    "production calibration claim."
)


class FinalizationError(ValueError):
    """Raised when protected baseline evidence cannot be approved safely."""


def _read_json_object(path: Path, *, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FinalizationError(f"Could not read {description}") from error
    if not isinstance(value, dict):
        raise FinalizationError(f"{description.capitalize()} must be a JSON object")
    return value


def _sha256(path: Path, *, description: str) -> str:
    try:
        return sha256_file(path)
    except OSError as error:
        raise FinalizationError(f"Could not read {description}") from error


def _require_equal(actual: object, expected: object, *, description: str) -> None:
    if actual != expected:
        raise FinalizationError(
            f"{description.capitalize()} does not match release policy"
        )


def _require_rate(value: object, *, description: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FinalizationError(f"{description.capitalize()} must be a number")
    rate = float(value)
    if not 0 <= rate <= 1:
        raise FinalizationError(f"{description.capitalize()} must be between 0 and 1")
    return rate


def _validate_confusion_evidence(confusion: Mapping[str, Any]) -> None:
    try:
        matrix = confusion["confusionMatrix"]
        threshold = confusion["threshold"]
        binary_policy = confusion["binaryPolicy"]
        if (
            not isinstance(matrix, list)
            or len(matrix) != len(LABELS)
            or any(
                not isinstance(row, list)
                or len(row) != len(LABELS)
                or any(
                    isinstance(value, bool) or not isinstance(value, int) or value < 0
                    for value in row
                )
                for row in matrix
            )
        ):
            raise FinalizationError("Confusion matrix must match canonical labels")
        if not isinstance(threshold, dict) or not isinstance(binary_policy, dict):
            raise FinalizationError("Confusion metrics must be JSON objects")
        for name in ("threshold", "precision", "recall", "f1"):
            _require_rate(threshold[name], description=f"threshold {name}")
        for name in ("precision", "recall", "f1"):
            _require_rate(binary_policy[name], description=f"binary-policy {name}")
    except KeyError as error:
        raise FinalizationError(
            "Confusion evidence is missing required fields"
        ) from error


def build_public_summary(
    manifest: pd.DataFrame,
    audit: Mapping[str, Any],
    *,
    manifest_hash: str,
    release_id: str,
) -> dict[str, Any]:
    """Return aggregate-only evidence suitable for public documentation."""
    labels_by_split = {
        split: {
            label: int(
                ((manifest["split"] == split) & (manifest["label"] == label)).sum()
            )
            for label in LABELS
        }
        for split in REQUIRED_TRAINING_SPLITS
    }
    source_groups_by_split = {
        split: int(manifest.loc[manifest["split"] == split, "source_id"].nunique())
        for split in REQUIRED_TRAINING_SPLITS
    }
    return {
        "schemaVersion": 1,
        "releaseId": release_id,
        "datasetManifestHash": manifest_hash,
        "profile": audit["profile"],
        "seed": audit["seed"],
        "scannedCount": audit["scannedCount"],
        "acceptedCount": len(manifest),
        "sourceGroupCount": int(manifest["source_id"].nunique()),
        "splits": {
            split: int((manifest["split"] == split).sum())
            for split in REQUIRED_TRAINING_SPLITS
        },
        "labels": {label: int((manifest["label"] == label).sum()) for label in LABELS},
        "labelsBySplit": labels_by_split,
        "sourceGroupsBySplit": source_groups_by_split,
        "exactDuplicateCount": audit["exactDuplicateCount"],
        "nearDuplicateClusterCount": audit["nearDuplicateClusterCount"],
        "conflictingClusterRecordCount": audit["conflictingClusterRecordCount"],
        "corruptCount": audit["corruptCount"],
        "policyExcludedCount": audit["policyExcludedCount"],
    }


def _validate_audit(
    audit: Mapping[str, Any], *, public_summary: Mapping[str, Any]
) -> None:
    try:
        for field in ("acceptedCount", "sourceGroupCount", "splits", "labels"):
            if audit[field] != public_summary[field]:
                raise FinalizationError(
                    f"Audit {field} does not match the protected manifest"
                )
        count_fields = (
            "scannedCount",
            "acceptedCount",
            "sourceGroupCount",
            "exactDuplicateCount",
            "nearDuplicateClusterCount",
            "conflictingClusterRecordCount",
            "corruptCount",
            "policyExcludedCount",
        )
        if any(
            isinstance(audit[field], bool)
            or not isinstance(audit[field], int)
            or audit[field] < 0
            for field in count_fields
        ):
            raise FinalizationError("Audit counts must be non-negative integers")
        if audit["scannedCount"] < audit["acceptedCount"]:
            raise FinalizationError("Audit scannedCount must cover acceptedCount")
        ratios = audit["splitRatios"]
        if not isinstance(ratios, dict) or set(ratios) != set(REQUIRED_TRAINING_SPLITS):
            raise FinalizationError("Audit split ratios are invalid")
        if not math.isclose(
            sum(
                _require_rate(ratios[split], description="split ratio")
                for split in ratios
            ),
            1.0,
            abs_tol=1e-12,
        ):
            raise FinalizationError("Audit split ratios do not sum to 1")
    except KeyError as error:
        raise FinalizationError("Dataset audit is missing required fields") from error


def _validate_policy_binding(
    *,
    policy: Mapping[str, Any],
    draft: Mapping[str, Any],
    audit: Mapping[str, Any],
    confusion: Mapping[str, Any],
    hashes: Mapping[str, str],
) -> None:
    try:
        if policy["schemaVersion"] != 1:
            raise FinalizationError("Unsupported release policy version")
        _require_equal(draft["reportId"], policy["reportId"], description="report ID")
        _require_equal(
            draft["trainingCommit"],
            policy["trainingCommit"],
            description="training commit",
        )
        _require_equal(draft["labels"], policy["labels"], description="report labels")
        _require_equal(list(LABELS), policy["labels"], description="canonical labels")
        _require_equal(
            draft["evaluation"]["split"],
            policy["evaluationSplit"],
            description="evaluation split",
        )
        _require_equal(
            draft["evaluation"]["calibration"]["status"],
            policy["calibrationStatus"],
            description="calibration status",
        )
        _require_equal(
            audit["profile"], policy["profile"], description="dataset profile"
        )
        _require_equal(audit["seed"], policy["seed"], description="dataset seed")
        for name, policy_field in (
            ("manifest", "datasetManifestHash"),
            ("audit", "datasetAuditHash"),
            ("draft", "draftReportHash"),
            ("checkpoint", "checkpointHash"),
            ("confusion", "confusionMatrixHash"),
        ):
            _require_equal(
                hashes[name], policy[policy_field], description=f"{name} SHA-256"
            )
        _require_equal(
            draft["datasetManifestHash"],
            hashes["manifest"],
            description="report manifest SHA-256",
        )
        _require_equal(
            draft["model"]["checkpointReference"]["sha256"],
            hashes["checkpoint"],
            description="checkpoint reference SHA-256",
        )
        _require_equal(
            draft["evaluation"]["metrics"]["confusionMatrixReference"]["sha256"],
            hashes["confusion"],
            description="confusion-matrix reference SHA-256",
        )
        _require_equal(
            confusion["split"],
            policy["evaluationSplit"]["name"],
            description="confusion-matrix split",
        )
        if not math.isclose(
            _require_rate(confusion["threshold"]["threshold"], description="threshold"),
            _require_rate(policy["threshold"], description="policy threshold"),
            rel_tol=0,
            abs_tol=1e-12,
        ):
            raise FinalizationError("Threshold does not match release policy")
    except (KeyError, TypeError) as error:
        raise FinalizationError(
            "Release evidence is missing required fields"
        ) from error


def finalize_baseline(
    *,
    policy_path: Path,
    manifest_path: Path,
    audit_path: Path,
    draft_path: Path,
    checkpoint_path: Path,
    confusion_matrix_path: Path,
    approver: str,
    schema_path: Path,
    approved_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not approver.strip():
        raise FinalizationError("Approver must not be empty")

    policy = _read_json_object(policy_path, description="release policy")
    audit = _read_json_object(audit_path, description="dataset audit")
    draft = _read_json_object(draft_path, description="baseline validation draft")
    confusion = _read_json_object(
        confusion_matrix_path, description="confusion-matrix evidence"
    )
    try:
        validate_baseline_report(draft, schema_path=schema_path)
    except ValidationError as error:
        raise FinalizationError(
            "Baseline validation draft does not conform to its schema"
        ) from error
    if draft["approval"]["status"] != "draft":
        raise FinalizationError("Only a draft baseline report can be finalized")

    hashes = {
        "manifest": _sha256(manifest_path, description="protected manifest"),
        "audit": _sha256(audit_path, description="dataset audit"),
        "draft": _sha256(draft_path, description="baseline validation draft"),
        "checkpoint": _sha256(checkpoint_path, description="model checkpoint"),
        "confusion": _sha256(
            confusion_matrix_path, description="confusion-matrix evidence"
        ),
    }
    _validate_confusion_evidence(confusion)
    _validate_policy_binding(
        policy=policy,
        draft=draft,
        audit=audit,
        confusion=confusion,
        hashes=hashes,
    )

    try:
        manifest = load_training_manifest(
            manifest_path, verify_files=False, verify_hashes=False
        )
    except (OSError, ValueError) as error:
        raise FinalizationError("Protected manifest is invalid") from error

    try:
        summary = build_public_summary(
            manifest,
            audit,
            manifest_hash=hashes["manifest"],
            release_id=policy["releaseId"],
        )
    except KeyError as error:
        raise FinalizationError("Dataset audit is missing required fields") from error
    _validate_audit(audit, public_summary=summary)

    evaluation_split = draft["evaluation"]["split"]
    split_name = evaluation_split["name"]
    if evaluation_split["recordCount"] != int((manifest["split"] == split_name).sum()):
        raise FinalizationError(
            "Validation report record count does not match the protected manifest"
        )
    if evaluation_split["sourceGroupCount"] != int(
        manifest.loc[manifest["split"] == split_name, "source_id"].nunique()
    ):
        raise FinalizationError(
            "Validation report source-group count does not match the protected manifest"
        )

    approved = copy.deepcopy(draft)
    approved["approval"] = {
        "status": "approved",
        "approvedAt": approved_at or datetime.now(UTC).isoformat(),
        "approver": approver.strip(),
        "notes": APPROVAL_NOTE,
    }
    try:
        validate_baseline_report(approved, schema_path=schema_path)
    except ValidationError as error:
        raise FinalizationError(
            "Approved baseline report does not conform to its schema"
        ) from error
    return approved, summary


def validate_protected_output_path(
    output_path: Path,
    *,
    repository_root: Path,
    temporary_root: Path | None = None,
) -> None:
    resolved = output_path.resolve()
    if not resolved.parent.is_dir():
        raise FinalizationError("Protected output directory does not exist")
    if resolved.is_relative_to(repository_root.resolve()):
        raise FinalizationError("Protected output must be outside the Git worktree")
    temp_root = (temporary_root or Path(tempfile.gettempdir())).resolve()
    if resolved.is_relative_to(temp_root):
        raise FinalizationError("Protected output must not use temporary storage")
    if resolved.exists():
        raise FinalizationError("Output path already exists; refusing to overwrite it")


def _write_approved_report(report: Mapping[str, Any], output_path: Path) -> None:
    try:
        descriptor = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output_file:
            json.dump(report, output_file, indent=2)
            output_file.write("\n")
    except FileExistsError as error:
        raise FinalizationError(
            "Output path already exists; refusing to overwrite it"
        ) from error
    except OSError as error:
        raise FinalizationError("Could not write protected approval report") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Approve a protected BBCDS baseline validation report"
    )
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--confusion-matrix", type=Path, required=True)
    parser.add_argument("--approver", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def _exit_with_error(
    parser: argparse.ArgumentParser, error: FinalizationError
) -> NoReturn:
    parser.exit(2, f"error: {error}\n")


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    model_root = Path(__file__).parents[2]
    try:
        approved, summary = finalize_baseline(
            policy_path=args.policy,
            manifest_path=args.manifest,
            audit_path=args.audit,
            draft_path=args.draft,
            checkpoint_path=args.checkpoint,
            confusion_matrix_path=args.confusion_matrix,
            approver=args.approver,
            schema_path=model_root / "baseline-validation.schema.json",
        )
        validate_protected_output_path(
            args.output, repository_root=Path(__file__).parents[3]
        )
        _write_approved_report(approved, args.output)
    except FinalizationError as error:
        _exit_with_error(parser, error)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
