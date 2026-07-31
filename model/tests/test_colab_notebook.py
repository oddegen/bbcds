from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def test_colab_notebook_has_safe_recoverable_workflow() -> None:
    notebook_path = Path(__file__).parents[1] / "notebooks" / "train-colab.ipynb"
    notebook: dict[str, Any] = json.loads(notebook_path.read_text())
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") in {"code", "markdown"}
    )

    assert notebook["nbformat"] == 4
    assert "bbcds_model.prepare_manifest" in source
    assert "bbcds_model.train" in source
    assert '"--resume"' in source
    assert 'drive.mount("/content/drive")' in source
    assert "shutil.rmtree(DATA_ROOT" in source
    assert "from google.colab import errors" not in source
    assert "except userdata.SecretNotFoundError:" in source
    assert "except Exception as exc:" not in source
    assert "if gpu_check.returncode != 0:" in source
    assert "print(gpu_check.stderr)" in source
    assert 'RuntimeError("TensorFlow GPU check failed.")' in source
    assert not re.search(r"\b(?:hf|github_pat)_[A-Za-z0-9_]{10,}\b", source)
    assert all(
        cell.get("outputs", []) == []
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
