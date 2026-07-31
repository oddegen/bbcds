"""MobileNetV3-Small baseline classifier."""

from __future__ import annotations

import tensorflow as tf
from tensorflow import keras

from bbcds_model.constants import IMAGE_SIZE, LABELS


def build_classifier(
    *,
    num_classes: int = len(LABELS),
    dropout_rate: float = 0.25,
    alpha: float = 1.0,
) -> tuple[keras.Model, keras.Model]:
    inputs = keras.Input(shape=(IMAGE_SIZE, IMAGE_SIZE, 3), dtype=tf.float32, name="image")

    backbone = keras.applications.MobileNetV3Small(
        input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3),
        alpha=alpha,
        minimalistic=False,
        include_top=False,
        weights="imagenet",
        pooling="avg",
        include_preprocessing=True,
    )
    backbone.trainable = False

    features = backbone(inputs, training=False)
    features = keras.layers.Dropout(dropout_rate, name="classifier_dropout")(features)
    outputs = keras.layers.Dense(
        num_classes,
        activation="softmax",
        dtype=tf.float32,
        name="probabilities",
    )(features)

    return keras.Model(inputs=inputs, outputs=outputs, name="bbcds_mobilenet_v3_small"), backbone
