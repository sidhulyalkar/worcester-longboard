#!/usr/bin/env python3
"""First-order Worcester X1 sizing model with optional private rider profile."""
import argparse
import csv
import json
import math
from pathlib import Path

KV = 160.0
GEAR = 63 / 9
V_FULL = 58.8
V_NOM = 50.4
D = 0.2032
ETA_SPEED = 0.84
ETA_DRIVE = 0.90
DEFAULT_RIDER_MASS_KG = 50.0
DEFAULT_BOARD_MASS_KG = 20.0
G = 9.80665
KT = 60 / (2 * math.pi * KV)


def _positive_mass(value, field):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be a finite positive mass")
    return value


def load_mass(profile_path=None):
    rider = DEFAULT_RIDER_MASS_KG
    board = DEFAULT_BOARD_MASS_KG
    if profile_path:
        profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
        current = profile.get("mass_kg")
        legacy = profile.get("rider_mass_kg")
        if current is not None and legacy is not None:
            current_value = _positive_mass(current, "mass_kg")
            legacy_value = _positive_mass(legacy, "rider_mass_kg")
            if not math.isclose(current_value, legacy_value, rel_tol=0.0, abs_tol=1e-6):
                raise ValueError("mass_kg conflicts with legacy rider_mass_kg")
        rider_value = current if current is not None else legacy
        if rider_value is not None:
            rider = _positive_mass(rider_value, "mass_kg")
        if profile.get("board_mass_kg") is not None:
            board = _positive_mass(profile["board_mass_kg"], "board_mass_kg")
    return rider, rider + board


def no_load_mph(v):
    motor_rpm = KV * v
    wheel_rpm = motor_rpm / GEAR
    mps = wheel_rpm * math.pi * D / 60
    return mps * 2.2369362921


def wheel_force(phase_a_per_motor):
    motor_torque = KT * phase_a_per_motor
    wheel_torque_each = motor_torque * GEAR * ETA_DRIVE
    return 2 * wheel_torque_each / (D / 2)


def grade_force(grade, mass):
    theta = math.atan(grade)
    return mass * G * math.sin(theta)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", help="optional private rider profile JSON")
    a = ap.parse_args()
    rider_mass, total_mass = load_mass(a.profile)
    rows = []
    for voltage in (V_NOM, V_FULL):
        rows.append(["speed", voltage, "theoretical_no_load_mph", no_load_mph(voltage)])
        rows.append(["speed", voltage, "estimated_loaded_mph", no_load_mph(voltage) * ETA_SPEED])
    for amps in (30, 55, 70, 80):
        rows.append(["traction", amps, "two_motor_wheel_force_N", wheel_force(amps)])
    for grade in (0.1, 0.2, 0.3, 0.4):
        rows.append(["grade", grade, "gravity_force_N", grade_force(grade, total_mass)])
    print(f"Rider mass={rider_mass:.1f} kg; first-order total mass={total_mass:.1f} kg")
    print(f"Kt={KT:.5f} Nm/A, gear={GEAR:.3f}:1")
    print(f"Nominal theoretical/loaded speed: {no_load_mph(V_NOM):.1f}/{no_load_mph(V_NOM) * ETA_SPEED:.1f} mph")
    print(f"Full theoretical/loaded speed: {no_load_mph(V_FULL):.1f}/{no_load_mph(V_FULL) * ETA_SPEED:.1f} mph")
    print(f"Two-motor wheel force @55A phase each: {wheel_force(55):.0f} N")
    print(f"Gravity component @30% grade: {grade_force(.30, total_mass):.0f} N")
    with open(Path(__file__).with_name("design_points.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "input", "metric", "value"])
        writer.writerows(rows)


if __name__ == "__main__":
    main()
