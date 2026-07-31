"""TFLite conversion, contract inspection, and Keras parity evaluation."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Mapping
from typing import Any

import numpy as np
import pandas as pd
import tensorflow as tf
from numpy.typing import NDArray
from tensorflow import keras

from bbcds_model.artifact_release import (
    ArtifactReleaseError,
    fixed_threshold_metrics,
    validate_probabilities,
)
from bbcds_model.constants import INPUT_SHAPE, LABELS
from bbcds_model.dataset import decode_and_letterbox, make_dataset
from bbcds_model.manifest import split_manifest
from bbcds_model.tensorflow_adapter import frozen_concrete_function


def select_representative_samples(
    manifest: pd.DataFrame,
    *,
    samples_per_label: int,
    seed: int,
) -> tuple[pd.DataFrame, str]:
    training = split_manifest(manifest, "train")
    selected: list[pd.DataFrame] = []
    for label in LABELS:
        candidates = training.loc[training["label"] == label].drop_duplicates(
            subset="source_id", keep="first"
        )
        if len(candidates) < samples_per_label:
            raise ArtifactReleaseError(
                "Training split has inadequate representative coverage"
            )
        order = candidates.apply(
            lambda row: hashlib.sha256(
                f"{seed}|{row['source_id']}|{row['sha256']}".encode()
            ).hexdigest(),
            axis=1,
        )
        selected.append(
            candidates.assign(_selection_order=order)
            .sort_values("_selection_order")
            .head(samples_per_label)
        )
    result = pd.concat(selected, ignore_index=True).drop(columns="_selection_order")
    if result["source_id"].nunique() != len(result):
        raise ArtifactReleaseError(
            "Representative samples must use unique source groups"
        )
    subset_digest = hashlib.sha256(
        "\n".join(sorted(result["sha256"].astype(str))).encode()
    ).hexdigest()
    return result, subset_digest


def _representative_dataset(
    samples: pd.DataFrame,
) -> Iterator[list[NDArray[np.float32]]]:
    for row in samples.itertuples(index=False):
        image, _ = decode_and_letterbox(
            tf.convert_to_tensor(str(row.path_resolved)),
            tf.convert_to_tensor(int(row.label_id)),
        )
        yield [np.expand_dims(np.asarray(image, dtype=np.float32), axis=0)]


def convert_model(model: keras.Model, samples: pd.DataFrame) -> bytes:
    try:
        frozen = frozen_concrete_function(model)
        converter = tf.lite.TFLiteConverter.from_concrete_functions([frozen])
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.representative_dataset = lambda: _representative_dataset(samples)
        converter.target_spec.supported_ops = [
            tf.lite.OpsSet.TFLITE_BUILTINS_INT8
        ]
        converter.inference_input_type = tf.float32
        converter.inference_output_type = tf.float32
        return bytes(converter.convert())
    except ArtifactReleaseError:
        raise
    except Exception as error:
        raise ArtifactReleaseError("TFLite conversion failed") from error


def inspect_tflite(
    model_content: bytes,
) -> tuple[tf.lite.Interpreter, dict[str, Any]]:
    try:
        interpreter = tf.lite.Interpreter(model_content=model_content)
        interpreter.allocate_tensors()
    except Exception as error:
        raise ArtifactReleaseError(
            "TFLite interpreter could not load the artifact"
        ) from error
    inputs = interpreter.get_input_details()
    outputs = interpreter.get_output_details()
    if len(inputs) != 1 or len(outputs) != 1:
        raise ArtifactReleaseError(
            "TFLite artifact must expose one input and one output"
        )
    input_detail, output_detail = inputs[0], outputs[0]
    if input_detail["dtype"] != np.float32 or list(input_detail["shape"]) != list(
        INPUT_SHAPE
    ):
        raise ArtifactReleaseError("TFLite input contract is invalid")
    if output_detail["dtype"] != np.float32 or list(output_detail["shape"]) != [
        1,
        len(LABELS),
    ]:
        raise ArtifactReleaseError("TFLite output contract is invalid")
    tensor_details = interpreter.get_tensor_details()
    integer_tensors = sum(
        detail["dtype"] in (np.int8, np.uint8)
        and detail["quantization_parameters"]["scales"].size > 0
        for detail in tensor_details
    )
    if integer_tensors == 0:
        raise ArtifactReleaseError("TFLite artifact has no quantized internal tensors")
    return interpreter, {
        "inputShape": list(INPUT_SHAPE),
        "inputDType": "float32",
        "outputShape": [1, len(LABELS)],
        "outputDType": "float32",
        "quantizedInternalTensorCount": integer_tensors,
        "tensorCount": len(tensor_details),
    }


def validate_keras_contract(model: keras.Model) -> None:
    if isinstance(model.input_shape, list) or isinstance(model.output_shape, list):
        raise ArtifactReleaseError(
            "Keras checkpoint must expose one input and one output"
        )
    if list(model.input_shape[1:]) != list(INPUT_SHAPE[1:]):
        raise ArtifactReleaseError("Keras checkpoint input shape is invalid")
    if list(model.output_shape[1:]) != [len(LABELS)]:
        raise ArtifactReleaseError("Keras checkpoint output shape is invalid")
    if model.inputs[0].dtype != "float32" or model.outputs[0].dtype != "float32":
        raise ArtifactReleaseError("Keras checkpoint boundaries must be float32")


def evaluate_parity(
    model: keras.Model,
    interpreter: tf.lite.Interpreter,
    validation: pd.DataFrame,
    *,
    batch_size: int,
    seed: int,
    threshold: float,
) -> dict[str, Any]:
    dataset = make_dataset(
        validation, batch_size=batch_size, training=False, seed=seed
    )
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]
    labels: list[NDArray[np.int32]] = []
    keras_outputs: list[NDArray[np.float32]] = []
    tflite_outputs: list[NDArray[np.float32]] = []
    for images, batch_labels in dataset:
        image_values = np.asarray(images, dtype=np.float32)
        labels.append(np.asarray(batch_labels, dtype=np.int32))
        keras_outputs.append(
            np.asarray(model(images, training=False), dtype=np.float32)
        )
        for image in image_values:
            interpreter.set_tensor(input_detail["index"], image[np.newaxis, ...])
            interpreter.invoke()
            tflite_outputs.append(
                np.asarray(
                    interpreter.get_tensor(output_detail["index"]), dtype=np.float32
                )
            )
    label_values = np.concatenate(labels)
    keras_values = validate_probabilities(
        np.concatenate(keras_outputs), description="Keras"
    )
    tflite_values = validate_probabilities(
        np.concatenate(tflite_outputs), description="TFLite"
    )
    keras_metrics = fixed_threshold_metrics(
        label_values, keras_values, threshold=threshold
    )
    tflite_metrics = fixed_threshold_metrics(
        label_values, tflite_values, threshold=threshold
    )
    absolute_error = np.abs(keras_values - tflite_values)
    return {
        "recordCount": len(label_values),
        "sourceGroupCount": int(validation["source_id"].nunique()),
        "threshold": threshold,
        "keras": keras_metrics,
        "tflite": tflite_metrics,
        "top1Agreement": float(
            np.mean(
                np.argmax(keras_values, axis=1)
                == np.argmax(tflite_values, axis=1)
            )
        ),
        "meanAbsoluteProbabilityError": float(np.mean(absolute_error)),
        "maximumAbsoluteProbabilityError": float(np.max(absolute_error)),
    }


def validate_parity_gates(
    parity: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, bool]:
    gates = policy["parity"]
    keras_metrics = parity["keras"]
    tflite_metrics = parity["tflite"]
    results = {
        "top1Agreement": parity["top1Agreement"]
        >= gates["minimumTop1Agreement"],
        "macroF1": keras_metrics["macroF1"] - tflite_metrics["macroF1"]
        <= gates["maximumMacroF1Drop"],
        "binaryPrecision": keras_metrics["binaryPrecision"]
        - tflite_metrics["binaryPrecision"]
        <= gates["maximumBinaryPrecisionDrop"],
        "binaryRecall": keras_metrics["binaryRecall"]
        - tflite_metrics["binaryRecall"]
        <= gates["maximumBinaryRecallDrop"],
    }
    if not all(results.values()):
        raise ArtifactReleaseError("TFLite artifact does not meet parity gates")
    return results
