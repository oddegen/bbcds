from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from bbcds_model.constants import LABELS
from bbcds_model.manifest import load_training_manifest
from bbcds_model.prepare_manifest import build_manifest

FOLDER_COLORS = {
    "neutral": (30, 60, 90),
    "drawings": (190, 80, 20),
    "sexy": (80, 150, 40),
    "porn": (160, 30, 100),
    "hentai": (60, 40, 180),
}


def _write_dataset(root: Path, *, records_per_folder: int = 12) -> None:
    for folder_name, base_color in FOLDER_COLORS.items():
        folder = root / folder_name
        folder.mkdir(parents=True)
        for index in range(records_per_folder):
            rng = random.Random(f"{folder_name}-{index}")
            image = Image.new("RGB", (32, 32), color=base_color)
            for x in range(image.width):
                for y in range(image.height):
                    if rng.random() < 0.35:
                        image.putpixel(
                            (x, y),
                            tuple(rng.randrange(256) for _ in range(3)),
                        )
            image.save(folder / f"fixture-{index}.png")


def test_build_manifest_is_deterministic_and_valid(tmp_path: Path) -> None:
    dataset_root = tmp_path / "images"
    _write_dataset(dataset_root)

    first_path = tmp_path / "first" / "dataset.csv"
    second_path = tmp_path / "second" / "dataset.csv"
    first, first_audit = build_manifest(
        dataset_root=dataset_root,
        output_path=first_path,
        profile="deepghs-nsfw-detect",
        license_name="research-test",
        seed=42,
        maximum_hamming_distance=0,
    )
    second, second_audit = build_manifest(
        dataset_root=dataset_root,
        output_path=second_path,
        profile="deepghs-nsfw-detect",
        license_name="research-test",
        seed=42,
        maximum_hamming_distance=0,
    )

    comparable_columns = ["label", "source_id", "split", "media_type", "license", "sha256"]
    pd.testing.assert_frame_equal(
        first[comparable_columns].reset_index(drop=True),
        second[comparable_columns].reset_index(drop=True),
    )
    assert first_audit == second_audit
    assert set(first["label"]) == set(LABELS)
    assert set(first["split"]) == {"train", "validation", "test"}
    assert first.groupby("source_id")["split"].nunique().max() == 1
    split_ratios = first["split"].value_counts(normalize=True)
    assert split_ratios["train"] == pytest.approx(0.8, abs=0.05)
    assert split_ratios["validation"] == pytest.approx(0.1, abs=0.05)
    assert split_ratios["test"] == pytest.approx(0.1, abs=0.05)
    load_training_manifest(first_path)


def test_build_manifest_quarantines_bad_and_duplicate_records(tmp_path: Path) -> None:
    dataset_root = tmp_path / "images"
    _write_dataset(dataset_root, records_per_folder=5)
    corrupt = dataset_root / "neutral" / "corrupt.png"
    corrupt.write_text("not an image")

    exact_source = dataset_root / "porn" / "fixture-0.png"
    (dataset_root / "porn" / "duplicate.png").write_bytes(exact_source.read_bytes())

    conflicting_source = dataset_root / "hentai" / "fixture-0.png"
    (dataset_root / "neutral" / "conflict.png").write_bytes(conflicting_source.read_bytes())

    output_path = tmp_path / "dataset.csv"
    manifest, audit = build_manifest(
        dataset_root=dataset_root,
        output_path=output_path,
        profile="deepghs-nsfw-detect",
        license_name="research-test",
        seed=7,
        maximum_hamming_distance=0,
    )

    assert audit["corruptCount"] == 1
    assert audit["exactDuplicateCount"] == 2
    assert audit["conflictingClusterRecordCount"] == 2
    assert len(manifest) == 24


def test_audit_contains_only_aggregate_data(tmp_path: Path) -> None:
    dataset_root = tmp_path / "sensitive-dataset-name"
    _write_dataset(dataset_root)
    output_path = tmp_path / "dataset.csv"

    build_manifest(
        dataset_root=dataset_root,
        output_path=output_path,
        profile="deepghs-nsfw-detect",
        license_name="research-test",
        seed=11,
        maximum_hamming_distance=0,
    )

    audit_text = output_path.with_suffix(".audit.json").read_text()
    audit = json.loads(audit_text)
    assert "sensitive-dataset-name" not in audit_text
    assert "fixture-" not in audit_text
    assert "path" not in audit_text.lower()
    assert "url" not in audit_text.lower()
    assert "probabilit" not in audit_text.lower()
    assert audit["acceptedCount"] == 60
