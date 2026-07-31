"""Protected evidence I/O shared by model release commands."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class ProtectedEvidenceError(ValueError):
    """Raised when protected evidence cannot be read or written safely."""


def read_json_object(path: Path, *, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProtectedEvidenceError(f"Could not read {description}") from error
    if not isinstance(value, dict):
        raise ProtectedEvidenceError(
            f"{description.capitalize()} must be a JSON object"
        )
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path, *, description: str) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ProtectedEvidenceError(f"Could not read {description}") from error
    return digest.hexdigest()


def validate_new_protected_path(
    path: Path,
    *,
    repository_root: Path,
    temporary_root: Path | None = None,
) -> None:
    resolved = path.resolve()
    if not resolved.parent.is_dir():
        raise ProtectedEvidenceError(
            "Protected output parent directory does not exist"
        )
    if resolved.is_relative_to(repository_root.resolve()):
        raise ProtectedEvidenceError(
            "Protected output must be outside the Git worktree"
        )
    temp_root = (temporary_root or Path(tempfile.gettempdir())).resolve()
    if resolved.is_relative_to(temp_root):
        raise ProtectedEvidenceError(
            "Protected output must not use temporary storage"
        )
    if resolved.exists():
        raise ProtectedEvidenceError(
            "Protected output already exists; refusing to overwrite it"
        )


def write_private_json(path: Path, value: Mapping[str, Any]) -> None:
    _write_exclusive(path, json.dumps(value, indent=2).encode() + b"\n")


def write_private_bytes(path: Path, value: bytes) -> None:
    _write_exclusive(path, value)


def _write_exclusive(path: Path, value: bytes) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ProtectedEvidenceError(
            "Protected output already exists; refusing to overwrite it"
        ) from error
    except OSError as error:
        raise ProtectedEvidenceError("Could not create protected output") from error
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(value)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
