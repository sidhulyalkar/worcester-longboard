#!/usr/bin/env python3
"""Screen Worcester X1 propulsion candidates against force, traction, current,
power, ERPM and geometric speed constraints.

This is a first-order rejection/sensitivity model only. It cannot select a
drive, configure a controller/battery, qualify thermal behavior, authorize
procurement, or authorize powered operation.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

G = 9.80665
MPH_PER_MPS = 2.2369362920544
TOPOLOGIES = {"front", "rear", "awd"}
SPEED_BASES = {"nominal", "full"}


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _positive(value: Any) -> bool:
    return _finite(value) and float(value) > 0


def _nonnegative(value: Any) -> bool:
    return _finite(value) and float(value) >= 0


def ideal_kt_nm_per_a(kv_rpm_per_v: float) -> float:
    return 60.0 / (2.0 * math.pi * float(kv_rpm_per_v))


def validate_config(config: dict) -> list[str]:
    errors: list[str] = []
    if config.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if config.get("scope") != "rev_c_powertrain_envelope":
        errors.append("wrong powertrain-envelope scope")

    vehicle = config.get("vehicle")
    if not isinstance(vehicle, dict):
        errors.append("vehicle must be an object")
        vehicle = {}

    for key in (
        "total_mass_kg",
        "wheelbase_m",
        "cg_from_rear_m",
        "cg_height_m",
        "wheel_diameter_m",
    ):
        if not _positive(vehicle.get(key)):
            errors.append(f"vehicle.{key} must be finite and positive")

    wheelbase = vehicle.get("wheelbase_m")
    cg_x = vehicle.get("cg_from_rear_m")
    if _positive(wheelbase) and _positive(cg_x):
        if not 0 < float(cg_x) < float(wheelbase):
            errors.append(
                "vehicle.cg_from_rear_m must lie between rear and front contacts"
            )

    crr = vehicle.get("rolling_resistance_coeff")
    if not _nonnegative(crr) or float(crr) >= 0.5:
        errors.append("vehicle.rolling_resistance_coeff must be in [0, 0.5)")

    cda = vehicle.get("aero_drag_area_m2", 0.0)
    if not _nonnegative(cda):
        errors.append("vehicle.aero_drag_area_m2 must be finite and nonnegative")
    rho = vehicle.get("air_density_kg_m3", 1.225)
    if not _positive(rho):
        errors.append("vehicle.air_density_kg_m3 must be finite and positive")

    candidate = config.get("candidate")
    if not isinstance(candidate, dict):
        errors.append("candidate must be an object")
        candidate = {}

    if not isinstance(candidate.get("id"), str) or not candidate.get("id", "").strip():
        errors.append("candidate.id must be a nonempty string")
    if candidate.get("topology") not in TOPOLOGIES:
        errors.append("candidate.topology must be front, rear, or awd")

    motor_count = candidate.get("motor_count")
    if not isinstance(motor_count, int) or isinstance(motor_count, bool) or motor_count <= 0:
        errors.append("candidate.motor_count must be a positive integer")

    pole_pairs = candidate.get("motor_pole_pairs")
    if not isinstance(pole_pairs, int) or isinstance(pole_pairs, bool) or pole_pairs <= 0:
        errors.append("candidate.motor_pole_pairs must be a positive integer")

    for key in (
        "motor_kv_rpm_per_v",
        "nominal_voltage_v",
        "full_voltage_v",
        "phase_current_limit_a_per_motor",
        "battery_current_limit_a_total",
        "erpm_limit",
        "drivetrain_efficiency",
        "electrical_efficiency",
    ):
        if not _positive(candidate.get(key)):
            errors.append(f"candidate.{key} must be finite and positive")

    for key in ("drivetrain_efficiency", "electrical_efficiency"):
        value = candidate.get(key)
        if _positive(value) and float(value) > 1.0:
            errors.append(f"candidate.{key} must be <= 1")

    nominal = candidate.get("nominal_voltage_v")
    full = candidate.get("full_voltage_v")
    if _positive(nominal) and _positive(full) and float(full) < float(nominal):
        errors.append("candidate.full_voltage_v must be >= nominal_voltage_v")

    for key in ("wheel_gear_teeth", "motor_gear_teeth"):
        value = candidate.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            errors.append(f"candidate.{key} must be a positive integer")

    if candidate.get("speed_voltage_basis") not in SPEED_BASES:
        errors.append("candidate.speed_voltage_basis must be nominal or full")

    power_limit = candidate.get("electrical_power_limit_w_total")
    if power_limit is not None and not _positive(power_limit):
        errors.append(
            "candidate.electrical_power_limit_w_total must be null or positive"
        )

    scenarios = config.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append("scenarios must be a nonempty list")
        scenarios = []

    names: set[str] = set()
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            errors.append(f"scenario {index} must be an object")
            continue
        name = scenario.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"scenario {index} requires a nonempty name")
        elif name in names:
            errors.append(f"duplicate scenario name: {name}")
        else:
            names.add(name)
        if not _nonnegative(scenario.get("grade")):
            errors.append(f"{name or index}: grade must be finite and nonnegative")
        if not _nonnegative(scenario.get("target_speed_mps")):
            errors.append(
                f"{name or index}: target_speed_mps must be finite and nonnegative"
            )
        if not _nonnegative(scenario.get("acceleration_mps2")):
            errors.append(
                f"{name or index}: acceleration_mps2 must be finite and nonnegative"
            )
        if not _positive(scenario.get("assumed_mu")):
            errors.append(f"{name or index}: assumed_mu must be finite and positive")

    for key in (
        "physical_authority",
        "procurement_authority",
        "controller_configuration_authority",
        "battery_configuration_authority",
        "powered_operation_authorized",
    ):
        if config.get(key) is not False:
            errors.append(f"{key} must be false")

    return errors


def _axle_normals(
    *,
    mass_kg: float,
    wheelbase_m: float,
    cg_from_rear_m: float,
    cg_height_m: float,
    grade: float,
    acceleration_mps2: float,
) -> tuple[float, float, float]:
    theta = math.atan(grade)
    normal_total = mass_kg * G * math.cos(theta)
    front = (
        mass_kg * G * math.cos(theta) * cg_from_rear_m
        - mass_kg
        * (G * math.sin(theta) + acceleration_mps2)
        * cg_height_m
    ) / wheelbase_m
    rear = normal_total - front
    return front, rear, normal_total


def analyze_scenario(config: dict, scenario: dict) -> dict:
    vehicle = config["vehicle"]
    candidate = config["candidate"]

    mass = float(vehicle["total_mass_kg"])
    wheelbase = float(vehicle["wheelbase_m"])
    cg_x = float(vehicle["cg_from_rear_m"])
    cg_h = float(vehicle["cg_height_m"])
    diameter = float(vehicle["wheel_diameter_m"])
    radius = diameter / 2.0
    crr = float(vehicle["rolling_resistance_coeff"])
    cda = float(vehicle.get("aero_drag_area_m2", 0.0))
    rho = float(vehicle.get("air_density_kg_m3", 1.225))

    grade = float(scenario["grade"])
    speed = float(scenario["target_speed_mps"])
    accel = float(scenario["acceleration_mps2"])
    assumed_mu = float(scenario["assumed_mu"])
    theta = math.atan(grade)

    f_grade = mass * G * math.sin(theta)
    f_roll = crr * mass * G * math.cos(theta)
    f_accel = mass * accel
    f_aero = 0.5 * rho * cda * speed * speed
    f_total = f_grade + f_roll + f_accel + f_aero

    front_n, rear_n, total_n = _axle_normals(
        mass_kg=mass,
        wheelbase_m=wheelbase,
        cg_from_rear_m=cg_x,
        cg_height_m=cg_h,
        grade=grade,
        acceleration_mps2=accel,
    )

    topology = candidate["topology"]
    if topology == "front":
        driven_normal = front_n
    elif topology == "rear":
        driven_normal = rear_n
    else:
        driven_normal = total_n

    required_mu = None if driven_normal <= 0 else f_total / driven_normal
    traction_force_limit = max(0.0, assumed_mu * driven_normal)
    traction_margin = traction_force_limit - f_total

    motor_count = int(candidate["motor_count"])
    wheel_teeth = int(candidate["wheel_gear_teeth"])
    motor_teeth = int(candidate["motor_gear_teeth"])
    ratio = wheel_teeth / motor_teeth
    eta_drive = float(candidate["drivetrain_efficiency"])
    eta_electrical = float(candidate["electrical_efficiency"])
    kv = float(candidate["motor_kv_rpm_per_v"])
    kt = ideal_kt_nm_per_a(kv)

    wheel_torque_total = f_total * radius
    motor_torque_each = (
        wheel_torque_total / (motor_count * ratio * eta_drive)
    )
    ideal_phase_current_each = motor_torque_each / kt

    circumference = math.pi * diameter
    wheel_rpm = 0.0 if circumference <= 0 else speed / circumference * 60.0
    motor_rpm = wheel_rpm * ratio
    erpm = motor_rpm * int(candidate["motor_pole_pairs"])

    wheel_power = f_total * speed
    mechanical_motor_input_power = (
        wheel_power / eta_drive if eta_drive > 0 else math.inf
    )
    estimated_electrical_power = (
        mechanical_motor_input_power / eta_electrical
        if eta_electrical > 0
        else math.inf
    )
    nominal_voltage = float(candidate["nominal_voltage_v"])
    full_voltage = float(candidate["full_voltage_v"])
    battery_current_nominal = estimated_electrical_power / nominal_voltage
    battery_current_full = estimated_electrical_power / full_voltage

    motor_no_load_rpm_nominal = kv * nominal_voltage
    motor_no_load_rpm_full = kv * full_voltage
    wheel_no_load_rpm_nominal = motor_no_load_rpm_nominal / ratio
    wheel_no_load_rpm_full = motor_no_load_rpm_full / ratio
    no_load_speed_nominal = wheel_no_load_rpm_nominal / 60.0 * circumference
    no_load_speed_full = wheel_no_load_rpm_full / 60.0 * circumference

    basis = candidate["speed_voltage_basis"]
    basis_speed = (
        no_load_speed_nominal if basis == "nominal" else no_load_speed_full
    )
    speed_margin = basis_speed - speed
    nominal_speed_fraction = (
        speed / no_load_speed_nominal if no_load_speed_nominal > 0 else math.inf
    )
    full_speed_fraction = (
        speed / no_load_speed_full if no_load_speed_full > 0 else math.inf
    )

    phase_limit = float(candidate["phase_current_limit_a_per_motor"])
    battery_limit = float(candidate["battery_current_limit_a_total"])
    erpm_limit = float(candidate["erpm_limit"])
    power_limit = candidate.get("electrical_power_limit_w_total")

    checks = {
        "traction": {
            "passed": driven_normal > 0 and traction_margin >= 0,
            "margin_n": traction_margin,
        },
        "phase_current": {
            "passed": ideal_phase_current_each <= phase_limit,
            "required_a_per_motor": ideal_phase_current_each,
            "limit_a_per_motor": phase_limit,
            "margin_a_per_motor": phase_limit - ideal_phase_current_each,
        },
        "battery_current": {
            "passed": battery_current_nominal <= battery_limit,
            "estimated_a_at_nominal_voltage": battery_current_nominal,
            "limit_a_total": battery_limit,
            "margin_a": battery_limit - battery_current_nominal,
        },
        "erpm": {
            "passed": erpm <= erpm_limit,
            "required_erpm": erpm,
            "limit_erpm": erpm_limit,
            "margin_erpm": erpm_limit - erpm,
        },
        "geometric_speed": {
            "passed": speed_margin >= 0,
            "basis": basis,
            "basis_no_load_speed_mps": basis_speed,
            "target_speed_mps": speed,
            "margin_mps": speed_margin,
        },
    }

    if power_limit is None:
        checks["electrical_power"] = {
            "passed": True,
            "limit_declared": False,
            "estimated_w": estimated_electrical_power,
            "limit_w": None,
            "margin_w": None,
        }
    else:
        power_limit = float(power_limit)
        checks["electrical_power"] = {
            "passed": estimated_electrical_power <= power_limit,
            "limit_declared": True,
            "estimated_w": estimated_electrical_power,
            "limit_w": power_limit,
            "margin_w": power_limit - estimated_electrical_power,
        }

    rejection_reasons = [
        name for name, result in checks.items() if result["passed"] is not True
    ]

    return {
        "name": scenario["name"],
        "grade": grade,
        "grade_angle_deg": math.degrees(theta),
        "target_speed_mps": speed,
        "target_speed_mph": speed * MPH_PER_MPS,
        "acceleration_mps2": accel,
        "assumed_mu": assumed_mu,
        "force_components_n": {
            "grade": f_grade,
            "rolling_resistance": f_roll,
            "acceleration": f_accel,
            "aerodynamic": f_aero,
            "required_total": f_total,
        },
        "normal_loads_n": {
            "front": front_n,
            "rear": rear_n,
            "total": total_n,
            "driven": driven_normal,
        },
        "traction": {
            "required_mu": required_mu,
            "assumed_mu": assumed_mu,
            "force_limit_n": traction_force_limit,
            "force_margin_n": traction_margin,
        },
        "drivetrain": {
            "ratio_wheel_over_motor": ratio,
            "wheel_torque_total_nm": wheel_torque_total,
            "motor_torque_each_nm": motor_torque_each,
            "ideal_kt_nm_per_a": kt,
            "ideal_phase_current_a_per_motor": ideal_phase_current_each,
        },
        "speed_electrical": {
            "wheel_rpm": wheel_rpm,
            "motor_rpm": motor_rpm,
            "erpm": erpm,
            "no_load_speed_nominal_mps": no_load_speed_nominal,
            "no_load_speed_nominal_mph": no_load_speed_nominal * MPH_PER_MPS,
            "no_load_speed_full_mps": no_load_speed_full,
            "no_load_speed_full_mph": no_load_speed_full * MPH_PER_MPS,
            "target_fraction_of_no_load_nominal": nominal_speed_fraction,
            "target_fraction_of_no_load_full": full_speed_fraction,
        },
        "power": {
            "wheel_mechanical_power_w": wheel_power,
            "motor_side_mechanical_power_before_drive_loss_w": mechanical_motor_input_power,
            "estimated_battery_input_power_w": estimated_electrical_power,
            "estimated_battery_current_a_at_nominal_voltage": battery_current_nominal,
            "estimated_battery_current_a_at_full_voltage": battery_current_full,
        },
        "checks": checks,
        "passes_declared_first_order_envelope": not rejection_reasons,
        "rejection_reasons": rejection_reasons,
        "thermal_qualification": False,
        "physical_authority": False,
        "procurement_authority": False,
        "controller_configuration_authority": False,
        "battery_configuration_authority": False,
        "powered_operation_authorized": False,
    }


def analyze(config: dict) -> dict:
    errors = validate_config(config)
    if errors:
        return {
            "schema_version": 1,
            "authority": "x1_rev_c_powertrain_envelope_analysis",
            "valid": False,
            "errors": errors,
            "physical_authority": False,
            "procurement_authority": False,
            "controller_configuration_authority": False,
            "battery_configuration_authority": False,
            "thermal_qualification": False,
            "powered_operation_authorized": False,
        }

    scenarios = [analyze_scenario(config, s) for s in config["scenarios"]]
    return {
        "schema_version": 1,
        "authority": "x1_rev_c_powertrain_envelope_analysis",
        "valid": True,
        "errors": [],
        "candidate_id": config["candidate"]["id"],
        "topology": config["candidate"]["topology"],
        "candidate": copy.deepcopy(config["candidate"]),
        "vehicle": copy.deepcopy(config["vehicle"]),
        "scenarios": scenarios,
        "all_scenarios_pass_declared_first_order_envelope": all(
            s["passes_declared_first_order_envelope"] for s in scenarios
        ),
        "failed_scenarios": [
            s["name"]
            for s in scenarios
            if not s["passes_declared_first_order_envelope"]
        ],
        "assumptions": [
            "quasi-static longitudinal load transfer",
            "ideal Kt derived from motor Kv",
            "steady-state battery input power estimate",
            "no detailed motor winding-resistance, saturation or field-weakening model",
            "no thermal model",
            "no lateral load transfer, tire sinkage or transient wheel-hop model",
            "no-load speed is a geometric electrical ceiling, not predicted ride speed",
        ],
        "thermal_qualification": False,
        "physical_authority": False,
        "procurement_authority": False,
        "controller_configuration_authority": False,
        "battery_configuration_authority": False,
        "powered_operation_authorized": False,
    }


def sweep_pinions(config: dict, pinions: list[int]) -> dict:
    rows = []
    seen: set[int] = set()
    for pinion in pinions:
        if not isinstance(pinion, int) or isinstance(pinion, bool) or pinion <= 0:
            rows.append(
                {
                    "motor_gear_teeth": pinion,
                    "valid": False,
                    "errors": ["pinion tooth count must be a positive integer"],
                }
            )
            continue
        if pinion in seen:
            continue
        seen.add(pinion)

        candidate_config = copy.deepcopy(config)
        candidate_config["candidate"]["motor_gear_teeth"] = pinion
        candidate_config["candidate"]["id"] = (
            f"{config['candidate'].get('id', 'candidate')}-pinion-{pinion}"
        )
        result = analyze(candidate_config)
        rows.append(
            {
                "motor_gear_teeth": pinion,
                "ratio_wheel_over_motor": (
                    config["candidate"].get("wheel_gear_teeth", 0) / pinion
                    if _positive(config["candidate"].get("wheel_gear_teeth"))
                    else None
                ),
                "valid": result["valid"],
                "all_scenarios_pass_declared_first_order_envelope": result.get(
                    "all_scenarios_pass_declared_first_order_envelope"
                ),
                "failed_scenarios": result.get("failed_scenarios", []),
                "scenario_results": result.get("scenarios", []),
                "errors": result.get("errors", []),
            }
        )

    passing = [
        row["motor_gear_teeth"]
        for row in rows
        if row.get("valid")
        and row.get("all_scenarios_pass_declared_first_order_envelope")
    ]
    return {
        "schema_version": 1,
        "authority": "x1_rev_c_powertrain_ratio_sweep",
        "valid": bool(rows) and all(row.get("valid") for row in rows),
        "base_candidate_id": config.get("candidate", {}).get("id"),
        "wheel_gear_teeth": config.get("candidate", {}).get("wheel_gear_teeth"),
        "pinion_results": rows,
        "passing_motor_gear_teeth": passing,
        "selection_made": False,
        "thermal_qualification": False,
        "physical_authority": False,
        "procurement_authority": False,
        "controller_configuration_authority": False,
        "battery_configuration_authority": False,
        "powered_operation_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--sweep-pinions", type=int, nargs="*")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.sweep_pinions is not None:
        report = sweep_pinions(config, args.sweep_pinions)
    else:
        report = analyze(config)

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
