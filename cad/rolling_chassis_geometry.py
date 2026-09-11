"""Pure-Python geometry authority for Worcester X1 unpowered rolling chassis.

The default brake-first reference is now grounded in the published MBS Comp 95
geometry because that is the preferred donor strategy. Published dimensions are
still not a substitute for received-part measurements: physical_unit_verified
remains false until the actual donor is measured.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import math


@dataclass(frozen=True)
class WheelEnvelope:
    # MBS publishes the T1 as nominal 200x50 while the current product page
    # gives 194 mm actual tire diameter and 51 mm width. Use the physical-size
    # reference for collision packaging, not the nominal product name.
    diameter_mm: float = 194.0
    width_mm: float = 51.0
    axle_diameter_mm: float = 12.0
    nominal_size: str = "200x50 (8-inch class)"
    source: str = "MBS T1 8in 200x50; published tire diameter 194mm, width 51mm"
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
            source="MBS Matrix III CNC 420mm / 70mm axle drive reference",
        )

    @classmethod
    def brake_hanger_with_70mm_axles_reference(cls) -> "TruckEnvelope":
        # Vendor text describes the 300 mm 400-series hanger upgraded with
        # 70 mm axles as an ultra-wide 440 mm drivetrain-capable variant. Brake
        # rotor alignment after this swap is intentionally UNKNOWN.
        return cls(
            total_width_mm=440.0,
            nominal_hanger_mm=300.0,
            axle_extension_each_mm=70.0,
            brake_reference_compatible=False,
            drive_reference_compatible=True,
            source="Matrix III 300mm hanger + 70mm axle topology-study reference",
        )


@dataclass(frozen=True)
class ChassisEnvelope:
    # Published Comp 95 references.
    deck_length_mm: float = 950.0
    deck_max_width_mm: float = 251.0
    wheelbase_mm: float = 940.0
    published_overall_length_mm: float = 1140.0
    donor_unpowered_mass_reference_kg: float = 6.6

    # Still-provisional packaging values. These remain measurement gates.
    deck_reference_thickness_mm: float = 16.0
    rider_interface_keepout_length_mm: float = 650.0
    rider_interface_keepout_width_mm: float = 240.0
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
    def wheel_radius_mm(self) -> float:
        return self.wheel.diameter_mm / 2.0

    @property
    def wheel_center_lateral_mm(self) -> float:
        """Reference wheel center from board centerline.

        The truck width is hanger plus two axle extensions. Before a physical
        hub stack is measured, place the wheel center approximately halfway
        along each axle extension instead of incorrectly placing it at the axle
        tip.
        """
        return self.truck.nominal_hanger_mm / 2.0 + self.truck.axle_extension_each_mm / 2.0

    @property
    def estimated_outer_wheel_envelope_width_mm(self) -> float:
        return 2.0 * self.wheel_center_lateral_mm + self.wheel.width_mm

    @property
    def steered_wheel_half_extent_x_mm(self) -> float:
        """Plan-view longitudinal half-extent of a yawed wheel rectangle."""
        a = math.radians(abs(self.truck.max_steer_deg))
        return self.wheel_radius_mm * math.cos(a) + self.wheel.width_mm / 2.0 * math.sin(a)

    @property
    def steered_wheel_half_extent_y_mm(self) -> float:
        """Plan-view lateral half-extent of a yawed wheel rectangle."""
        a = math.radians(abs(self.truck.max_steer_deg))
        return self.wheel_radius_mm * math.sin(a) + self.wheel.width_mm / 2.0 * math.cos(a)

    @property
    def rider_keepout_margin_each_end_mm(self) -> float:
        return (self.deck_length_mm - self.rider_interface_keepout_length_mm) / 2.0

    @property
    def derived_overall_length_mm(self) -> float:
        # Useful sanity check for the published donor geometry: axle-to-axle
        # plus one tire diameter should be close to the board's overall length.
        return self.wheelbase_mm + self.wheel.diameter_mm

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not 185.0 <= self.wheel.diameter_mm <= 270.0:
            errors.append("wheel diameter outside X1 8-10in physical packaging range")
        if self.wheel.width_mm < 45.0:
            errors.append("wheel width is too narrow for current off-road reference")
        if self.truck.total_width_mm < self.deck_max_width_mm + 100.0:
            errors.append("truck lacks lateral wheel/deck clearance budget")
        if self.wheelbase_mm > self.published_overall_length_mm:
            errors.append("wheelbase cannot exceed published overall board length")
        if abs(self.derived_overall_length_mm - self.published_overall_length_mm) > 20.0:
            errors.append("wheelbase + tire-diameter sanity check disagrees with published donor length")
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
            "schema_version": 2,
            "scope": "unpowered_rolling_chassis_geometry_only",
            "geometry": asdict(self),
            "derived": {
                "wheel_radius_mm": self.wheel_radius_mm,
                "wheel_center_lateral_mm": self.wheel_center_lateral_mm,
                "estimated_outer_wheel_envelope_width_mm": self.estimated_outer_wheel_envelope_width_mm,
                "steered_wheel_half_extent_x_mm": self.steered_wheel_half_extent_x_mm,
                "steered_wheel_half_extent_y_mm": self.steered_wheel_half_extent_y_mm,
                "rider_keepout_margin_each_end_mm": self.rider_keepout_margin_each_end_mm,
                "derived_overall_length_mm": self.derived_overall_length_mm,
                "compressed_clearance_after_travel_mm": self.static_ground_clearance_mm - self.suspension_vertical_travel_allowance_mm,
            },
            "validation_errors": self.validate(),
            "vendor_envelopes_verified": self.vendor_envelopes_verified,
            "brake_interface_verified": self.brake_interface_verified,
            "motion_sweep_verified": self.motion_sweep_verified,
            "fabrication_ready": self.fabrication_ready,
            "reference_conflicts": {
                "400mm_50mm_axle_brake_first": {
                    "brake_reference_compatible": True,
                    "drive_reference_compatible": False,
                },
                "420mm_70mm_axle_drive_reference": {
                    "brake_reference_compatible": False,
                    "drive_reference_compatible": True,
                },
                "300mm_hanger_70mm_axle_440mm_topology_study": {
                    "brake_reference_compatible": "UNKNOWN_AFTER_AXLE_SWAP",
                    "drive_reference_compatible": True,
                },
            },
            "gates": [
                "measure received Comp 95 tire/hub/truck/deck geometry",
                "measure actual static/compressed clearance instead of promoting provisional Z values",
                "qualify V5 brake interface on its received 400mm/50mm-axle configuration",
                "resolve Issue #19 brake-drive topology before selecting drivetrain hardware",
                "perform and record full steering/suspension/drive/brake interference sweep",
                "preserve rider-interface keepout until Rev-B fit authority",
            ],
        }


BRAKE_FIRST = ChassisEnvelope()
DRIVE_CLEARANCE = replace(BRAKE_FIRST, truck=TruckEnvelope.drive_clearance_reference())
BRAKE_HANGER_70MM_TOPOLOGY_STUDY = replace(
    BRAKE_FIRST, truck=TruckEnvelope.brake_hanger_with_70mm_axles_reference()
)
