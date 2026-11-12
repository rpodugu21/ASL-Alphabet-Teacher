"""Normalize every JSON sample in a directory and save SVG comparisons."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from normalize import load_ground_truth, normalize_payload
from test_normalize import _write_svg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path(__file__).with_name("sample_sets"))
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("output"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(args.input_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"No JSON samples found in {args.input_dir}")

    for source in files:
        with source.open(encoding="utf-8") as file:
            payload = json.load(file)
        letter = payload.get("classification") or payload.get("letter")
        if not isinstance(letter, str):
            raise SystemExit(f"Missing classification in {source}")
        target = load_ground_truth(letter)
        normalized = normalize_payload(payload, letter)
        destination = args.output_dir / f"{source.stem}.svg"
        _write_svg(
            payload["normalized_landmarks"],
            normalized["normalized_landmarks"],
            target["normalized_landmarks"],
            str(destination),
        )
        print(f"{source.name} -> {destination.name}")


if __name__ == "__main__":
    main()
