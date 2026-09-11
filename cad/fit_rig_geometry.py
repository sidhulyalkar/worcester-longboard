"""Pure-Python geometry authority for the unpowered X1 Fit Rig v0.3.

The current Phidgets 3135 mechanical drawing gives a 55 x 12.65 x 12.65 mm
body, two M5x0.8 through holes total, and 40 mm hole-center spacing. X1 uses
that vendor drawing as the one-zone pilot reference while still requiring one
physical sensor to be checked before four final pods are duplicated.

Coordinate convention
---------------------
Sensor origin: geometric center of the sensor body.
+x: loaded/free end. -x: fixed/wire end. +y: across sensor width.
Pod Z datum: bottom face of the printed/machined pod.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Sequence

HoleXY = tuple[float, float]


@dataclass(frozen=True)
class LoadCellEnvelope:
    length_mm: float = 55.0
    width_mm: float = 12.65
    height_mm: float = 12.65
    thread: str = "M5x0.8 THRU"
    fixed_hole_xy_mm: HoleXY = (-20.0, 0.0)
    loaded_hole_xy_mm: HoleXY = (20.0, 0.0)
    pattern_source: str = "Phidgets 3135_0 mechanical drawing Rev 1, 2025-06-04"
    physical_unit_verified: bool = False

    @property
    def vendor_pattern_available(self) -> bool:
        return self.fixed_hole_xy_mm is not None and self.loaded_hole_xy_mm is not None

    @property
    def fabrication_ready(self) -> bool:
        return self.vendor_pattern_available and self.physical_unit_verified and not self.validate()

    def validate(self) -> list[str]:
        errors: list[str] = []
        half_l = self.length_mm / 2
        half_w = self.width_mm / 2
        for label, point, expected_sign in (
            ("fixed", self.fixed_hole_xy_mm, -1),
            ("loaded", self.loaded_hole_xy_mm, +1),
        ):
            x, y = point
            if not (-half_l <= float(x) <= half_l and -half_w <= float(y) <= half_w):
                errors.append(f"{label} hole center ({x}, {y}) lies outside sensor envelope")
            if expected_sign < 0 and x >= 0:
                errors.append(f"fixed hole x={x} must lie on the -x wire/fixed end")
            if expected_sign > 0 and x <= 0:
                errors.append(f"loaded hole x={x} must lie on the +x free/loaded end")
        spacing = self.loaded_hole_xy_mm[0] - self.fixed_hole_xy_mm[0]
        if abs(spacing - 40.0) > 0.25:
            errors.append(f"hole-center spacing {spacing:.3f} mm disagrees with 40 mm vendor drawing")
        return errors

    def with_physical_verification(
        self,
        fixed: Sequence[float],
        loaded: Sequence[float],
        tolerance_mm: float = 0.5,
    ) -> "LoadCellEnvelope":
        fixed_xy = (float(fixed[0]), float(fixed[1]))
        loaded_xy = (float(loaded[0]), float(loaded[1]))
        for label, measured, nominal in (
            ("fixed", fixed_xy, self.fixed_hole_xy_mm),
            ("loaded", loaded_xy, self.loaded_hole_xy_mm),
        ):
            if max(abs(measured[i] - nominal[i]) for i in (0, 1)) > tolerance_mm:
                raise ValueError(f"measured {label} hole differs from vendor pattern by >{tolerance_mm} mm")
        return replace(
            self,
            fixed_hole_xy_mm=fixed_xy,
            loaded_hole_xy_mm=loaded_xy,
            physical_unit_verified=True,
        )


@dataclass(frozen=True)
class FitRigGeometry:
    base_length_mm: float = 700.0
    base_width_mm: float = 300.0
    base_thickness_mm: float = 12.0
    footplate_length_mm: float = 260.0
    footplate_width_mm: float = 132.0
    footplate_thickness_mm: float = 6.0
    zone_pad_length_mm: float = 105.0
    zone_pad_width_mm: float = 78.0
    zone_pad_thickness_mm: float = 6.0
    load_cell_pod_length_mm: float = 92.0
    load_cell_pod_width_mm: float = 38.0
    load_cell_pod_thickness_mm: float = 6.0
    overload_stop_gap_mm: float = 0.8
    overload_stop_diameter_mm: float = 10.0
    electronics_box_length_mm: float = 185.0
    electronics_box_width_mm: float = 125.0
    electronics_box_height_mm: float = 42.0
    electronics_wall_mm: float = 3.0
    rail_slot_length_mm: float = 105.0
    rail_slot_width_mm: float = 6.5
    rail_offset_y_mm: float = 42.0
    load_cell: LoadCellEnvelope = LoadCellEnvelope()

    @property
    def nominal_zone_pad_bottom_z_mm(self) -> float:
        """Pad bottom assuming the sensor sits on the pod top with no spacer."""
        return self.load_cell_pod_thickness_mm + self.load_cell.height_mm

    @property
    def nominal_overload_stop_top_z_mm(self) -> float:
        """Stop top measured from pod bottom, leaving the requested air gap."""
        return self.nominal_zone_pad_bottom_z_mm - self.overload_stop_gap_mm

    @property
    def nominal_overload_stop_clearance_mm(self) -> float:
        return self.nominal_zone_pad_bottom_z_mm - self.nominal_overload_stop_top_z_mm

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.base_length_mm < 2 * self.footplate_length_mm + 80:
            errors.append("base is too short for two independently adjustable footplates")
        if self.base_width_mm < self.footplate_width_mm + 80:
            errors.append("base is too narrow for footplate adjustment and hardware clearance")
        if self.zone_pad_width_mm >= self.footplate_width_mm:
            errors.append("zone pad must fit inside the footplate width")
        if self.load_cell_pod_width_mm <= self.load_cell.width_mm + 8:
            errors.append("load-cell pod lacks lateral clearance")
        if not 0.3 <= self.overload_stop_gap_mm <= 2.0:
            errors.append("overload stop gap outside conservative fixture range")
        if self.nominal_overload_stop_top_z_mm <= self.load_cell_pod_thickness_mm:
            errors.append("overload stop does not rise above pod top")
        if abs(self.nominal_overload_stop_clearance_mm - self.overload_stop_gap_mm) > 1e-9:
            errors.append("overload stop Z-stack does not reproduce requested clearance")
        if self.electronics_wall_mm < 2.0:
            errors.append("electronics enclosure wall is too thin for prototype handling")
        errors.extend(self.load_cell.validate())
        return errors

    @property
    def sensor_mount_pilot_ready(self) -> bool:
        return self.load_cell.vendor_pattern_available and not self.load_cell.validate()

    @property
    def sensor_mount_fabrication_ready(self) -> bool:
        return self.load_cell.fabrication_ready

    def with_load_cell_verification(self, data: dict) -> "FitRigGeometry":
        cell = self.load_cell.with_physical_verification(
            fixed=data["fixed_hole_xy_mm"], loaded=data["loaded_hole_xy_mm"]
        )
        return replace(self, load_cell=cell)

    def authority_report(self) -> dict:
        return {
            "schema_version": 4,
            "fixture_type": "unpowered_fit_rig_only",
            "coordinate_frame": {
                "sensor_origin": "load-cell geometric center",
                "+x": "loaded/free end",
                "-x": "fixed/wire end",
                "+y": "across narrow sensor width",
                "pod_z_origin": "bottom face of load-cell pod",
                "units": "mm",
            },
            "geometry": asdict(self),
            "nominal_z_stack": {
                "pod_top_z_mm": self.load_cell_pod_thickness_mm,
                "zone_pad_bottom_z_mm": self.nominal_zone_pad_bottom_z_mm,
                "overload_stop_top_z_mm": self.nominal_overload_stop_top_z_mm,
                "overload_stop_clearance_mm": self.nominal_overload_stop_clearance_mm,
            },
            "validation_errors": self.validate(),
            "sensor_mount_pilot_ready": self.sensor_mount_pilot_ready,
            "sensor_mount_fabrication_ready": self.sensor_mount_fabrication_ready,
            "measurement_gates": [] if self.sensor_mount_fabrication_ready else [
                "verify one physical 3135 fixed-hole center against vendor pattern",
                "verify one physical 3135 loaded-hole center against vendor pattern",
                "verify overload-stop clearance under real sensor deflection",
            ],
            "note": (
                "The vendor drawing is sufficient for a one-zone pilot pod. Duplicate final "
                "pods only after one physical sensor verifies the drawing and stop clearance."
            ),
        }


DEFAULT = FitRigGeometry()
