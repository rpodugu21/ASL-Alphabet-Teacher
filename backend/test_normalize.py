"""Normalize and visualize a sample payload against letter ground truth.

Examples:
    python test_normalize.py --show
    python test_normalize.py --input sample_payload.json --letter B --save comparison.png
"""

from __future__ import annotations

import argparse
import json
import html
from pathlib import Path

from normalize import load_ground_truth, normalize_payload


CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
    (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
)


def _write_svg(
    sample: list[dict], normalized: list[dict], target: list[dict], path: str
) -> None:
    points = sample + normalized + target
    x_values = [point["x"] for point in points]
    y_values = [point["y"] for point in points]
    minimum_x, maximum_x = min(x_values), max(x_values)
    minimum_y, maximum_y = min(y_values), max(y_values)
    padding = 0.08
    x_span = max(maximum_x - minimum_x, 0.01)
    y_span = max(maximum_y - minimum_y, 0.01)
    minimum_x -= x_span * padding
    maximum_x += x_span * padding
    minimum_y -= y_span * padding
    maximum_y += y_span * padding
    width, height, panel_width = 1200, 430, 400

    def project(point: dict, panel: int) -> tuple[float, float]:
        x = panel * panel_width + (point["x"] - minimum_x) / (maximum_x - minimum_x) * 360 + 20
        y = 40 + (point["y"] - minimum_y) / (maximum_y - minimum_y) * 350
        return x, y

    groups = ((sample, "Input", "#777777"), (normalized, "Normalized", "#1769aa"), (target, "Ground truth", "#d97706"))
    elements = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="430" viewBox="0 0 1200 430">']
    elements.append('<rect width="100%" height="100%" fill="white"/>')
    for panel, (points_for_panel, title, color) in enumerate(groups):
        elements.append(f'<text x="{panel * panel_width + 20}" y="25" font-family="sans-serif" font-size="18">{html.escape(title)}</text>')
        for start, end in CONNECTIONS:
            x1, y1 = project(points_for_panel[start], panel)
            x2, y2 = project(points_for_panel[end], panel)
            elements.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="2"/>')
        for point in points_for_panel:
            x, y = project(point, panel)
            elements.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}"/>')
    elements.append("</svg>")
    Path(path).write_text("\n".join(elements), encoding="utf-8")


def _plot_comparison(sample: list[dict], normalized: list[dict], target: list[dict], save: str | None) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        if save:
            _write_svg(sample, normalized, target, save)
            print(f"Saved dependency-free SVG comparison to {save}")
            return
        raise SystemExit("Visualization requires matplotlib: python -m pip install matplotlib") from error

    figure, axes = plt.subplots(1, 3, figsize=(15, 5))
    for axis, points, title, color in zip(
        axes,
        (sample, normalized, target),
        ("Input", "Normalized", "Ground truth"),
        ("tab:gray", "tab:blue", "tab:orange"),
    ):
        axis.scatter([point["x"] for point in points], [-point["y"] for point in points], color=color)
        for start, end in CONNECTIONS:
            axis.plot(
                [points[start]["x"], points[end]["x"]],
                [-points[start]["y"], -points[end]["y"]],
                color=color,
                linewidth=1,
            )
        axis.set_title(title)
        axis.set_aspect("equal")
        axis.grid(True, alpha=0.25)
    figure.tight_layout()
    if save:
        figure.savefig(save, dpi=150)
        print(f"Saved comparison to {save}")
    else:
        plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("sample_payload.json"))
    parser.add_argument("--letter", default=None, help="Override the payload classification.")
    parser.add_argument("--ground-truth-root", type=Path, default=None)
    parser.add_argument("--save", help="Save the plot instead of opening a window.")
    parser.add_argument("--show", action="store_true", help="Open the comparison plot.")
    args = parser.parse_args()

    with args.input.open(encoding="utf-8") as file:
        payload = json.load(file)
    letter = args.letter or payload.get("classification") or payload.get("letter")
    if not letter:
        parser.error("--letter is required when the payload has no classification or letter.")

    kwargs = {}
    if args.ground_truth_root is not None:
        kwargs["ground_truth_root"] = args.ground_truth_root
    target_payload = load_ground_truth(letter, **kwargs)
    result = normalize_payload(payload, letter, **kwargs)
    target = target_payload["normalized_landmarks"]
    sample = payload["normalized_landmarks"]
    print(f"Normalized {len(result['normalized_landmarks'])} landmarks for letter {letter.upper()}.")
    if args.show or args.save:
        _plot_comparison(sample, result["normalized_landmarks"], target, args.save)


if __name__ == "__main__":
    main()
