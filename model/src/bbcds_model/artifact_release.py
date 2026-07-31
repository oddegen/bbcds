"""Shared safety and evidence helpers for protected model-artifact releases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator, FormatChecker
from numpy.typing import NDArray
from sklearn.metrics import f1_score, precision_score, recall_score

from bbcds_model.constants import CLASS_TO_ID, LABELS, SUGGESTIVE_RISK_WEIGHT
from bbcds_model.protected_io import (
    ProtectedEvidenceError,
    read_json_object,
    sha256_bytes,
    sha256_file,
    validate_new_protected_path,
    write_private_bytes,
    write_private_json,
)

ArtifactReleaseError = ProtectedEvidenceError

__all__ = [
    "ArtifactReleaseError",
    "fixed_threshold_metrics",
    "read_json_object",
    "require_equal",
    "sha256_bytes",
    "sha256_file",
    "validate_manifest_schema",
    "validate_new_protected_path",
    "validate_probabilities",
    "write_private_bytes",
    "write_private_json",
]


def require_equal(actual: object, expected: object, *, description: str) -> None:
    if actual != expected:
        raise ArtifactReleaseError(f"{description.capitalize()} does not match release policy")


def validate_probabilities(probabilities: NDArray[Any], *, description: str) -> NDArray[np.float32]:
    result = np.asarray(probabilities, dtype=np.float32)
    if result.ndim != 2 or result.shape[1] != len(LABELS):
        raise ArtifactReleaseError(f"{description.capitalize()} output shape is invalid")
    if not np.all(np.isfinite(result)):
        raise ArtifactReleaseError(f"{description.capitalize()} output contains non-finite values")
    if np.any(result < -1e-6) or np.any(result > 1.0 + 1e-6):
        raise ArtifactReleaseError(f"{description.capitalize()} output is not probabilistic")
    if not np.allclose(result.sum(axis=1), 1.0, atol=1e-2, rtol=0):
        raise ArtifactReleaseError(f"{description.capitalize()} probabilities do not sum to one")
    return result


def fixed_threshold_metrics(
    labels: NDArray[Any], probabilities: NDArray[Any], *, threshold: float
) -> dict[str, float]:
    values = validate_probabilities(probabilities, description="model")
    label_values = np.asarray(labels)
    predicted = np.argmax(values, axis=1)
    binary_targets = np.isin(
        label_values,
        [CLASS_TO_ID["Explicit"], CLASS_TO_ID["Explicit Illustration"]],
    )
    risks = np.clip(
        values[:, CLASS_TO_ID["Explicit"]]
        + values[:, CLASS_TO_ID["Explicit Illustration"]]
        + SUGGESTIVE_RISK_WEIGHT * values[:, CLASS_TO_ID["Suggestive"]],
        0.0,
        1.0,
    )
    binary_predictions = risks >= threshold
    return {
        "macroF1": float(
            f1_score(
                label_values,
                predicted,
                labels=np.arange(len(LABELS)),
                average="macro",
                zero_division=0,
            )
        ),
        "binaryPrecision": float(
            precision_score(binary_targets, binary_predictions, zero_division=0)
        ),
        "binaryRecall": float(
            recall_score(binary_targets, binary_predictions, zero_division=0)
        ),
    }


def validate_manifest_schema(manifest: dict[str, Any], *, schema_path: Path) -> None:
    schema = read_json_object(schema_path, description="artifact manifest schema")
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
