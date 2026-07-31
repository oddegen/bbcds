"""Evaluation helpers for classifier and policy metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
)

from bbcds_model.constants import CLASS_TO_ID, LABELS, SUGGESTIVE_RISK_WEIGHT


@dataclass(frozen=True)
class ThresholdResult:
    threshold: float
    precision: float
    recall: float
    f1: float


def frame_risk(probabilities: NDArray[Any]) -> NDArray[np.float32]:
    suggestive = probabilities[:, CLASS_TO_ID["Suggestive"]]
    explicit = probabilities[:, CLASS_TO_ID["Explicit"]]
    illustration = probabilities[:, CLASS_TO_ID["Explicit Illustration"]]
    return np.asarray(
        np.clip(explicit + illustration + SUGGESTIVE_RISK_WEIGHT * suggestive, 0.0, 1.0),
        dtype=np.float32,
    )


def binary_inappropriate_targets(labels: NDArray[Any]) -> NDArray[np.bool_]:
    return np.isin(labels, [CLASS_TO_ID["Explicit"], CLASS_TO_ID["Explicit Illustration"]])


def select_threshold(y_true_binary: NDArray[Any], risks: NDArray[Any]) -> ThresholdResult:
    candidates: list[ThresholdResult] = []

    for threshold in np.linspace(0.1, 0.95, 171):
        predicted = risks >= threshold
        candidates.append(
            ThresholdResult(
                threshold=float(threshold),
                precision=float(precision_score(y_true_binary, predicted, zero_division=0)),
                recall=float(recall_score(y_true_binary, predicted, zero_division=0)),
                f1=float(f1_score(y_true_binary, predicted, zero_division=0)),
            )
        )

    eligible = [candidate for candidate in candidates if candidate.recall >= 0.9]
    if eligible:
        return max(eligible, key=lambda item: item.precision)
    return max(candidates, key=lambda item: item.f1)


def classification_report(y_true: NDArray[Any], probabilities: NDArray[Any]) -> dict[str, object]:
    predicted = np.argmax(probabilities, axis=1)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        predicted,
        labels=np.arange(len(LABELS)),
        zero_division=0,
    )

    per_class = [
        {
            "label": label,
            "support": int(support[index]),
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(f1[index]),
        }
        for index, label in enumerate(LABELS)
    ]

    y_true_binary = binary_inappropriate_targets(y_true)
    risks = frame_risk(probabilities)
    threshold = select_threshold(y_true_binary, risks)
    binary_predicted = risks >= threshold.threshold

    return {
        "macroF1": float(
            f1_score(
                y_true,
                predicted,
                labels=np.arange(len(LABELS)),
                average="macro",
                zero_division=0,
            )
        ),
        "perClass": per_class,
        "confusionMatrix": confusion_matrix(
            y_true,
            predicted,
            labels=np.arange(len(LABELS)),
        ).tolist(),
        "threshold": threshold.__dict__,
        "binaryPolicy": {
            "precision": float(precision_score(y_true_binary, binary_predicted, zero_division=0)),
            "recall": float(recall_score(y_true_binary, binary_predicted, zero_division=0)),
            "f1": float(f1_score(y_true_binary, binary_predicted, zero_division=0)),
        },
    }
