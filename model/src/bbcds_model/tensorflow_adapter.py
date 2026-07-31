"""Version-checked access to TensorFlow graph freezing for TFLite export."""

from __future__ import annotations

import tensorflow as tf
from tensorflow import keras

from bbcds_model.constants import INPUT_SHAPE
from bbcds_model.protected_io import ProtectedEvidenceError

SUPPORTED_TENSORFLOW_MINOR = (2, 16)


def frozen_concrete_function(model: keras.Model) -> object:
    version = tuple(int(part) for part in tf.__version__.split(".")[:2])
    if version != SUPPORTED_TENSORFLOW_MINOR:
        raise ProtectedEvidenceError(
            "TensorFlow graph-freezing adapter does not support this version"
        )
    try:
        from tensorflow.python.framework.convert_to_constants import (  # type: ignore[attr-defined]
            convert_variables_to_constants_v2,
        )
    except ImportError as error:
        raise ProtectedEvidenceError(
            "TensorFlow graph-freezing adapter is unavailable"
        ) from error

    @tf.function(
        input_signature=[
            tf.TensorSpec(shape=INPUT_SHAPE, dtype=tf.float32, name="image")
        ]
    )
    def serving(image: tf.Tensor) -> tf.Tensor:
        return model(image, training=False)

    return convert_variables_to_constants_v2(serving.get_concrete_function())
