"""Approve protected conversion and LiteRT.js compatibility evidence."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import ValidationError

from bbcds_model.artifact_policy import validate_artifact_policy
from bbcds_model.artifact_release import (
    ArtifactReleaseError,
    read_json_object,
    require_equal,
    sha256_file,
    validate_manifest_schema,
    validate_new_protected_path,
    write_private_json,
)
from bbcds_model.artifact_service import validate_parity_gates
from bbcds_model.constants import LABELS

APPROVAL_NOTE = (
    "Approved as a protected TFLite artifact after Keras/TFLite "
    "parity and Chromium WASM compatibility gates; latency is record-only and "
    "the policy threshold remains exploratory."
)


def _require_fields(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    fields: Sequence[str],
    *,
    prefix: str,
) -> None:
    for field in fields:
        require_equal(actual[field], expected[field], description=f"{prefix} {field}")


def _validate_artifact_binding(
    artifact: Mapping[str, Any], *, digest: str, size: int, prefix: str
) -> None:
    require_equal(artifact["sha256"], digest, description=f"{prefix} artifact hash")
    require_equal(artifact["sizeBytes"], size, description=f"{prefix} artifact size")


def _validate_tensor_contract(
    contract: Mapping[str, Any], policy: Mapping[str, Any], *, prefix: str
) -> None:
    expected = {
        "inputShape": policy["input"]["shape"],
        "inputDType": policy["input"]["dtype"],
        "outputShape": policy["output"]["shape"],
        "outputDType": policy["output"]["dtype"],
    }
    _require_fields(
        contract,
        expected,
        tuple(expected),
        prefix=f"{prefix} tensor contract",
    )


def _validate_conversion_report(
    report: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    artifact_hash: str,
    artifact_size: int,
    policy_hash: str,
    lockfile_hash: str,
) -> None:
    try:
        _require_fields(
            report,
            policy,
            (
                "releaseId",
                "modelId",
                "semanticVersion",
                "trainingCommit",
                "datasetManifestHash",
                "checkpointHash",
                "approvedBaselineReportHash",
            ),
            prefix="conversion",
        )
        _validate_artifact_binding(
            report["artifact"], digest=artifact_hash, size=artifact_size, prefix="conversion"
        )
        require_equal(
            report["quantization"]["mode"],
            policy["quantization"]["mode"],
            description="conversion quantization mode",
        )
        require_equal(
            report["quantization"]["representativeSampleCount"],
            policy["quantization"]["representativeSampleCount"],
            description="representative sample count",
        )
        require_equal(
            report["quantization"]["representativeSourceGroupCount"],
            policy["quantization"]["representativeSampleCount"],
            description="representative source-group count",
        )
        require_equal(
            report["quantization"]["samplesPerLabel"],
            {label: policy["quantization"]["samplesPerLabel"] for label in LABELS},
            description="representative label coverage",
        )
        _validate_tensor_contract(report["tensorContract"], policy, prefix="conversion")
        if report["tensorContract"]["quantizedInternalTensorCount"] < 1:
            raise ArtifactReleaseError("Conversion evidence has no quantized internals")
        provenance = report["provenance"]
        require_equal(
            provenance["policyHash"], policy_hash, description="conversion policy hash"
        )
        require_equal(
            provenance["lockfileHash"],
            lockfile_hash,
            description="conversion lockfile hash",
        )
        if not re.fullmatch(r"[a-f0-9]{40}", provenance["sourceCommit"]):
            raise ArtifactReleaseError("Conversion source commit is invalid")
        toolchain = provenance["toolchain"]
        if any(
            not isinstance(toolchain[field], str) or not toolchain[field]
            for field in ("pythonVersion", "tensorflowVersion", "kerasVersion")
        ):
            raise ArtifactReleaseError("Conversion toolchain evidence is invalid")
        validate_parity_gates(report["parity"], policy)
    except (KeyError, TypeError) as error:
        raise ArtifactReleaseError("Conversion report is missing required evidence") from error


def _nonnegative_number(value: object, *, description: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ArtifactReleaseError(f"{description.capitalize()} must be non-negative")
    return float(value)


def _validate_compatibility_report(
    report: Mapping[str, Any], policy: Mapping[str, Any], *, artifact_hash: str, artifact_size: int
) -> None:
    try:
        require_equal(report["schemaVersion"], 1, description="compatibility schema version")
        _require_fields(
            report,
            policy,
            ("releaseId", "modelId", "semanticVersion"),
            prefix="compatibility",
        )
        _validate_artifact_binding(
            report["artifact"],
            digest=artifact_hash,
            size=artifact_size,
            prefix="compatibility",
        )
        _require_fields(
            report["runtime"],
            policy["runtime"],
            ("package", "version", "accelerator"),
            prefix="compatibility runtime",
        )
        require_equal(
            report["browser"]["name"], policy["runtime"]["browser"], description="browser"
        )
        _validate_tensor_contract(report["tensorContract"], policy, prefix="browser")
        require_equal(
            report["benchmark"]["warmupIterations"],
            policy["runtime"]["warmupIterations"],
            description="warmup iteration count",
        )
        require_equal(
            report["benchmark"]["measuredIterations"],
            policy["runtime"]["measuredIterations"],
            description="measured iteration count",
        )
        for field in ("runtimeInitialized", "modelCompiled", "inferenceCompleted", "resourcesReleased", "passed"):
            require_equal(report["compatibility"][field], True, description=f"compatibility {field}")
        _nonnegative_number(report["benchmark"]["runtimeInitializationMs"], description="runtime initialization")
        _nonnegative_number(report["benchmark"]["modelCompilationMs"], description="model compilation")
        timings = report["benchmark"]["inferenceMs"]
        values = [
            _nonnegative_number(timings[field], description=f"inference {field}")
            for field in ("minimum", "p50", "p95", "maximum")
        ]
        if values != sorted(values):
            raise ArtifactReleaseError("Compatibility inference percentiles are inconsistent")
    except (KeyError, TypeError) as error:
        raise ArtifactReleaseError("Compatibility report is missing required evidence") from error


def finalize_artifact(
    *,
    policy_path: Path,
    artifact_path: Path,
    conversion_report_path: Path,
    compatibility_report_path: Path,
    approved_baseline_report_path: Path,
    approver: str,
    output_path: Path,
    schema_path: Path,
    repository_root: Path,
    approved_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not approver.strip():
        raise ArtifactReleaseError("Approver must not be empty")
    policy = validate_artifact_policy(
        read_json_object(policy_path, description="artifact policy")
    )
    conversion = read_json_object(conversion_report_path, description="conversion report")
    compatibility = read_json_object(
        compatibility_report_path, description="compatibility report"
    )
    approved_baseline = read_json_object(
        approved_baseline_report_path, description="approved baseline report"
    )
    artifact_hash = sha256_file(artifact_path, description="TFLite artifact")
    try:
        artifact_size = artifact_path.stat().st_size
    except OSError as error:
        raise ArtifactReleaseError("Could not inspect TFLite artifact") from error
    require_equal(
        sha256_file(approved_baseline_report_path, description="approved baseline report"),
        policy["approvedBaselineReportHash"],
        description="approved baseline report SHA-256",
    )
    try:
        require_equal(
            approved_baseline["approval"]["status"],
            "approved",
            description="baseline approval status",
        )
    except (KeyError, TypeError) as error:
        raise ArtifactReleaseError("Approved baseline report is missing approval evidence") from error
    _validate_conversion_report(
        conversion,
        policy,
        artifact_hash=artifact_hash,
        artifact_size=artifact_size,
        policy_hash=sha256_file(policy_path, description="artifact policy"),
        lockfile_hash=sha256_file(
            schema_path.parent / "uv.lock", description="model lockfile"
        ),
    )
    _validate_compatibility_report(
        compatibility, policy, artifact_hash=artifact_hash, artifact_size=artifact_size
    )
    manifest = {
        "schemaVersion": 1,
        "releaseId": policy["releaseId"],
        "modelId": policy["modelId"],
        "semanticVersion": policy["semanticVersion"],
        "artifact": {"sha256": artifact_hash, "sizeBytes": artifact_size},
        "trainingCommit": policy["trainingCommit"],
        "datasetManifestHash": policy["datasetManifestHash"],
        "labels": policy["labels"],
        "input": policy["input"],
        "output": policy["output"],
        "quantizationMode": policy["quantization"]["mode"],
        "thresholdsVersion": policy["thresholdsVersion"],
        "runtime": {
            "package": policy["runtime"]["package"],
            "minimumVersion": policy["runtime"]["version"],
            "accelerator": policy["runtime"]["accelerator"],
        },
        "evidence": {
            "approvedBaselineReportHash": policy["approvedBaselineReportHash"],
            "conversionReportHash": sha256_file(
                conversion_report_path, description="conversion report"
            ),
            "compatibilityReportHash": sha256_file(
                compatibility_report_path, description="compatibility report"
            ),
        },
        "approval": {
            "status": "approved",
            "approvedAt": approved_at or datetime.now(UTC).isoformat(),
            "approver": approver.strip(),
            "notes": APPROVAL_NOTE,
        },
    }
    try:
        validate_manifest_schema(manifest, schema_path=schema_path)
    except ValidationError as error:
        raise ArtifactReleaseError("Approved artifact manifest is invalid") from error
    validate_new_protected_path(output_path, repository_root=repository_root)
    write_private_json(output_path, manifest)
    summary = {
        "releaseId": manifest["releaseId"],
        "modelId": manifest["modelId"],
        "semanticVersion": manifest["semanticVersion"],
        "artifact": manifest["artifact"],
        "quantizationMode": manifest["quantizationMode"],
        "parity": conversion["parity"],
        "runtime": manifest["runtime"],
        "benchmark": compatibility["benchmark"],
        "evidence": manifest["evidence"],
    }
    return manifest, summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Approve protected TFLite conversion and browser evidence."
    )
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--conversion-report", type=Path, required=True)
    parser.add_argument("--compatibility-report", type=Path, required=True)
    parser.add_argument("--approved-baseline-report", type=Path, required=True)
    parser.add_argument("--approver", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    repository_root = Path(__file__).parents[3]
    try:
        _, summary = finalize_artifact(
            policy_path=args.policy,
            artifact_path=args.artifact,
            conversion_report_path=args.conversion_report,
            compatibility_report_path=args.compatibility_report,
            approved_baseline_report_path=args.approved_baseline_report,
            approver=args.approver,
            output_path=args.output,
            schema_path=repository_root / "model" / "manifest.schema.json",
            repository_root=repository_root,
        )
    except ArtifactReleaseError as error:
        raise SystemExit(f"Artifact finalization failed: {error}") from error
    print(json.dumps(summary, indent=2))
if __name__ == "__main__":
    main()
