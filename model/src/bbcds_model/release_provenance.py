"""Reproducibility metadata for protected artifact conversion evidence."""

from __future__ import annotations

import platform
import re
import subprocess
from pathlib import Path
from typing import Any

import tensorflow as tf
from tensorflow import keras

from bbcds_model.protected_io import ProtectedEvidenceError, sha256_file


def collect_provenance(*, policy_path: Path, repository_root: Path) -> dict[str, Any]:
    lockfile = repository_root / "model" / "uv.lock"
    try:
        result = subprocess.run(
            ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ProtectedEvidenceError("Could not determine release source commit") from error
    source_commit = result.stdout.strip()
    if not re.fullmatch(r"[a-f0-9]{40}", source_commit):
        raise ProtectedEvidenceError("Release source commit is invalid")
    return {
        "policyHash": sha256_file(policy_path, description="artifact policy"),
        "sourceCommit": source_commit,
        "lockfileHash": sha256_file(lockfile, description="model lockfile"),
        "toolchain": {
            "pythonVersion": platform.python_version(),
            "tensorflowVersion": tf.__version__,
            "kerasVersion": keras.__version__,
        },
    }
