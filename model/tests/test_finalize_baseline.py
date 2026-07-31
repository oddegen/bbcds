from __future__ import annotations

import json
import stat
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest

from bbcds_model.constants import LABELS
from bbcds_model.finalize_baseline import (
    FinalizationError,
    finalize_baseline,
    main,
    validate_protected_output_path,
)
from bbcds_model.manifest import sha256_file
from bbcds_model.validation_report import (
    build_baseline_validation_report,
    protected_reference,
    validate_baseline_report,
)

SCHEMA = Path(__file__).parents[1] / "baseline-validation.schema.json"
APPROVED_AT = "2026-07-31T12:00:00+00:00"


@dataclass(frozen=True)
class Evidence:
    policy: Path
    manifest: Path
    audit: Path
    draft: Path
    checkpoint: Path
    confusion: Path


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_evidence(tmp_path: Path) -> Evidence:
    rows = [
        {
            "path": f"private-{split}-{index}.png",
            "label": label,
            "source_id": f"source-{split}-{index}",
            "split": split,
            "media_type": "image",
            "license": "research-test",
            "sha256": f"{index + 1:064x}",
        }
        for split in ("train", "validation", "test")
        for index, label in enumerate(LABELS)
    ]
    manifest = tmp_path / "dataset.csv"
    pd.DataFrame(rows).to_csv(manifest, index=False)

    audit = tmp_path / "dataset.audit.json"
    _write_json(
        audit,
        {
            "schemaVersion": 1,
            "profile": "deepghs-nsfw-detect",
            "seed": 7,
            "splitRatios": {"train": 0.8, "validation": 0.1, "test": 0.1},
            "scannedCount": 12,
            "acceptedCount": 12,
            "sourceGroupCount": 12,
            "splits": {"train": 4, "validation": 4, "test": 4},
            "labels": {label: 3 for label in LABELS},
            "exactDuplicateCount": 0,
            "nearDuplicateClusterCount": 0,
            "conflictingClusterRecordCount": 0,
            "corruptCount": 0,
            "policyExcludedCount": 0,
        },
    )

    checkpoint = tmp_path / "final.keras"
    checkpoint.write_bytes(b"synthetic checkpoint")
    confusion = tmp_path / "validation-confusion-matrix.json"
    _write_json(
        confusion,
        {
            "split": "validation",
            "confusionMatrix": [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ],
            "threshold": {
                "threshold": 0.43,
                "precision": 1.0,
                "recall": 1.0,
                "f1": 1.0,
            },
            "binaryPolicy": {"precision": 1.0, "recall": 1.0, "f1": 1.0},
        },
    )

    per_class = [
        {"label": label, "support": 1, "precision": 1.0, "recall": 1.0, "f1": 1.0}
        for label in LABELS
    ]
    draft = tmp_path / "baseline-validation-draft.json"
    report = build_baseline_validation_report(
        report_id="baseline-test",
        training_commit="abcdef123456",
        dataset_manifest_hash=sha256_file(manifest),
        checkpoint_reference=protected_reference(
            kind="protected-file",
            uri="protected://model-runs/final.keras",
            sha256=sha256_file(checkpoint),
        ),
        confusion_matrix_reference=protected_reference(
            kind="protected-file",
            uri="protected://model-runs/validation-confusion-matrix.json",
            sha256=sha256_file(confusion),
        ),
        split_name="validation",
        split_record_count=4,
        split_source_group_count=4,
        metrics={"macroF1": 1.0, "perClass": per_class},
        limitations=["Synthetic test evidence."],
        threshold_rationale="Synthetic test threshold.",
        calibration_status="exploratory",
        calibration_notes="Synthetic test calibration.",
    )
    _write_json(draft, report)

    policy = tmp_path / "baseline-policy.json"
    evidence = Evidence(policy, manifest, audit, draft, checkpoint, confusion)
    _write_json(
        policy,
        {
            "schemaVersion": 1,
            "releaseId": "baseline-test-v1",
            "reportId": report["reportId"],
            "trainingCommit": report["trainingCommit"],
            "datasetManifestHash": sha256_file(manifest),
            "datasetAuditHash": sha256_file(audit),
            "draftReportHash": sha256_file(draft),
            "checkpointHash": sha256_file(checkpoint),
            "confusionMatrixHash": sha256_file(confusion),
            "profile": "deepghs-nsfw-detect",
            "seed": 7,
            "labels": list(LABELS),
            "evaluationSplit": report["evaluation"]["split"],
            "threshold": 0.43,
            "calibrationStatus": "exploratory",
        },
    )
    return evidence


def _repin(evidence: Evidence) -> None:
    policy = json.loads(evidence.policy.read_text(encoding="utf-8"))
    policy.update(
        datasetManifestHash=sha256_file(evidence.manifest),
        datasetAuditHash=sha256_file(evidence.audit),
        draftReportHash=sha256_file(evidence.draft),
        checkpointHash=sha256_file(evidence.checkpoint),
        confusionMatrixHash=sha256_file(evidence.confusion),
    )
    _write_json(evidence.policy, policy)


def _finalize(evidence: Evidence):
    return finalize_baseline(
        policy_path=evidence.policy,
        manifest_path=evidence.manifest,
        audit_path=evidence.audit,
        draft_path=evidence.draft,
        checkpoint_path=evidence.checkpoint,
        confusion_matrix_path=evidence.confusion,
        approver="project-owner",
        schema_path=SCHEMA,
        approved_at=APPROVED_AT,
    )


