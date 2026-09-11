#!/usr/bin/env python3
"""Generate the unpowered Worcester X1 one-zone pilot fixture.

This package reuses the qualified Fit Rig v0.3 sensor geometry but adds a
pilot-only pod mounting pattern and rigid carrier plate. It is for bench
calibration up to the software-enforced pilot load ceiling, never for riding.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cadquery as cq

from cad.fit_rig_geometry import DEFAULT, FitRigGeometry
from cad.generate_fit_rig import (
    alignment_jig,
    export,
    load_cell_pod,
    load_cell_reference,
    zone_pad,
)


@dataclass(frozen=True)
class PilotCarrierGeometry:
    carrier_length_mm: float = 130.0
    carrier_width_mm: float = 70.0
    carrier_thickness_mm: float = 8.0
    pod_mount_x_mm: float = 36.0
    pod_mount_y_mm: float = 12.0
    pod_mount_clearance_diameter_mm: float = 4.5
    bench_mount_x_mm: float = 55.0
    bench_mount_y_mm: float = 25.0
    bench_mount_clearance_diameter_mm: float = 6.5

    def validate(self, rig: FitRigGeometry = DEFAULT) -> list[str]:
        errors: list[str] = []
        if self.carrier_length_mm < rig.load_cell_pod_length_mm + 20:
            errors.append("carrier lacks longitudinal margin around the pod")
        if self.carrier_width_mm < rig.load_cell_pod_width_mm + 20:
            errors.append("carrier lacks lateral margin around the pod")
        if self.pod_mount_x_mm >= rig.load_cell_pod_length_mm / 2 - 4:
            errors.append("pilot pod mount holes are too close to the pod end")
        if self.pod_mount_y_mm >= rig.load_cell_pod_width_mm / 2 - 4:
            errors.append("pilot pod mount holes are too close to the pod side")
        # Keep the auxiliary holes outside the sensor body envelope and away from
        # the overload towers. These are reference-clearance rules, not a strength
        # certification.
        if self.pod_mount_y_mm <= rig.load_cell.width_mm / 2 + 3:
            errors.append("pilot pod mount holes lack clearance from sensor body")
        tower_dx = abs(self.pod_mount_x_mm - rig.load_cell.loaded_hole_xy_mm[0])
        tower_min = rig.overload_stop_diameter_mm / 2 + self.pod_mount_clearance_diameter_mm / 2 + 2
        if tower_dx <= tower_min:
            errors.append("loaded-end pilot mount holes are too close to overload towers")
        return errors


PILOT = PilotCarrierGeometry()


def _cut_xy_holes(shape, centers, diameter: float, depth: float):
    for x, y in centers:
        shape = shape.cut(
            cq.Workplane("XY").center(x, y).circle(diameter / 2).extrude(depth)
        )
    return shape


def pilot_pod(rig: FitRigGeometry = DEFAULT, pilot: PilotCarrierGeometry = PILOT):
    """Fit-rig pod plus four auxiliary M4-class carrier mounting holes."""
    pod = load_cell_pod(rig)
    centers = [
        (sx * pilot.pod_mount_x_mm, sy * pilot.pod_mount_y_mm)
        for sx in (-1, 1) for sy in (-1, 1)
    ]
    return _cut_xy_holes(
        pod,
        centers,
        pilot.pod_mount_clearance_diameter_mm,
        rig.load_cell_pod_thickness_mm + 2,
    )


def carrier_plate(pilot: PilotCarrierGeometry = PILOT):
    plate = (
        cq.Workplane("XY")
        .box(
            pilot.carrier_length_mm,
            pilot.carrier_width_mm,
            pilot.carrier_thickness_mm,
            centered=(True, True, False),
        )
        .edges("|Z").fillet(4)
    )
    pod_centers = [
        (sx * pilot.pod_mount_x_mm, sy * pilot.pod_mount_y_mm)
        for sx in (-1, 1) for sy in (-1, 1)
    ]
    plate = _cut_xy_holes(
        plate,
        pod_centers,
        pilot.pod_mount_clearance_diameter_mm,
        pilot.carrier_thickness_mm + 2,
    )
    bench_centers = [
        (sx * pilot.bench_mount_x_mm, sy * pilot.bench_mount_y_mm)
        for sx in (-1, 1) for sy in (-1, 1)
    ]
    return _cut_xy_holes(
        plate,
        bench_centers,
        pilot.bench_mount_clearance_diameter_mm,
        pilot.carrier_thickness_mm + 2,
    )


def main() -> None:
    rig = DEFAULT
    pilot = PILOT
    errors = rig.validate() + pilot.validate(rig)
    if errors:
        raise SystemExit("Invalid one-zone pilot geometry: " + "; ".join(errors))

    out = Path(__file__).resolve().parent / "generated_one_zone_pilot"
    out.mkdir(parents=True, exist_ok=True)
    export(out, "x1_pilot_carrier_plate", carrier_plate(pilot))
    export(out, "x1_pilot_load_cell_pod", pilot_pod(rig, pilot))
    export(out, "x1_pilot_zone_pad", zone_pad(rig))
    export(out, "x1_pilot_load_cell_reference", load_cell_reference(rig))
    export(out, "x1_pilot_alignment_jig", alignment_jig(rig))

    authority = {
        "schema_version": 1,
        "fixture_type": "unpowered_one_zone_pilot_only",
        "fit_rig_geometry": rig.authority_report(),
        "pilot_carrier_geometry": asdict(pilot),
        "pilot_validation_errors": pilot.validate(rig),
        "pilot_cad_ready": rig.sensor_mount_pilot_ready and not pilot.validate(rig),
        "four_zone_duplication_ready": False,
        "physical_gates": [
            "verify one real 3135 body and 40 mm hole pattern",
            "verify M5 engagement and flexure clearance",
            "measure unloaded overload-stop gap",
            "measure minimum loaded stop clearance during <=20 kg pilot test",
            "obtain passing Issue #4 pilot authority before duplication",
        ],
        "note": (
            "Auxiliary M4-class pod-to-carrier holes are pilot-only. The carrier "
            "provides a positive bench mounting path without changing the four-zone pod authority."
        ),
    }
    (out / "one_zone_pilot_authority.json").write_text(
        json.dumps(authority, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated one-zone pilot package in {out} [PHYSICAL QUALIFICATION STILL REQUIRED]")


if __name__ == "__main__":
    main()
