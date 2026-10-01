#!/usr/bin/env python3
"""Analyze Rev-C energy architectures without selecting a battery or charger.

Published battery facts come from the dated reference snapshot. Derived values
such as Wh/lb and planning range are arithmetic comparisons only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulation.range_envelope import planning_envelope


def analyze(snapshot: dict) -> dict:
    errors: list[str] = []
    if snapshot.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if snapshot.get("scope") != "rev_c_energy_charge_reference_snapshot":
        errors.append("wrong energy snapshot scope")
    if snapshot.get("facts_only") is not True:
        errors.append("snapshot must remain facts_only")

    refs = snapshot.get("commercial_references")
    if not isinstance(refs, list) or not refs:
        errors.append("commercial_references must be nonempty")
        refs = []

    rows = []
    for ref in refs:
        try:
            energy = float(ref["nominal_energy_wh"])
            mass = float(ref["weight_lb"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{ref.get('id')}: energy and mass are required")
            continue
        if energy <= 0 or mass <= 0:
            errors.append(f"{ref.get('id')}: energy and mass must be positive")
            continue

        rows.append(
            {
                "id": ref.get("id"),
                "nominal_energy_wh": energy,
                "weight_lb": mass,
                "specific_energy_wh_per_lb": round(energy / mass, 2),
                "trail_range_miles_20pct_reserve": planning_envelope(
                    energy, "trail", 0.20
                ).as_dict()["range_miles"],
                "mixed_range_miles_20pct_reserve": planning_envelope(
                    energy, "mixed", 0.20
                ).as_dict()["range_miles"],
                "availability_snapshot": ref.get("availability_snapshot"),
                "quick_swap": ref.get("quick_swap"),
            }
        )

    by_id = {row["id"]: row for row in rows}
    comparison = {}
    small = by_id.get("MBS_AGENT_540")
    large = by_id.get("MBS_AGENT_1080")
    if small and large:
        dual_small_energy = 2 * small["nominal_energy_wh"]
        dual_small_mass = 2 * small["weight_lb"]
        comparison = {
            "two_540_inventory_reference": {
                "nominal_trip_energy_wh": dual_small_energy,
                "total_battery_inventory_mass_lb": dual_small_mass,
                "installed_battery_mass_lb_during_cold_swap_operation": small[
                    "weight_lb"
                ],
                "simultaneous_on_board_installation_assumed": False,
                "safe_spare_location_required": True,
                "rider_body_carry_default": False,
            },
            "one_1080_reference": {
                "nominal_trip_energy_wh": large["nominal_energy_wh"],
                "total_battery_inventory_mass_lb": large["weight_lb"],
                "installed_battery_mass_lb": large["weight_lb"],
            },
            "energy_delta_wh_two_540_minus_1080": round(
                dual_small_energy - large["nominal_energy_wh"], 1
            ),
            "inventory_mass_delta_lb_two_540_minus_1080": round(
                dual_small_mass - large["weight_lb"], 1
            ),
            "installed_mass_delta_lb_one_540_minus_1080": round(
                small["weight_lb"] - large["weight_lb"], 1
            ),
            "interpretation": (
                "Cold swapping separates installed board mass from total battery "
                "inventory mass. One 540 reference would keep 15 lb installed while "
                "a second pack exists only at a safe logistics point; one 1089 Wh "
                "reference installs 20 lb continuously. Near-equal trip energy therefore "
                "creates a handling-versus-logistics trade, not a simple 30-versus-20 lb "
                "vehicle-mass comparison."
            ),
        }

    return {
        "schema_version": 1,
        "authority": "x1_rev_c_energy_trade_analysis",
        "valid": not errors,
        "errors": errors,
        "physical_authority": False,
        "procurement_authority": False,
        "charger_compatibility_authority": False,
        "powered_operation_authorized": False,
        "reference_rows": rows,
        "architecture_comparison": comparison,
        "decision_boundaries": [
            "Planning range is not a product range claim.",
            "Published pack mass does not include X1-specific retention or enclosure mass.",
            "No battery or charger is selected by this analysis.",
            "Cold swap remains powered-off only unless a selected qualified system explicitly supports otherwise.",
            "Do not carry an unprotected spare traction pack on the rider as a default range strategy.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "snapshot",
        type=Path,
        nargs="?",
        default=Path("hardware/rev_c_energy_charge_snapshot_2026-10-01.json"),
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = analyze(json.loads(args.snapshot.read_text(encoding="utf-8")))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