def _cli_args(evidence: Evidence, output: Path) -> list[str]:
    return [
        "--policy",
        str(evidence.policy),
        "--manifest",
        str(evidence.manifest),
        "--audit",
        str(evidence.audit),
        "--draft",
        str(evidence.draft),
        "--checkpoint",
        str(evidence.checkpoint),
        "--confusion-matrix",
        str(evidence.confusion),
        "--approver",
        "project-owner",
        "--output",
        str(output),
    ]


def test_cli_approves_schema_valid_report_and_prints_only_aggregates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence = _write_evidence(tmp_path)
    output = tmp_path / "approved.json"
    monkeypatch.setattr(
        "bbcds_model.finalize_baseline.validate_protected_output_path",
        lambda *args, **kwargs: None,
    )

    main(_cli_args(evidence, output))

    approved = json.loads(output.read_text(encoding="utf-8"))
    validate_baseline_report(approved, schema_path=SCHEMA)
    assert approved["approval"]["status"] == "approved"
    assert approved["approval"]["approver"] == "project-owner"
    assert stat.S_IMODE(output.stat().st_mode) == 0o600

    summary = capsys.readouterr().out
    assert json.loads(summary)["sourceGroupsBySplit"]["validation"] == 4
    assert all(
        fragment not in summary.lower()
        for fragment in ("private-", "source-", "path", "url", "probabilit")
    )


@pytest.mark.parametrize(
    "target", ["manifest", "audit", "draft", "checkpoint", "confusion"]
)
def test_rejects_protected_artifact_hash_mismatch(tmp_path: Path, target: str) -> None:
    evidence = _write_evidence(tmp_path)
    path = getattr(evidence, target)
    if path.suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        if target == "draft":
            value["createdAt"] = "2026-07-31T13:00:00+00:00"
        else:
            value["tampered"] = True
        _write_json(path, value)
    else:
        path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(FinalizationError, match="(?i)SHA-256"):
        _finalize(evidence)


def test_rejects_audit_aggregate_mismatch(tmp_path: Path) -> None:
    evidence = _write_evidence(tmp_path)
    audit = json.loads(evidence.audit.read_text(encoding="utf-8"))
    audit["acceptedCount"] = 11
    _write_json(evidence.audit, audit)
    _repin(evidence)

    with pytest.raises(FinalizationError, match="acceptedCount"):
        _finalize(evidence)


@pytest.mark.parametrize("defect", ["source-leakage", "unknown-label"])
def test_rejects_invalid_manifest_contract(tmp_path: Path, defect: str) -> None:
    evidence = _write_evidence(tmp_path)
    manifest = pd.read_csv(evidence.manifest)
    if defect == "source-leakage":
        manifest.loc[manifest["split"] == "validation", "source_id"] = "source-train-0"
    else:
        manifest.loc[0, "label"] = "Not canonical"
    manifest.to_csv(evidence.manifest, index=False)

    draft = json.loads(evidence.draft.read_text(encoding="utf-8"))
    draft["datasetManifestHash"] = sha256_file(evidence.manifest)
    _write_json(evidence.draft, draft)
    _repin(evidence)

    with pytest.raises(FinalizationError, match="manifest is invalid"):
        _finalize(evidence)


def test_rejects_validation_count_mismatch(tmp_path: Path) -> None:
    evidence = _write_evidence(tmp_path)
    draft = json.loads(evidence.draft.read_text(encoding="utf-8"))
    draft["evaluation"]["split"]["recordCount"] = 3
    _write_json(evidence.draft, draft)
    policy = json.loads(evidence.policy.read_text(encoding="utf-8"))
    policy["evaluationSplit"]["recordCount"] = 3
    _write_json(evidence.policy, policy)
    _repin(evidence)

    with pytest.raises(FinalizationError, match="record count"):
        _finalize(evidence)


def test_rejects_unsafe_or_existing_output_paths(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    protected = tmp_path / "protected"
    temporary = tmp_path / "temporary"
    repository.mkdir()
    protected.mkdir()
    temporary.mkdir()

    for target, message in (
        (repository / "approved.json", "Git worktree"),
        (temporary / "approved.json", "temporary storage"),
    ):
        with pytest.raises(FinalizationError, match=message):
            validate_protected_output_path(
                target, repository_root=repository, temporary_root=temporary
            )

    existing = protected / "approved.json"
    existing.write_text("existing", encoding="utf-8")
    with pytest.raises(FinalizationError, match="refusing to overwrite"):
        validate_protected_output_path(
            existing, repository_root=repository, temporary_root=temporary
        )


def test_cli_errors_do_not_expose_protected_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    evidence = _write_evidence(tmp_path)
    missing = tmp_path / "sensitive-name.csv"

    with pytest.raises(SystemExit, match="2"):
        missing_evidence = Evidence(
            evidence.policy,
            missing,
            evidence.audit,
            evidence.draft,
            evidence.checkpoint,
            evidence.confusion,
        )
        main(_cli_args(missing_evidence, tmp_path / "approved.json"))

    error = capsys.readouterr().err
    assert str(missing) not in error
    assert "traceback" not in error.lower()
