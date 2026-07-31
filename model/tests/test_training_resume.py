from __future__ import annotations

from pathlib import Path

import pytest
from tensorflow import keras

from bbcds_model.train import restore_training_model


def _tiny_model() -> keras.Model:
    inputs = keras.Input(shape=(4,), name="image")
    backbone_inputs = keras.Input(shape=(4,))
    backbone_outputs = keras.layers.Dense(3)(backbone_inputs)
    backbone = keras.Model(backbone_inputs, backbone_outputs, name="test_backbone")
    outputs = keras.layers.Dense(4, activation="softmax", name="probabilities")(backbone(inputs))
    return keras.Model(inputs, outputs)


def test_restore_training_model_uses_latest_completed_stage(tmp_path: Path) -> None:
    model = _tiny_model()
    model.save(tmp_path / "head-final.keras")

    restored, backbone, stage = restore_training_model(output_dir=tmp_path, resume=True)
    assert restored.output_shape == (None, 4)
    assert backbone.name == "test_backbone"
    assert stage == "head"

    model.save(tmp_path / "fine-tune-final.keras")
    _, _, stage = restore_training_model(output_dir=tmp_path, resume=True)
    assert stage == "fine-tune"

    (tmp_path / "fine-tune-final.keras").write_text("corrupt")
    _, _, stage = restore_training_model(output_dir=tmp_path, resume=True)
    assert stage == "head"

    (tmp_path / "head-final.keras").write_text("corrupt")
    with pytest.raises(RuntimeError, match="No valid completed"):
        restore_training_model(output_dir=tmp_path, resume=True)


def test_restore_training_model_requires_explicit_resume(tmp_path: Path) -> None:
    _tiny_model().save(tmp_path / "head-final.keras")

    with pytest.raises(FileExistsError, match="pass --resume"):
        restore_training_model(output_dir=tmp_path, resume=False)
