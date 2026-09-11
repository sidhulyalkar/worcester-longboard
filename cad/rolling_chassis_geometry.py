"""Pure-Python geometry authority for Worcester X1 unpowered rolling chassis.

This tranche defines packaging envelopes and manufacturing gates only. Vendor
reference dimensions are useful for collision studies but do not make the
chassis fabrication-ready until selected physical components/drawings, brake
interfaces, and the full motion sweep are verified.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import math


@dataclass(frozen=True)
class WheelEnvelope:
    diameter_mm: float = 250.0
    width_mm: float = 50.0
    axle_diameter_mm: float = 12.0
    source: str = "MBS T2 9in tire 250x50 reference"
    physical_unit_verified: bool = False


@dataclass(frozen=True)
class TruckEnvelope:
    total_width_mm: float = 400.0
    nominal_hanger_mm: float = 300.0
    axle_extension_each_mm: float = 50.0
    max_steer_deg: float = 22.0
    brake_reference_compatible: bool = True
    drive_reference_compatible: bool = False
    source: str = "MBS Matrix III CNC 400mm reference"
    physical_unit_verified: bool = False

    @classmethod
    def drive_clearance_reference(cls) -> "TruckEnvelope":
        return cls(
            total_width_mm=420.0,
            nominal_hanger_mm=280.0,
            axle_extension_each_mm=70.0,
            brake_reference_compatible=False,
            drive_reference_compatible=True,
            source="MBS Matrix III CNC 420mm reference",
        )


@dataclass(frozen=True)
class ChassisEnvelope:
    deck_length_mm: float = 950.0
    deck_max_width_mm: float = 260.0
    deck_reference_thickness_mm: float = 16.0
    wheelbase_mm: float = 820.0
    rider_interface_keepout_length_mm: float = 650.0
    rider_interface_keepout_width_mm: float = 245.0
    static_ground_clearance_mm: float = 65.0
    minimum_compressed_clearance_mm: float = 45.0
    suspension_vertical_travel_allowance_mm: float = 20.0
    wheel_to_deck_clearance_mm: float = 12.0
    drivetrain_guard_radial_allowance_mm: float = 25.0
    brake_rotor_reference_diameter_mm: float = 160.0
    finished_mass_target_kg: float = 18.0
    finished_mass_hard_review_kg: float = 20.0
    brake_interface_verified: bool = False
    motion_sweep_verified: bool = False
    wheel: WheelEnvelope = WheelEnvelope()
    truck: TruckEnvelope = TruckEnvelope()

    @property
    def half_track_mm(self) -> float:
        return self.truck.total_width_mm / 2.0

    @property
    def wheel_radius_mm(self) -> float:
        return self.wheel.diameter_mm / 2.0

    @property
    def steered_wheel_half_extent_x_mm(self) -> float:
        """Conservative half-extent of one rectangular wheel envelope in plan view."""
        a = math.radians(abs(self.truck.max_steer_deg))
        return self.wheel_radius_mm * math.sin(a) + self.wheel.width_mm / 2.0 * math.cos(a)

    @property
    def steered_wheel_half_extent_y_mm(self) -> float:
        a = math.radians(abs(self.truck.max_steer_deg))
        return self.wheel_radius_mm * math.cos(a) + self.wheel.width_mm / 2.0 * math.sin(a)

    @property
    def rider_keepout_margin_each_end_mm(self) -> float:
        return (self.deck_length_mm - self.rider_interface_keepout_length_mm) / 2.0

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not 220.0 <= self.wheel.diameter_mm <= 270.0:
            errors.append("wheel diameter outside X1 8.5-10in packaging range")
        if self.wheel.width_mm < 45.0:
            errors.append("wheel width is too narrow for current off-road reference")
        if self.truck.total_width_mm < self.deck_max_width_mm + 100.0:
            errors.append("truck lacks lateral wheel/deck clearance budget")
        if self.wheelbase_mm >= self.deck_length_mm:
            errors.append("wheelbase must fit within deck reference envelope")
        if self.rider_interface_keepout_length_mm >= self.deck_length_mm:
            errors.append("rider interface keepout consumes entire deck")
        if self.rider_interface_keepout_width_mm > self.deck_max_width_mm:
            errors.append("rider keepout is wider than deck")
        if self.rider_keepout_margin_each_end_mm < 100.0:
            errors.append("insufficient end packaging outside rider keepout")
        if self.static_ground_clearance_mm < self.minimum_compressed_clearance_mm:
            errors.append("static ground clearance is below compressed minimum")
        if self.static_ground_clearance_mm - self.suspension_vertical_travel_allowance_mm < self.minimum_compressed_clearance_mm:
            errors.append("suspension travel violates compressed ground-clearance gate")
        if self.brake_rotor_reference_diameter_mm >= self.wheel.diameter_mm - 2 * self.wheel_to_deck_clearance_mm:
            errors.append("brake rotor reference is too large for wheel envelope")
        if self.finished_mass_target_kg >= self.finished_mass_hard_review_kg:
            errors.append("mass target must remain below hard-review threshold")
        return errors

    @property
    def vendor_envelopes_verified(self) -> bool:
        return self.wheel.physical_unit_verified and self.truck.physical_unit_verified

    @property
    def fabrication_ready(self) -> bool:
        return (
            self.vendor_envelopes_verified
            and self.brake_interface_verified
            and self.motion_sweep_verified
            and not self.validate()
        )

    def with_component_verification(self) -> "ChassisEnvelope":
        return replace(
            self,
            wheel=replace(self.wheel, physical_unit_verified=True),
            truck=replace(self.truck, physical_unit_verified=True),
        )

    def with_full_interface_verification(self) -> "ChassisEnvelope":
        return replace(
            self.with_component_verification(),
            brake_interface_verified=True,
            motion_sweep_verified=True,
        )

    def authority_report(self) -> dict:
        return {
            "schema_version": 1,
            "scope": "unpowered_rolling_chassis_geometry_only",
            "geometry": asdict(self),
            "derived": {
                "wheel_radius_mm": self.wheel_radius_mm,
                "steered_wheel_half_extent_x_mm": self.steered_wheel_half_extent_x_mm,
                "steered_wheel_half_extent_y_mm": self.steered_wheel_half_extent_y_mm,
                "rider_keepout_margin_each_end_mm": self.rider_keepout_margin_each_end_mm,
                "compressed_clearance_after_travel_mm": self.static_ground_clearance_mm - self.suspension_vertical_travel_allowance_mm,
            },
            "validation_errors": self.validate(),
            "vendor_envelopes_verified": self.vendor_envelopes_verified,
            "brake_interface_verified": self.brake_interface_verified,
            "motion_sweep_verified": self.motion_sweep_verified,
            "fabrication_ready": self.fabrication_ready,
            "reference_conflicts": {
                "400mm_brake_first": {
                    "brake_reference_compatible": True,
                    "drive_reference_compatible": False,
                },
                "420mm_drive_clearance": {
                    "brake_reference_compatible": False,
                    "drive_reference_compatible": True,
                },
            },
            "gates": [
                "select truck width only after resolving mechanical-brake versus drive packaging",
                "verify selected truck technical drawing or physical unit",
                "verify selected wheel/hub/tire envelope",
                "define and verify selected mechanical brake rotor/caliper interface",
                "perform and record full steering/suspension interference sweep",
                "preserve rider-interface keepout until Rev-B fit authority",
            ],
        }


BRAKE_FIRST = ChassisEnvelope()
DRIVE_CLEARANCE = replace(BRAKE_FIRST, truck=TruckEnvelope.drive_clearance_reference())
