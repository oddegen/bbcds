from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from bbcds_model.train import write_baseline_evidence
from bbcds_model.validation_report import validate_baseline_report


def test_write_baseline_evidence_writes_schema_valid_draft(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest_path = tmp_path / "dataset.csv"
    manifest = pd.DataFrame(
        [
            {
                "path": "private-a.png",
                "label": "Safe",
                "source_id": "source-000000000001",
                "split": "validation",
                "media_type": "image",
                "license": "internal-test",
                "sha256": "0" * 64,
            },
            {
                "path": "private-b.png",
                "label": "Explicit",
                "source_id": "source-000000000002",
                "split": "validation",
                "media_type": "image",
                "license": "internal-test",
                "sha256": "1" * 64,
            },
        ]
    )
    manifest.to_csv(manifest_path, index=False)
    final_model_path = tmp_path / "final.keras"
    final_model_path.write_bytes(b"model")

    def fake_collect_predictions(model, dataset):
        del model, dataset
        return (
            np.array([0, 2]),
            np.array(
                [
                    [0.9, 0.1, 0.0, 0.0],
                    [0.0, 0.1, 0.8, 0.1],
                ]
            ),
        )

    monkeypatch.setattr("bbcds_model.train.collect_predictions", fake_collect_predictions)

    evidence = write_baseline_evidence(
        output_dir=tmp_path / "run",
        manifest_path=manifest_path,
        manifest=manifest,
        validation_ds=object(),
        model=object(),
        final_model_path=final_model_path,
        training_commit="abcdef123456",
    )

    report_path = Path(evidence["validationReportPath"])
    assert report_path.is_file()

    validate_baseline_report(
        json.loads(report_path.read_text()),
        schema_path=Path(__file__).parents[1] / "baseline-validation.schema.json",
    )
    assert "private-a.png" not in report_path.read_text()
