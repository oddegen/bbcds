"""Training manifest loading and validation.

The CSV manifest handled here is a protected training input. It is intentionally
separate from the public JSON schemas in this repository, which define evidence
contracts rather than the local file paths needed by TensorFlow.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from pathlib import Path

import pandas as pd

from bbcds_model.constants import (
    CLASS_TO_ID,
    MEDIA_TYPES,
    REQUIRED_TRAINING_SPLITS,
    SPLITS,
)

REQUIRED_COLUMNS = ("path", "label", "source_id", "split", "media_type", "license", "sha256")


class ManifestError(ValueError):
    """Raised when a protected training manifest is invalid."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _missing_values(values: Iterable[str], allowed: Sequence[str]) -> list[str]:
    return sorted(set(values) - set(allowed))


def load_training_manifest(
    manifest_path: str | Path,
    *,
    verify_files: bool = True,
    verify_hashes: bool = True,
    required_splits: Sequence[str] = REQUIRED_TRAINING_SPLITS,
) -> pd.DataFrame:
    path = Path(manifest_path)
    manifest = pd.read_csv(path)
    validate_training_manifest(
        manifest,
        manifest_dir=path.parent,
        verify_files=verify_files,
        verify_hashes=verify_hashes,
        required_splits=required_splits,
    )
    return manifest


def validate_training_manifest(
    manifest: pd.DataFrame,
    *,
    manifest_dir: Path,
    verify_files: bool,
    verify_hashes: bool,
    required_splits: Sequence[str] = REQUIRED_TRAINING_SPLITS,
) -> None:
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(manifest.columns))
    if missing_columns:
        raise ManifestError(f"Missing manifest columns: {missing_columns}")

    if manifest.empty:
        raise ManifestError("Manifest must contain at least one row")

    unknown_labels = _missing_values(manifest["label"].astype(str), tuple(CLASS_TO_ID))
    if unknown_labels:
        raise ManifestError(f"Unknown labels: {unknown_labels}")

    unknown_splits = _missing_values(manifest["split"].astype(str), SPLITS)
    if unknown_splits:
        raise ManifestError(f"Unknown splits: {unknown_splits}")

    unknown_media_types = _missing_values(manifest["media_type"].astype(str), MEDIA_TYPES)
    if unknown_media_types:
        raise ManifestError(f"Unknown media types: {unknown_media_types}")

    present_splits = set(manifest["split"].astype(str))
    absent_required_splits = sorted(set(required_splits) - present_splits)
    if absent_required_splits:
        raise ManifestError(f"Missing required splits: {absent_required_splits}")

    split_counts = manifest.groupby("source_id", dropna=False)["split"].nunique()
    leaking_sources = split_counts[split_counts > 1].index.astype(str).tolist()
    if leaking_sources:
        raise ManifestError(f"Sources appear in multiple splits: {sorted(leaking_sources)}")

    if verify_files or verify_hashes:
        _validate_files(
            manifest,
            manifest_dir,
            verify_files=verify_files,
            verify_hashes=verify_hashes,
        )


def _validate_files(
    manifest: pd.DataFrame,
    manifest_dir: Path,
    *,
    verify_files: bool,
    verify_hashes: bool,
) -> None:
    missing_paths: list[str] = []
    mismatched_hashes: list[str] = []

    for row in manifest.itertuples(index=False):
        raw_path = Path(str(row.path))
        resolved_path = raw_path if raw_path.is_absolute() else manifest_dir / raw_path

        if verify_files and not resolved_path.is_file():
            missing_paths.append(str(raw_path))
            continue

        if verify_hashes and resolved_path.is_file():
            actual_hash = sha256_file(resolved_path)
            expected_hash = str(row.sha256)
            if actual_hash != expected_hash:
                mismatched_hashes.append(str(raw_path))

    if missing_paths:
        raise ManifestError(f"Missing image files: {missing_paths[:10]}")

    if mismatched_hashes:
        raise ManifestError(f"SHA-256 mismatches: {mismatched_hashes[:10]}")


def attach_training_columns(manifest: pd.DataFrame, *, manifest_dir: Path) -> pd.DataFrame:
    prepared = manifest.copy()
    prepared["label_id"] = prepared["label"].map(CLASS_TO_ID).astype("int32")
    prepared["path_resolved"] = prepared["path"].map(
        lambda raw_path: str(
            Path(str(raw_path))
            if Path(str(raw_path)).is_absolute()
            else manifest_dir / Path(str(raw_path))
        )
    )
    return prepared


def split_manifest(manifest: pd.DataFrame, split: str) -> pd.DataFrame:
    if split not in SPLITS:
        raise ManifestError(f"Unknown split: {split}")
    return manifest[manifest["split"] == split].copy()


def count_source_groups(manifest: pd.DataFrame, split: str) -> int:
    return int(split_manifest(manifest, split)["source_id"].nunique())
