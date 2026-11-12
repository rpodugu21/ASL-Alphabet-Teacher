# Backend

## Requirements

The backend is a small Python-only normalization and visualization workflow.

Required:

- Python 3.10 or newer
- GNU Make
- The committed `ground_truth_letters/` directory with the canonical files:
  `ground_truth_letters/ground_truth_<LETTER>.json`
- WSL is recommended when running on Windows because the Makefile uses
  Unix-style commands such as `rm`.

No third-party Python packages are required for the default workflow. SVG
comparisons are generated directly by Python.

Optional:

- `matplotlib` for interactive plots with `--show`

Install the optional dependency in the active Python environment:

```bash
python3 -m pip install matplotlib
```

## What the normalizer does

For a classified hand sample, the normalizer:

1. Validates the 21 MediaPipe landmarks.
2. Uses landmarks `0, 5, 9, 13, 17` to calculate the palm center.
3. Corrects image-landmark aspect ratio when image dimensions are supplied.
4. Mirrors the sample horizontally when its handedness differs from the
   ground-truth handedness.
5. Uniformly scales using the wrist-to-middle-MCP distance.
6. Translates the result into the selected letter's ground-truth coordinate
   frame.

The original landmark deviations are preserved. The normalizer does not rotate
or force individual joints onto the ground truth.

## Run the complete workflow

From WSL:

```bash
cd /home/david/computer-vision/project/backend
make all
```

This will:

- Generate 130 realistic edge-case samples in `edge_samples/`
- Generate 52 more severe samples in `severe_samples/`
- Normalize the regular generated samples
- Normalize all realistic edge-case samples
- Normalize all severe samples
- Write SVG comparisons to:
  - `output/`
  - `output/edge/`
  - `output/severe/`

Generated samples and outputs are intentionally ignored by Git and can be
recreated at any time.

## Make targets

```bash
make samples          # Generate sample_sets/, edge_samples/, severe_samples/
make normalize        # Process sample_sets/
make normalize-edge   # Process edge_samples/
make normalize-severe # Process severe_samples/
make all              # Run every generation and normalization step
make clean-output     # Remove generated samples and visualizations
```

`make samples` regenerates all generated sample directories from the canonical
ground-truth files.

## Run one sample

The test script accepts a JSON payload containing `normalized_landmarks` and a
classification:

```bash
python3 test_normalize.py \
  --input sample_payload.json \
  --letter B \
  --save comparison.svg
```

If the payload contains `"classification"` or `"letter"`, `--letter` can be
omitted:

```bash
python3 test_normalize.py \
  --input edge_samples/B_bent_ring.json \
  --save B_bent_ring.svg
```

The saved SVG contains input, normalized, and ground-truth hand diagrams.

For an interactive Matplotlib window:

```bash
python3 test_normalize.py \
  --input sample_payload.json \
  --letter B \
  --show
```

## Input payload format

The payload should contain exactly 21 landmarks. Each landmark must have
numeric `x`, `y`, and `z` values and may include an `id` from `0` through `20`.

Example:

```json
{
  "classification": "B",
  "handedness": {
    "category": "Right"
  },
  "normalized_landmarks": [
    {"id": 0, "x": 0.54, "y": 0.91, "z": 0.00}
  ]
}
```

The example is abbreviated; a real payload must include all 21 landmarks.

## Image landmark dimensions

For MediaPipe normalized image landmarks, pass both image sizes when calling
the Python API:

```python
from normalize import normalize_payload

result = normalize_payload(
    payload,
    "B",
    sample_image_size=(1280, 720),
    reference_image_size=(640, 480),
)
```

Do not mix image landmarks and world landmarks. Omit image sizes for world
landmarks or coordinates that already use equal axis units.

## Repository data policy

Only the canonical single-letter ground-truth files are intended to be saved:

```text
backend/ground_truth_letters/ground_truth_A.json
...
backend/ground_truth_letters/ground_truth_Z.json
```

The model, training data, ground-truth source files, generated sample sets,
and visualization outputs are ignored by `.gitignore`.

Run the complete workflow from WSL:

```bash
make all
```

This creates near-ground-truth edge-case samples with realistic pose variation,
larger hands, opposite handedness, and individual-finger deviations, then writes SVG comparisons to `output/` and
`output/edge/`.

The full workflow also creates a separate `severe_samples/` set with
substantially larger scale, tilt, translation, depth noise, and finger
deviations. Its comparisons are written to `output/severe/`.

Individual targets:

```bash
make samples         # Generate edge_samples/
make normalize       # Process sample_sets/
make normalize-edge  # Process edge_samples/
make normalize-severe # Process severe_samples/
make clean-output    # Remove generated samples and visualizations
```

Normalization translates to the target palm, uniformly scales using wrist to
middle-MCP distance, and horizontally mirrors samples when their handedness
differs from the ground truth.
