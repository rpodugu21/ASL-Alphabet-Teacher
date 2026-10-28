"""Local server for the ASL Alphabet Teacher.

Serves the frontend, runs MediaPipe Hand Landmarker on captured photos, and
stores each photo with its landmarks in data/raw/ as <name>.png + <name>.json.

Run:  python backend/server.py   then open http://localhost:5000
"""

import json
import re
import threading
from datetime import datetime
from pathlib import Path

import mediapipe as mp
from flask import Flask, abort, jsonify, request, send_from_directory
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
FRONTEND_DIR = ROOT / "frontend"
RAW_DIR = ROOT / "data" / "raw"
MODEL_PATH = BACKEND_DIR / "models" / "hand_landmarker.task"

# Capture names look like 2026-10-28_14-03-22-512
NAME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-\d{3}")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

landmarker = HandLandmarker.create_from_options(
    HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=RunningMode.IMAGE,
        num_hands=2,
    )
)
# Requests run on separate threads; only one may use the landmarker at a time
landmarker_lock = threading.Lock()
name_lock = threading.Lock()


def annotate(image_path):
    """Run Hand Landmarker on an image file and return the result as plain data."""
    image = mp.Image.create_from_file(str(image_path))
    with landmarker_lock:
        result = landmarker.detect(image)

    hands = []
    for landmarks, world_landmarks, handedness in zip(
        result.hand_landmarks, result.hand_world_landmarks, result.handedness
    ):
        hands.append({
            # MediaPipe assumes a mirrored (selfie) image. Our photos are not
            # mirrored, so this label is the opposite of the signer's actual hand.
            "handedness": handedness[0].category_name,
            "score": handedness[0].score,
            # x, y: 0–1 relative to image width/height; z: depth relative to the wrist
            "landmarks": [{"x": p.x, "y": p.y, "z": p.z} for p in landmarks],
            # Meters, origin at the hand's center
            "world_landmarks": [{"x": p.x, "y": p.y, "z": p.z} for p in world_landmarks],
        })

    return {
        "width": image.width,
        "height": image.height,
        "model": MODEL_PATH.name,
        "hands": hands,
    }


def new_name():
    with name_lock:
        while True:
            now = datetime.now()
            name = now.strftime("%Y-%m-%d_%H-%M-%S-") + f"{now.microsecond // 1000:03d}"
            if not (RAW_DIR / f"{name}.png").exists():
                return name


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.post("/api/capture")
def capture():
    """Save a PNG photo to data/raw/, annotate it, and return the annotation."""
    data = request.get_data()
    if not data.startswith(PNG_SIGNATURE):
        abort(400, "Expected a PNG image")

    name = new_name()
    image_path = RAW_DIR / f"{name}.png"
    image_path.write_bytes(data)

    annotation = {"image": image_path.name, **annotate(image_path)}
    (RAW_DIR / f"{name}.json").write_text(json.dumps(annotation, indent=2))
    return jsonify(name=name, annotation=annotation)


@app.get("/api/captures")
def list_captures():
    """Names of saved photos, oldest first."""
    names = sorted(p.stem for p in RAW_DIR.glob("*.png") if NAME_PATTERN.fullmatch(p.stem))
    return jsonify(names)


@app.get("/api/captures/<filename>")
def get_capture(filename):
    """A saved photo (<name>.png) or its annotation (<name>.json)."""
    name, _, ext = filename.rpartition(".")
    if not NAME_PATTERN.fullmatch(name) or ext not in ("png", "json"):
        abort(404)
    return send_from_directory(RAW_DIR, filename, max_age=0)


if __name__ == "__main__":
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host="127.0.0.1", port=5000)
