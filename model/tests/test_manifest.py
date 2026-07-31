from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from bbcds_model.constants import LABELS
from bbcds_model.manifest import ManifestError, load_training_manifest


def _write_image(path: Path) -> str:
    Image.new("RGB", (8, 6), color=(12, 34, 56)).save(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(tmp_path: Path) -> Path:
    rows = []
    for index, split in enumerate(["train", "validation", "test", "holdout"]):
        image_path = tmp_path / f"sample-{split}.png"
        digest = _write_image(image_path)
        rows.append(
            {
                "path": image_path.name,
                "label": LABELS[index],
                "source_id": f"source-{index:012d}",
                "split": split,
                "media_type": "image",
                "license": "internal-test",
                "sha256": digest,
            }
        )

    manifest_path = tmp_path / "dataset.csv"
    pd.DataFrame(rows).to_csv(manifest_path, index=False)
    return manifest_path


def test_load_training_manifest_accepts_valid_manifest(tmp_path: Path) -> None:
    manifest = load_training_manifest(_manifest(tmp_path))

    assert manifest["label"].tolist() == list(LABELS)


def test_load_training_manifest_rejects_source_split_leakage(tmp_path: Path) -> None:
    manifest_path = _manifest(tmp_path)
    manifest = pd.read_csv(manifest_path)
    manifest.loc[0, "source_id"] = manifest.loc[1, "source_id"]
    manifest.to_csv(manifest_path, index=False)

    with pytest.raises(ManifestError, match="Sources appear in multiple splits"):
        load_training_manifest(manifest_path)


def test_load_training_manifest_rejects_hash_mismatch(tmp_path: Path) -> None:
    manifest_path = _manifest(tmp_path)
    manifest = pd.read_csv(manifest_path)
    manifest.loc[0, "sha256"] = "0" * 64
    manifest.to_csv(manifest_path, index=False)

    with pytest.raises(ManifestError, match="SHA-256 mismatches"):
        load_training_manifest(manifest_path)
