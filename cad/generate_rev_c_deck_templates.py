#!/usr/bin/env python3
"""Generate full-scale Rev-C deck-envelope SVGs for rider stance experiments.

These are deliberately simple maximum envelopes, not exact deck outlines and
not structural CAD. Print/tile at 100% scale or transfer dimensions to
cardboard/foam board.
"""
from __future__ import annotations

import argparse
import json
import secrets
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


def blind_svg_for(label: str, spec: dict) -> str:
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
  <text x="{margin+5}" y="{margin+12}" font-size="9">Candidate {label}</text>
  <text x="{margin+5}" y="{margin+24}" font-size="6">50 mm reference grid. Maximum-envelope study only.</text>
  <text x="{margin+5}" y="{margin+36}" font-size="6">NOT exact deck outline. NOT structural CAD. Product identity intentionally hidden.</text>
</svg>
"""


def generate_blinded(
    out_dir: Path,
    key_path: Path,
    candidate_order: list[str] | None = None,
) -> tuple[list[Path], dict]:
    names = list(CANDIDATES)
    if candidate_order is None:
        candidate_order = secrets.SystemRandom().sample(names, k=len(names))
    if sorted(candidate_order) != sorted(names):
        raise ValueError("candidate_order must contain each Rev-C deck candidate exactly once")

    out_dir.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    labels = ("A", "B", "C")
    mapping = {}
    paths = []
    for label, name in zip(labels, candidate_order):
        spec = CANDIDATES[name]
        path = out_dir / f"rev_c_candidate_{label.lower()}_blind.svg"
        path.write_text(blind_svg_for(label, spec), encoding="utf-8")
        paths.append(path)
        mapping[label] = {
            "candidate_id": name,
            "length_mm": int(spec["length_mm"]),
            "width_mm": int(spec["width_mm"]),
        }

    key = {
        "schema_version": 1,
        "scope": "rev_c_deck_blind_key",
        "mapping": mapping,
        "physical_authority": False,
        "powered_operation_authorized": False,
    }
    key_path.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    return paths, key


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
    parser.add_argument("--blind-out-dir", type=Path)
    parser.add_argument("--blind-key", type=Path)
    args = parser.parse_args()
    for path in generate(args.out_dir):
        print(path)
    if args.blind_out_dir or args.blind_key:
        if args.blind_out_dir is None or args.blind_key is None:
            raise SystemExit("--blind-out-dir and --blind-key must be supplied together")
        paths, _ = generate_blinded(args.blind_out_dir, args.blind_key)
        for path in paths:
            print(path)
        print(args.blind_key)


if __name__ == "__main__":
    main()
