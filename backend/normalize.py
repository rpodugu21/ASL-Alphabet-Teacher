"""Align hand landmarks to a reference using handedness and uniform scale.

Preserves finger angles, relative proportions, and hand orientation. It mirrors
left/right samples horizontally when the sample and reference handedness differ,
then translates and uniformly scales the hand.

For MediaPipe image landmarks, provide sample_image_size and
reference_image_size as (width, height) of the images/crops passed to MediaPipe.
This corrects the unequal x/y units before computing distances. If omitted,
coordinates are assumed to already have equal axis units (e.g. square-image
MediaPipe landmarks, or world landmarks). Never mix image and world landmarks.
Handedness is read from a payload's ``handedness.category`` field. Raw landmark
lists can pass ``sample_handedness`` explicitly.

The original four positional arguments remain supported. Returned coordinates
are in the reference's coordinate system and can lie outside [0, 1].
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


LANDMARK_COUNT = 21
PALM_LANDMARK_IDS = (0, 5, 9, 13, 17)
AXES = ("x", "y", "z")
DEFAULT_GROUND_TRUTH_ROOT = (
    Path(__file__).resolve().parent / "ground_truth_letters"
)


class NormalizationError(ValueError):
    """Raised when a hand payload cannot be normalized."""


def _validated_letter(letter: str) -> str:
    if not isinstance(letter, str):
        raise NormalizationError("letter must be a single ASCII letter A-Z.")
    letter = letter.strip().upper()
    if len(letter) != 1 or letter not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        raise NormalizationError("letter must be a single ASCII letter A-Z.")
    return letter


def _landmark_sequence(payload) -> list[dict[str, Any]]:
    if isinstance(payload, Mapping):
        landmarks = payload.get("normalized_landmarks")
        if landmarks is None:
            landmarks = payload.get("landmarks")
    else:
        landmarks = payload
    if (
        not isinstance(landmarks, Sequence)
        or isinstance(landmarks, (str, bytes))
        or len(landmarks) != LANDMARK_COUNT
    ):
        raise NormalizationError("Expected exactly 21 landmark objects.")
    if not all(isinstance(point, Mapping) for point in landmarks):
        raise NormalizationError("Each landmark must be an object with x, y, z.")

    points = [dict(point) for point in landmarks]
    # If IDs exist, use them to establish correspondence. Otherwise require
    # the usual MediaPipe order: index 0 = wrist, indices 1-20 = finger joints.
    if any("id" in point for point in points):
        ids = [point.get("id") for point in points]
        if (
            not all(isinstance(i, int) and not isinstance(i, bool) for i in ids)
            or set(ids) != set(range(LANDMARK_COUNT))
        ):
            raise NormalizationError("IDs must be unique integers 0 through 20.")
        points.sort(key=lambda point: point["id"])

    for index, point in enumerate(points):
        for axis in AXES:
            try:
                if isinstance(point[axis], bool):
                    raise ValueError
                value = float(point[axis])
                if not math.isfinite(value):
                    raise ValueError
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                raise NormalizationError(
                    f"Landmark {index} must have finite numeric {axis}."
                ) from error
            point[axis] = value
    return points


def _axis_factors(image_size) -> tuple[float, float, float]:
    if image_size is None:
        return (1.0, 1.0, 1.0)
    try:
        width, height = map(float, image_size)
        if not all(math.isfinite(v) and v > 0 for v in (width, height)):
            raise ValueError
    except (TypeError, ValueError, OverflowError) as error:
        raise NormalizationError("image_size must be positive (width, height).") from error
    # MediaPipe x and z use width-relative units; y uses height-relative units.
    return (1.0, height / width, 1.0)


def _geometry(points, factors):
    return [
        tuple(point[axis] * factor for axis, factor in zip(AXES, factors))
        for point in points
    ]


def _palm_center(points):
    return tuple(
        sum(points[i][axis] for i in PALM_LANDMARK_IDS) / len(PALM_LANDMARK_IDS)
        for axis in range(3)
    )


def _palm_size(points) -> float:
    # Wrist -> middle-finger MCP (base), not fingertip: bending fingers should
    # not determine the scale. 3D distance avoids 2D foreshortening alone.
    size = math.dist(points[0], points[9])
    if not math.isfinite(size) or size <= 1e-8:
        raise NormalizationError("Palm size is zero or too small to normalize.")
    return size


def _handedness(payload) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    value = payload.get("handedness")
    if isinstance(value, Mapping):
        value = value.get("category")
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    if value in {"left", "right"}:
        return value
    return None


def load_ground_truth(
    letter: str,
    ground_truth_root: str | Path = DEFAULT_GROUND_TRUTH_ROOT,
) -> dict[str, Any]:
    letter = _validated_letter(letter)
    path = Path(ground_truth_root) / f"ground_truth_{letter}.json"
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, ValueError) as error:
        raise NormalizationError(f"Cannot load ground truth: {path}") from error
    if not isinstance(payload, Mapping):
        raise NormalizationError("Ground-truth file must contain a payload object.")
    _landmark_sequence(payload)
    return payload


def _align(landmarks, letter, ground_truth, ground_truth_root,
           sample_image_size, reference_image_size,
           sample_handedness=None, reference_handedness=None):
    letter = _validated_letter(letter)
    if (sample_image_size is None) != (reference_image_size is None):
        raise NormalizationError("Supply both image sizes, or neither.")
    sample = _landmark_sequence(landmarks)
    target = _landmark_sequence(
        load_ground_truth(letter, ground_truth_root)
        if ground_truth is None else ground_truth
    )
    sample_factors = _axis_factors(sample_image_size)
    target_factors = _axis_factors(reference_image_size)
    sample_xyz = _geometry(sample, sample_factors)
    target_xyz = _geometry(target, target_factors)
    sample_center = _palm_center(sample_xyz)
    target_center = _palm_center(target_xyz)
    sample_hand = (
        sample_handedness.strip().lower()
        if isinstance(sample_handedness, str) else _handedness(landmarks)
    )
    target_hand = (
        reference_handedness.strip().lower()
        if isinstance(reference_handedness, str)
        else _handedness(
            load_ground_truth(letter, ground_truth_root)
            if ground_truth is None else ground_truth
        )
    )
    if sample_hand not in {None, "left", "right"}:
        raise NormalizationError("sample_handedness must be 'Left' or 'Right'.")
    if target_hand not in {None, "left", "right"}:
        raise NormalizationError("reference_handedness must be 'Left' or 'Right'.")
    mirrored = sample_hand is not None and target_hand is not None and sample_hand != target_hand
    if mirrored:
        sample_xyz = [
            (2 * sample_center[0] - point[0], point[1], point[2])
            for point in sample_xyz
        ]
        sample_center = _palm_center(sample_xyz)
    sample_size = _palm_size(sample_xyz)
    target_size = _palm_size(target_xyz)
    scale = target_size / sample_size

    aligned = []
    errors = []
    for i, point in enumerate(sample):
        xyz = tuple(
            (sample_xyz[i][j] - sample_center[j]) * scale + target_center[j]
            for j in range(3)
        )
        result = dict(point)
        result.update({axis: xyz[j] / target_factors[j]
                       for j, axis in enumerate(AXES)})
        aligned.append(result)
        # Dimensionless residual: 0.1 means 10% of the reference palm length.
        errors.append(math.dist(xyz, target_xyz[i]) / target_size)

    metadata = {
        "letter": letter,
        "reference_landmarks": list(PALM_LANDMARK_IDS),
        "operation": "palm_translation_and_uniform_scale",
        "handedness": {
            "sample": sample_hand,
            "reference": target_hand,
            "mirrored": mirrored,
        },
        "scale_landmarks": [0, 9],
        "scale_factor": scale,
        "sample_palm_size": sample_size,
        "reference_palm_size": target_size,
        "sample_axis_factors": list(sample_factors),
        "reference_axis_factors": list(target_factors),
        "coordinate_assumption": (
            "mediapipe_image_landmarks_aspect_corrected"
            if sample_image_size is not None else "equal_axis_units"
        ),
        "output_coordinate_frame": "reference",
    }
    return aligned, metadata, errors


def normalize_landmarks(
    landmarks,
    letter: str,
    ground_truth=None,
    ground_truth_root: str | Path = DEFAULT_GROUND_TRUTH_ROOT,
    *,
    sample_image_size=None,
    reference_image_size=None,
    sample_handedness=None,
    reference_handedness=None,
) -> list[dict[str, Any]]:
    """Return aligned landmarks in MediaPipe order, retaining extra fields.

    Uses p' = (p - sample_center) * (target_size/sample_size) + target_center.
    Optional image sizes are (width, height) for normalized IMAGE coordinates.
    Omit sizes for WORLD coordinates. If handedness differs, x is reflected
    around the sample palm center before scaling.
    """
    return _align(
        landmarks, letter, ground_truth, ground_truth_root,
        sample_image_size, reference_image_size,
        sample_handedness, reference_handedness,
    )[0]


def normalize_payload(
    payload: Mapping[str, Any],
    letter: str,
    ground_truth=None,
    ground_truth_root: str | Path = DEFAULT_GROUND_TRUTH_ROOT,
    *,
    sample_image_size=None,
    reference_image_size=None,
    sample_handedness=None,
    reference_handedness=None,
) -> dict[str, Any]:
    """Copy a payload, adding aligned landmarks and transform metadata.

    Other payload fields are unchanged; original image/crop metadata therefore
    still describes the input, NOT the aligned output's reference frame.
    """
    if not isinstance(payload, Mapping):
        raise NormalizationError("The payload must be a JSON object.")
    aligned, metadata, _ = _align(
        payload, letter, ground_truth, ground_truth_root,
        sample_image_size, reference_image_size,
        sample_handedness, reference_handedness,
    )
    return {**payload, "normalized_landmarks": aligned, "normalization": metadata}


def compare_landmarks(
    landmarks,
    letter: str,
    ground_truth=None,
    ground_truth_root: str | Path = DEFAULT_GROUND_TRUTH_ROOT,
    *,
    sample_image_size=None,
    reference_image_size=None,
    sample_handedness=None,
    reference_handedness=None,
) -> dict[str, Any]:
    """Align then report positional deviations in palm-length units.

    Pass ORIGINAL sample landmarks, not already aligned output. These are
    reference deviations, not probabilities or diagnoses: rotation, anatomy,
    and landmark noise can also cause a nonzero error. No pass/fail threshold
    is chosen; calibrate thresholds on labeled correct/incorrect examples.
    """
    _, metadata, errors = _align(
        landmarks, letter, ground_truth, ground_truth_root,
        sample_image_size, reference_image_size,
        sample_handedness, reference_handedness,
    )
    fingers = {"thumb": range(1, 5), "index": range(5, 9),
               "middle": range(9, 13), "ring": range(13, 17),
               "pinky": range(17, 21)}
    return {
        "units": "reference_palm_lengths",
        "mean_error": sum(errors) / LANDMARK_COUNT,
        "per_landmark_error": errors,
        "per_finger_mean_error": {
            name: sum(errors[i] for i in ids) / len(ids)
            for name, ids in fingers.items()
        },
        "normalization": metadata,
    }
