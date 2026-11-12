"""Create near-ground-truth samples for normalization edge cases."""

from __future__ import annotations

import json
import math
from pathlib import Path


BACKEND = Path(__file__).resolve().parent
GROUND_TRUTH = BACKEND / "ground_truth_letters"
OUTPUT = BACKEND / "edge_samples"
SEVERE_OUTPUT = BACKEND / "severe_samples"
PALM_IDS = (0, 5, 9, 13, 17)


def palm_center(points: list[dict]) -> tuple[float, float, float]:
    return tuple(
        sum(float(points[index][axis]) for index in PALM_IDS) / len(PALM_IDS)
        for axis in ("x", "y", "z")
    )


FINGER_GROUPS = {
    "thumb": (1, 2, 3, 4),
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}


def make_sample(
    payload: dict,
    letter: str,
    *,
    scale: float = 1.0,
    left: bool = False,
    bent_finger: str | None = None,
) -> dict:
    edge_case = []
    if scale != 1.0:
        edge_case.append("large_hand" if scale > 1 else "small_hand")
    if left:
        edge_case.append("left_hand")
    if bent_finger:
        edge_case.append(f"{bent_finger}_slightly_bent")
    result = {
        "image": f"edge_{letter}.jpg",
        "classification": letter,
        "edge_case": "_".join(edge_case) or "natural_pose_variation",
        "handedness": {
            "category": "Left" if left else "Right",
            "confidence": 1.0,
            "index": 0 if left else 1,
        },
    }
    source = [dict(point) for point in payload["normalized_landmarks"]]
    center = palm_center(source)
    points = []
    for index, point in enumerate(source):
        phase = index * 0.73 + ord(letter) * 0.11
        deviation = (
            0.0040 * math.sin(phase),
            0.0040 * math.cos(phase),
            0.0015 * math.sin(phase * 0.8),
        )
        x0 = center[0] + (float(point["x"]) - center[0]) * scale + deviation[0]
        y0 = center[1] + (float(point["y"]) - center[1]) * scale + deviation[1]
        z = center[2] + (float(point["z"]) - center[2]) * scale + deviation[2]
        # A small pose tilt models a hand that is not held perfectly level.
        angle = 0.045
        x = center[0] + (x0 - center[0]) * math.cos(angle) - (y0 - center[1]) * math.sin(angle)
        y = center[1] + (x0 - center[0]) * math.sin(angle) + (y0 - center[1]) * math.cos(angle)
        if bent_finger:
            finger_ids = FINGER_GROUPS[bent_finger]
            if index in finger_ids:
                bend = (finger_ids.index(index) + 1) / len(finger_ids)
                # Pull the distal joints toward the palm and slightly sideways.
                x += (center[0] - x) * 0.18 * bend
                y += (center[1] - y) * 0.10 * bend
                x += 0.012 * bend
        if left:
            x = 2 * center[0] - x
        points.append({**point, "x": x, "y": y, "z": z})
    result["normalized_landmarks"] = points
    result["source_ground_truth"] = f"backend/ground_truth_letters/ground_truth_{letter}.json"
    return result


def make_severe_sample(payload: dict, letter: str, *, left: bool, bent_finger: str) -> dict:
    """Create a substantially displaced but still recognizable hand pose."""
    result = make_sample(
        payload,
        letter,
        scale=1.38,
        left=left,
        bent_finger=bent_finger,
    )
    points = result["normalized_landmarks"]
    center = palm_center(points)
    angle = math.radians(11)
    for index, point in enumerate(points):
        x0 = float(point["x"]) - center[0]
        y0 = float(point["y"]) - center[1]
        point["x"] = center[0] + x0 * math.cos(angle) - y0 * math.sin(angle) + 0.018
        point["y"] = center[1] + x0 * math.sin(angle) + y0 * math.cos(angle) - 0.014
        point["z"] = float(point["z"]) + 0.004 * math.sin(index * 0.6)
        if index in FINGER_GROUPS[bent_finger]:
            bend = (FINGER_GROUPS[bent_finger].index(index) + 1) / 4
            point["x"] += (center[0] - point["x"]) * 0.34 * bend
            point["y"] += (center[1] - point["y"]) * 0.24 * bend
            point["x"] += 0.028 * bend
    result["edge_case"] = (
        f"severe_{'left_' if left else ''}large_{bent_finger}_deviation"
    )
    return result


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    SEVERE_OUTPUT.mkdir(exist_ok=True)
    for existing in OUTPUT.glob("*.json"):
        existing.unlink()
    for existing in SEVERE_OUTPUT.glob("*.json"):
        existing.unlink()
    for code in range(ord("A"), ord("Z") + 1):
        letter = chr(code)
        path = GROUND_TRUTH / f"ground_truth_{letter}.json"
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
        cases = {
            "pose": make_sample(payload, letter),
            "large": make_sample(payload, letter, scale=1.28),
            "left": make_sample(payload, letter, left=True),
            "large_left_bent_index": make_sample(
                payload, letter, scale=1.28, left=True, bent_finger="index"
            ),
            "bent_ring": make_sample(payload, letter, bent_finger="ring"),
        }
        for name, sample in cases.items():
            destination = OUTPUT / f"{letter}_{name}.json"
            destination.write_text(
                json.dumps(sample, indent=2) + "\n", encoding="utf-8"
            )
        severe_cases = {
            "severe_right_bent_index": make_severe_sample(
                payload, letter, left=False, bent_finger="index"
            ),
            "severe_left_bent_ring": make_severe_sample(
                payload, letter, left=True, bent_finger="ring"
            ),
        }
        for name, sample in severe_cases.items():
            destination = SEVERE_OUTPUT / f"{letter}_{name}.json"
            destination.write_text(
                json.dumps(sample, indent=2) + "\n", encoding="utf-8"
            )
    print(f"Generated {26 * 5} edge-case samples in {OUTPUT}")
    print(f"Generated {26 * 2} severe samples in {SEVERE_OUTPUT}")


if __name__ == "__main__":
    main()
