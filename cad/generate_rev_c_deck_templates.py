#!/usr/bin/env python3
"""Generate full-scale Rev-C deck-envelope SVGs for rider stance experiments.

These are deliberately simple maximum envelopes, not exact deck outlines and
not structural CAD. Print/tile at 100% scale or transfer dimensions to
cardboard/foam board.
"""
from __future__ import annotations

import argparse
from pathlib import Path

CANDIDATES = {
    "comp95": {
        "length_mm": 950.0,
        "width_mm": 251.0,
        "label": "Comp 95 max deck envelope",
    },
    "pro_warren_iii": {
        "length_mm": 980.0,
        "width_mm": 244.0,
        "label": "Pro Warren III max deck envelope",
    },
    "agent": {
        "length_mm": 1020.0,
        "width_mm": 284.0,
        "label": "Agent max deck envelope",
    },
}


def svg_for(name: str, spec: dict) -> str:
    length = float(spec["length_mm"])
    width = float(spec["width_mm"])
    margin = 20.0
    canvas_w = length + 2 * margin
    canvas_h = width + 2 * margin
    center_x = margin + length / 2
    center_y = margin + width / 2

    grid_lines = []
    for x in range(0, int(length) + 1, 50):
        grid_lines.append(
            f'<line x1="{margin+x}" y1="{margin}" x2="{margin+x}" y2="{margin+width}" '
            'stroke="#aaa" stroke-width="0.4" stroke-dasharray="3,3"/>'
        )
    for y in range(0, int(width) + 1, 50):
        grid_lines.append(
            f'<line x1="{margin}" y1="{margin+y}" x2="{margin+length}" y2="{margin+y}" '
            'stroke="#aaa" stroke-width="0.4" stroke-dasharray="3,3"/>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}mm" height="{canvas_h}mm"
viewBox="0 0 {canvas_w} {canvas_h}">
  <rect x="{margin}" y="{margin}" width="{length}" height="{width}"
        fill="none" stroke="black" stroke-width="1"/>
  {''.join(grid_lines)}
  <line x1="{center_x}" y1="{margin}" x2="{center_x}" y2="{margin+width}"
        stroke="black" stroke-width="0.6" stroke-dasharray="8,4"/>
  <line x1="{margin}" y1="{center_y}" x2="{margin+length}" y2="{center_y}"
        stroke="black" stroke-width="0.6" stroke-dasharray="8,4"/>
  <text x="{margin+5}" y="{margin+12}" font-size="8">{spec['label']}</text>
  <text x="{margin+5}" y="{margin+24}" font-size="6">{length:.0f} x {width:.0f} mm maximum envelope</text>
  <text x="{margin+5}" y="{margin+36}" font-size="6">50 mm reference grid. NOT exact deck outline. NOT structural CAD.</text>
</svg>
"""


def generate(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, spec in CANDIDATES.items():
        path = out_dir / f"rev_c_{name}_deck_envelope.svg"
        path.write_text(svg_for(name, spec), encoding="utf-8")
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("cad/generated/rev_c_templates"))
    args = parser.parse_args()
    for path in generate(args.out_dir):
        print(path)


if __name__ == "__main__":
    main()
