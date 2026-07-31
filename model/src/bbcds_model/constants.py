"""Canonical model contract constants."""

from __future__ import annotations

IMAGE_SIZE = 224
INPUT_SHAPE = (1, IMAGE_SIZE, IMAGE_SIZE, 3)
MODEL_ARCHITECTURE = "MobileNetV3-Small"
TAXONOMY_VERSION = "1"

LABELS = ("Safe", "Suggestive", "Explicit", "Explicit Illustration")
CLASS_TO_ID = {label: index for index, label in enumerate(LABELS)}
ID_TO_CLASS = {index: label for label, index in CLASS_TO_ID.items()}

SPLITS = ("train", "validation", "test", "holdout")
REQUIRED_TRAINING_SPLITS = ("train", "validation", "test")
MEDIA_TYPES = ("image", "video_frame")
INAPPROPRIATE_LABELS = ("Explicit", "Explicit Illustration")
SUGGESTIVE_RISK_WEIGHT = 0.35
