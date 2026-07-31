"""TensorFlow dataset pipeline for the image classifier."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import tensorflow as tf
from tensorflow import keras

from bbcds_model.constants import IMAGE_SIZE, REQUIRED_TRAINING_SPLITS
from bbcds_model.manifest import (
    attach_training_columns,
    load_training_manifest,
    split_manifest,
)

AUTOTUNE = tf.data.AUTOTUNE

AUGMENTATION = keras.Sequential(
    [
        keras.layers.RandomFlip("horizontal"),
        keras.layers.RandomZoom(height_factor=(-0.08, 0.08), width_factor=(-0.08, 0.08)),
        keras.layers.RandomContrast(0.15),
        keras.layers.RandomRotation(0.03),
    ],
    name="training_augmentation",
)


def decode_and_letterbox(path: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
    encoded = tf.io.read_file(path)
    image = tf.io.decode_image(encoded, channels=3, expand_animations=False)
    image.set_shape([None, None, 3])
    image = tf.image.resize_with_pad(image, IMAGE_SIZE, IMAGE_SIZE, antialias=True)
    return tf.cast(image, tf.float32), tf.cast(label, tf.int32)


def make_dataset(
    manifest: pd.DataFrame,
    *,
    batch_size: int,
    training: bool,
    seed: int,
) -> tf.data.Dataset:
    paths = manifest["path_resolved"].astype(str).to_numpy()
    labels = manifest["label_id"].astype("int32").to_numpy()
    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))

    if training:
        dataset = dataset.shuffle(
            buffer_size=min(len(manifest), 10_000),
            seed=seed,
            reshuffle_each_iteration=True,
        )

    dataset = dataset.map(decode_and_letterbox, num_parallel_calls=AUTOTUNE)
    dataset = dataset.batch(batch_size, drop_remainder=training)

    if training:
        dataset = dataset.map(
            lambda images, labels: (AUGMENTATION(images, training=True), labels),
            num_parallel_calls=AUTOTUNE,
        )

    return dataset.prefetch(AUTOTUNE)


def make_all_datasets(
    manifest_path: str | Path,
    *,
    batch_size: int,
    seed: int,
) -> tuple[tf.data.Dataset, tf.data.Dataset, tf.data.Dataset, pd.DataFrame]:
    manifest_path = Path(manifest_path)
    manifest = load_training_manifest(
        manifest_path,
        verify_files=True,
        verify_hashes=True,
        required_splits=REQUIRED_TRAINING_SPLITS,
    )
    prepared = attach_training_columns(manifest, manifest_dir=manifest_path.parent)

    train = split_manifest(prepared, "train")
    validation = split_manifest(prepared, "validation")
    test = split_manifest(prepared, "test")

    return (
        make_dataset(train, batch_size=batch_size, training=True, seed=seed),
        make_dataset(validation, batch_size=batch_size, training=False, seed=seed),
        make_dataset(test, batch_size=batch_size, training=False, seed=seed),
        prepared,
    )
