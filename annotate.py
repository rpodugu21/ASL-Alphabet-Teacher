import cv2
import mediapipe as mp
import os
import json

# =========================
# SETTINGS
# =========================

LETTERS = ["F", "G", "H", "I", "J", "K", "L", "M", "N", "O",
           "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
IMAGE_ROOT = "dataset/asl_alphabet_train/asl_alphabet_train"
OUTPUT_ROOT = "output"

MODEL_PATH = "hand_landmarker.task"

# =========================


BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode


options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=RunningMode.IMAGE,
    num_hands=1,
    min_hand_detection_confidence=0.3,
    min_hand_presence_confidence=0.3
)


def process_image(image_path, landmarker):

    img = cv2.imread(image_path)

    if img is None:
        print("Could not load:", image_path)
        return None

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=img_rgb
    )

    result = landmarker.detect(mp_image)

    if len(result.hand_landmarks) == 0:
        print("No hand detected:", image_path)
        return None

    handedness = result.handedness[0][0]

    normalized_landmarks = []

    for i, lm in enumerate(result.hand_landmarks[0]):
        normalized_landmarks.append({
            "id": i,
            "x": lm.x,
            "y": lm.y,
            "z": lm.z
        })

    world_landmarks = []

    for i, lm in enumerate(result.hand_world_landmarks[0]):
        world_landmarks.append({
            "id": i,
            "x": lm.x,
            "y": lm.y,
            "z": lm.z
        })

    data = {
        "image": os.path.basename(image_path),

        "handedness": {
            "category": handedness.category_name,
            "confidence": handedness.score,
            "index": handedness.index
        },

        "normalized_landmarks": normalized_landmarks,

        "world_landmarks": world_landmarks
    }

    return data


def main():

    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    with HandLandmarker.create_from_options(options) as landmarker:

        for letter in LETTERS:

            input_folder = os.path.join(IMAGE_ROOT, letter)
            output_folder = os.path.join(OUTPUT_ROOT, letter)

            os.makedirs(output_folder, exist_ok=True)

            if not os.path.exists(input_folder):
                print("Folder does not exist:", input_folder)
                continue

            print("\nProcessing:", letter)

            for filename in os.listdir(input_folder):

                if not filename.lower().endswith(
                    (".jpg", ".jpeg", ".png")
                ):
                    continue

                image_path = os.path.join(input_folder, filename)

                data = process_image(image_path, landmarker)

                if data is None:
                    continue

                base_name = os.path.splitext(filename)[0]

                output_path = os.path.join(
                    output_folder,
                    base_name + ".json"
                )

                with open(output_path, "w") as f:
                    json.dump(data, f, indent=2)

                print(filename, "->", output_path)


if __name__ == "__main__":
    main()