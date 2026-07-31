"""Validation for the release-specific model artifact policy."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, TypedDict, cast

from bbcds_model.constants import INPUT_SHAPE, LABELS
from bbcds_model.protected_io import ProtectedEvidenceError

SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class ArtifactPolicy(TypedDict):
    schemaVersion: int
    releaseId: str
    modelId: str
    semanticVersion: str
    trainingCommit: str
    datasetManifestHash: str
    checkpointHash: str
    approvedBaselineReportHash: str
    labels: list[str]
    input: dict[str, Any]
    output: dict[str, Any]
    quantization: dict[str, Any]
    parity: dict[str, Any]
    runtime: dict[str, Any]
    thresholdsVersion: str


def require_equal(actual: object, expected: object, *, description: str) -> None:
    if actual != expected:
        raise ProtectedEvidenceError(
            f"{description.capitalize()} does not match release policy"
        )


def validate_artifact_policy(policy: Mapping[str, Any]) -> ArtifactPolicy:
    try:
        require_equal(policy["schemaVersion"], 1, description="policy schema version")
        require_equal(policy["labels"], list(LABELS), description="canonical labels")
        require_equal(
            policy["input"]["shape"], list(INPUT_SHAPE), description="input shape"
        )
        require_equal(policy["input"]["dtype"], "float32", description="input dtype")
        require_equal(policy["input"]["range"], [0, 255], description="input range")
        require_equal(
            policy["output"]["shape"],
            [1, len(LABELS)],
            description="output shape",
        )
        require_equal(
            policy["output"]["dtype"], "float32", description="output dtype"
        )
        require_equal(
            policy["output"]["semantics"],
            "probabilities",
            description="output semantics",
        )
        require_equal(
            policy["quantization"]["representativeSplit"],
            "train",
            description="representative split",
        )
        require_equal(
            policy["quantization"]["uniqueSourceGroups"],
            True,
            description="representative source isolation",
        )
        require_equal(
            policy["runtime"]["accelerator"], "wasm", description="accelerator"
        )
        require_equal(
            policy["runtime"]["browser"], "chromium", description="browser"
        )
        if not all(
            isinstance(policy[field], str) and policy[field]
            for field in (
                "releaseId",
                "modelId",
                "trainingCommit",
                "thresholdsVersion",
            )
        ):
            raise ProtectedEvidenceError("Artifact policy identifiers are invalid")
        if not SEMVER_PATTERN.fullmatch(policy["semanticVersion"]):
            raise ProtectedEvidenceError("Artifact policy semantic version is invalid")
        for field in (
            "datasetManifestHash",
            "checkpointHash",
            "approvedBaselineReportHash",
        ):
            if not SHA256_PATTERN.fullmatch(policy[field]):
                raise ProtectedEvidenceError("Artifact policy contains an invalid hash")
        quantization = policy["quantization"]
        if quantization["representativeSampleCount"] != (
            quantization["samplesPerLabel"] * len(LABELS)
        ):
            raise ProtectedEvidenceError(
                "Representative sample policy is inconsistent"
            )
        if quantization["mode"] != "int8-internal-float32-boundary":
            raise ProtectedEvidenceError("Quantization mode is unsupported")
        for field in (
            "minimumTop1Agreement",
            "maximumMacroF1Drop",
            "maximumBinaryPrecisionDrop",
            "maximumBinaryRecallDrop",
        ):
            value = policy["parity"][field]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= value <= 1
            ):
                raise ProtectedEvidenceError("Parity policy contains an invalid rate")
        for field in ("warmupIterations", "measuredIterations"):
            value = policy["runtime"][field]
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ProtectedEvidenceError(
                    "Compatibility iteration policy is invalid"
                )
        for field in ("package", "version"):
            if not isinstance(policy["runtime"][field], str) or not policy["runtime"][field]:
                raise ProtectedEvidenceError("Runtime policy is invalid")
    except (KeyError, TypeError) as error:
        raise ProtectedEvidenceError(
            "Artifact policy is missing required fields"
        ) from error
    return cast(ArtifactPolicy, policy)
