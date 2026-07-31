from __future__ import annotations

import numpy as np

from bbcds_model.evaluate import classification_report, frame_risk, select_threshold


def test_frame_risk_collapses_policy_classes() -> None:
    probabilities = np.array(
        [
            [0.9, 0.1, 0.0, 0.0],
            [0.0, 0.0, 0.8, 0.1],
            [0.0, 0.5, 0.0, 0.0],
        ]
    )

    risks = frame_risk(probabilities)

    assert np.allclose(risks, [0.035, 0.9, 0.175])


def test_select_threshold_prefers_precision_when_recall_gate_is_met() -> None:
    y_true = np.array([False, False, True, True])
    risks = np.array([0.1, 0.2, 0.8, 0.9])

    selected = select_threshold(y_true, risks)

    assert selected.recall >= 0.9
    assert selected.precision == 1.0


def test_classification_report_returns_schema_ready_per_class_metrics() -> None:
    y_true = np.array([0, 1, 2, 3])
    probabilities = np.array(
        [
            [0.8, 0.1, 0.1, 0.0],
            [0.1, 0.7, 0.1, 0.1],
            [0.0, 0.1, 0.8, 0.1],
            [0.0, 0.1, 0.2, 0.7],
        ]
    )

    report = classification_report(y_true, probabilities)

    assert report["macroF1"] == 1.0
    assert len(report["perClass"]) == 4
    assert report["confusionMatrix"] == [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
