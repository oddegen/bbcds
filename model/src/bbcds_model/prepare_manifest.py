"""Build a protected training manifest from an image-folder dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import string
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import imagehash
import pandas as pd
from PIL import Image, UnidentifiedImageError

from bbcds_model.constants import CLASS_TO_ID, LABELS
from bbcds_model.manifest import load_training_manifest, sha256_file

DEFAULT_SEED: Final = 20260731
DEFAULT_LICENSE: Final = (
    "MIT-dataset-card; underlying-media-rights-unverified; research-only"
)
SHA256_HEX_LENGTH: Final = 64
PERCEPTUAL_HASH_BITS: Final = 64
SUPPORTED_EXTENSIONS: Final = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
SPLIT_RATIOS: Final = {"train": 0.8, "validation": 0.1, "test": 0.1}
PROFILE_LABELS: Final = {
    "deepghs-nsfw-detect": {
        "neutral": "Safe",
        "drawing": "Safe",
        "drawings": "Safe",
        "sexy": "Suggestive",
        "porn": "Explicit",
        "hentai": "Explicit Illustration",
    }
}


class PreparationError(ValueError):
    """Raised when a folder dataset cannot produce a valid manifest."""


@dataclass(frozen=True)
class Candidate:
    path: Path
    label: str
    sha256: str
    perceptual_hash: int


@dataclass
class HammingNode:
    value: int
    children: dict[int, HammingNode] = field(default_factory=dict)


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parents = list(range(size))

    def find(self, value: int) -> int:
        while self.parents[value] != value:
            self.parents[value] = self.parents[self.parents[value]]
            value = self.parents[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parents[right_root] = left_root


class HammingTree:
    """BK-tree for bounded Hamming-distance searches over 64-bit hashes."""

    def __init__(self) -> None:
        self.root: HammingNode | None = None

    @staticmethod
    def distance(left: int, right: int) -> int:
        return (left ^ right).bit_count()

    def add(self, value: int) -> None:
        if self.root is None:
            self.root = HammingNode(value)
            return

        node = self.root
        while True:
            distance = self.distance(value, node.value)
            child = node.children.get(distance)
            if child is None:
                node.children[distance] = HammingNode(value)
                return
            node = child

    def query(self, value: int, maximum_distance: int) -> list[int]:
        if self.root is None:
            return []

        matches: list[int] = []
        pending = [self.root]
        while pending:
            node = pending.pop()
            distance = self.distance(value, node.value)
            if distance <= maximum_distance:
                matches.append(node.value)
            minimum = distance - maximum_distance
            maximum = distance + maximum_distance
            pending.extend(
                child
                for edge, child in node.children.items()
                if minimum <= edge <= maximum
            )
        return matches


def _read_excluded_hashes(path: Path | None) -> set[str]:
    if path is None:
        return set()
    values = {
        line.strip().lower()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    invalid = sorted(
        value
        for value in values
        if len(value) != SHA256_HEX_LENGTH
        or any(character not in string.hexdigits for character in value)
    )
    if invalid:
        raise PreparationError("Exclusion list contains invalid SHA-256 values")
    return values


def _image_hash(path: Path) -> int:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        image.seek(0)
        return int(str(imagehash.phash(image.convert("RGB"))), 16)


def _profile_directories(dataset_root: Path, profile: str) -> list[tuple[Path, str]]:
    mapping = PROFILE_LABELS.get(profile)
    if mapping is None:
        raise PreparationError(f"Unknown dataset profile: {profile}")
    if not dataset_root.is_dir():
        raise PreparationError(f"Dataset root does not exist: {dataset_root}")

    directories = {path.name: path for path in dataset_root.iterdir() if path.is_dir()}
    required = {"neutral", "sexy", "porn", "hentai"}
    if not required.issubset(directories) or not ({"drawing", "drawings"} & directories.keys()):
        raise PreparationError("Dataset profile folders are incomplete")

    return [
        (directories[folder_name], label)
        for folder_name, label in mapping.items()
        if folder_name in directories
    ]


def scan_dataset(
    dataset_root: Path,
    *,
    profile: str,
    excluded_hashes: set[str],
) -> tuple[list[Candidate], dict[str, int]]:
    candidates: list[Candidate] = []
    counts = Counter[str]()
    for folder, label in _profile_directories(dataset_root, profile):
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            counts["scanned"] += 1
            try:
                digest = sha256_file(path)
                if digest in excluded_hashes:
                    counts["policyExcluded"] += 1
                    continue
                perceptual_hash = _image_hash(path)
            except (OSError, UnidentifiedImageError, ValueError):
                counts["corrupt"] += 1
                continue
            candidates.append(
                Candidate(
                    path=path,
                    label=label,
                    sha256=digest,
                    perceptual_hash=perceptual_hash,
                )
            )
    if not candidates:
        raise PreparationError("No valid images were found")
    return candidates, dict(counts)


def group_candidates(
    candidates: list[Candidate],
    *,
    maximum_hamming_distance: int = 4,
) -> tuple[list[list[Candidate]], dict[str, int]]:
    if not 0 <= maximum_hamming_distance <= PERCEPTUAL_HASH_BITS:
        raise PreparationError(
            f"Maximum Hamming distance must be between 0 and {PERCEPTUAL_HASH_BITS}"
        )

    by_digest: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in candidates:
        by_digest[candidate.sha256].append(candidate)

    conflicting_exact_groups = [
        group for group in by_digest.values() if len({candidate.label for candidate in group}) > 1
    ]
    unique = [
        min(group, key=lambda item: str(item.path))
        for group in by_digest.values()
        if len({candidate.label for candidate in group}) == 1
    ]
    unique.sort(key=lambda item: str(item.path))
    exact_duplicate_count = len(candidates) - len(by_digest)

    disjoint_set = DisjointSet(len(unique))
    tree = HammingTree()
    representative_by_hash: dict[int, int] = {}
    for index, candidate in enumerate(unique):
        for nearby_hash in tree.query(candidate.perceptual_hash, maximum_hamming_distance):
            disjoint_set.union(index, representative_by_hash[nearby_hash])
        if candidate.perceptual_hash not in representative_by_hash:
            representative_by_hash[candidate.perceptual_hash] = index
            tree.add(candidate.perceptual_hash)

    clusters: dict[int, list[Candidate]] = defaultdict(list)
    for index, candidate in enumerate(unique):
        clusters[disjoint_set.find(index)].append(candidate)

    accepted: list[list[Candidate]] = []
    conflicting_records = sum(len(group) for group in conflicting_exact_groups)
    for cluster in clusters.values():
        if len({candidate.label for candidate in cluster}) != 1:
            conflicting_records += len(cluster)
            continue
        accepted.append(sorted(cluster, key=lambda item: str(item.path)))
    accepted.sort(key=lambda cluster: cluster[0].sha256)

    return accepted, {
        "exactDuplicateCount": exact_duplicate_count,
        "conflictingClusterRecordCount": conflicting_records,
        "nearDuplicateClusterCount": sum(len(cluster) > 1 for cluster in accepted),
    }


def assign_splits(
    clusters: list[list[Candidate]],
    *,
    seed: int,
) -> dict[str, str]:
    clusters_by_label: dict[str, list[list[Candidate]]] = defaultdict(list)
    for cluster in clusters:
        clusters_by_label[cluster[0].label].append(cluster)

    assignments: dict[str, str] = {}
    for label in LABELS:
        label_clusters = clusters_by_label[label]
        if len(label_clusters) < len(SPLIT_RATIOS):
            raise PreparationError(f"Label {label!r} needs at least three source groups")

        rng = random.Random(seed + CLASS_TO_ID[label])
        rng.shuffle(label_clusters)
        label_clusters.sort(key=len, reverse=True)
        targets = {
            split: sum(map(len, label_clusters)) * ratio
            for split, ratio in SPLIT_RATIOS.items()
        }
        totals = dict.fromkeys(SPLIT_RATIOS, 0)

        seeded_splits = ("train", "validation", "test")
        for cluster, split in zip(label_clusters[:3], seeded_splits, strict=True):
            assignments[_cluster_key(cluster)] = split
            totals[split] += len(cluster)

        for cluster in label_clusters[3:]:
            split = max(
                SPLIT_RATIOS,
                key=lambda name: targets[name] - totals[name],
            )
            assignments[_cluster_key(cluster)] = split
            totals[split] += len(cluster)
    return assignments


def _cluster_key(cluster: list[Candidate]) -> str:
    digests = "|".join(sorted(candidate.sha256 for candidate in cluster))
    return hashlib.sha256(digests.encode()).hexdigest()


def build_manifest(
    *,
    dataset_root: Path,
    output_path: Path,
    profile: str,
    license_name: str,
    seed: int,
    excluded_hashes_path: Path | None = None,
    maximum_hamming_distance: int = 4,
) -> tuple[pd.DataFrame, dict[str, object]]:
    candidates, scan_counts = scan_dataset(
        dataset_root,
        profile=profile,
        excluded_hashes=_read_excluded_hashes(excluded_hashes_path),
    )
    clusters, grouping_counts = group_candidates(
        candidates,
        maximum_hamming_distance=maximum_hamming_distance,
    )
    assignments = assign_splits(clusters, seed=seed)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for cluster in clusters:
        cluster_key = _cluster_key(cluster)
        source_id = f"source-{cluster_key[:24]}"
        for candidate in cluster:
            rows.append(
                {
                    "path": os.path.relpath(candidate.path, output_path.parent),
                    "label": candidate.label,
                    "source_id": source_id,
                    "split": assignments[cluster_key],
                    "media_type": "image",
                    "license": license_name,
                    "sha256": candidate.sha256,
                }
            )

    manifest = pd.DataFrame(rows).sort_values(
        ["split", "label", "source_id", "sha256"],
        kind="stable",
    )
    manifest.to_csv(output_path, index=False)
    load_training_manifest(output_path)

    split_counts = manifest["split"].value_counts().sort_index().to_dict()
    label_counts = manifest["label"].value_counts().reindex(LABELS, fill_value=0).to_dict()
    audit: dict[str, object] = {
        "schemaVersion": 1,
        "profile": profile,
        "seed": seed,
        "splitRatios": SPLIT_RATIOS,
        "scannedCount": scan_counts.get("scanned", 0),
        "acceptedCount": len(manifest),
        "corruptCount": scan_counts.get("corrupt", 0),
        "policyExcludedCount": scan_counts.get("policyExcluded", 0),
        **grouping_counts,
        "sourceGroupCount": manifest["source_id"].nunique(),
        "splits": {str(key): int(value) for key, value in split_counts.items()},
        "labels": {str(key): int(value) for key, value in label_counts.items()},
    }
    audit_path = output_path.with_suffix(".audit.json")
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    return manifest, audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a protected BBCDS training manifest")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=sorted(PROFILE_LABELS), required=True)
    parser.add_argument("--license", dest="license_name", default=DEFAULT_LICENSE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--exclude-hashes", type=Path)
    parser.add_argument("--maximum-hamming-distance", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _, audit = build_manifest(
        dataset_root=args.dataset_root,
        output_path=args.output,
        profile=args.profile,
        license_name=args.license_name,
        seed=args.seed,
        excluded_hashes_path=args.exclude_hashes,
        maximum_hamming_distance=args.maximum_hamming_distance,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
