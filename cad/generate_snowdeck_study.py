#!/usr/bin/env python3
"""Generate non-authoritative X1 SnowDeck v0.1 bench-study CAD references."""
from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq

try:
    from cad.fit_rig_geometry import DEFAULT as FIT_RIG
    from cad.generate_fit_rig import cant_wedge, export, footplate
    from cad.snowdeck_study_geometry import DEFAULT as STUDY
except ModuleNotFoundError:
    from fit_rig_geometry import DEFAULT as FIT_RIG
    from generate_fit_rig import cant_wedge, export, footplate
    from snowdeck_study_geometry import DEFAULT as STUDY


def compliance_insert_envelope():
    return (
        cq.Workplane("XY")
        .box(
            STUDY.insert_envelope_length_mm,
            STUDY.insert_envelope_width_mm,
            STUDY.insert_study_max_thickness_mm,
            centered=(True, True, False),
        )
        .edges("|Z")
        .fillet(6)
    )


def main() -> None:
    errors = STUDY.validate()
    if errors:
        raise SystemExit("Invalid SnowDeck study geometry: " + "; ".join(errors))

    out = Path(__file__).resolve().parent / "generated_snowdeck_study"
    out.mkdir(parents=True, exist_ok=True)

    export(out, "snowdeck_universal_plate_reference", footplate(FIT_RIG))
    export(out, "snowdeck_compliance_insert_envelope", compliance_insert_envelope())

    for angle in STUDY.cant_study_angles_deg:
        if angle <= 0:
            continue
        label = str(angle).replace(".", "p")
        export(out, f"snowdeck_cant_{label}deg_study", cant_wedge(FIT_RIG, angle))

    (out / "snowdeck_study_authority.json").write_text(
        json.dumps(STUDY.authority_report(), indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Generated SnowDeck bench-study references in {out} "
        "[NOT FABRICATION OR RIDE READY]"
    )


if __name__ == "__main__":
    main()
