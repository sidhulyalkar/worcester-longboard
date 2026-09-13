#!/usr/bin/env python3
"""Validate Worcester X1 mechanical architecture references and release gates."""
from __future__ import annotations

import json
from pathlib import Path

from cad.rolling_chassis_geometry import (
    BRAKE_FIRST,
    DRIVE_CLEARANCE,
    BRAKE_HANGER_70MM_TOPOLOGY_STUDY,
)

ROOT = Path(__file__).resolve().parents[1]


def validate(
    benchmarks: dict,
    risks: dict,
    build: dict,
    planned_bom: dict,
) -> list[str]:
    errors: list[str] = []

    if benchmarks.get("schema_version") != 1:
        errors.append("mechanical benchmarks schema_version must be 1")
    refs = benchmarks.get("references", [])
    ref_ids = {x.get("id") for x in refs if isinstance(x, dict)}
    required_refs = {
        "MBS-COMP95",
        "MBS-MATRIXIII-400",
        "MBS-MATRIXIII-420",
        "MBS-V5",
        "MBS-G1",
        "MBS-AGENT",
        "OWNBOARD-PROMETHEUS",
        "BAJABOARD-G4",
        "BAJABOARD-DIY-CHASSIS",
        "PROPEL-ENDEAVOR",
        "LACROIX-HYPERTRUCK",
        "TRAMPA-FRONT-HYDRAULIC",
        "TRAMPA-SPUR-GEAR",
        "TRAMPA-OPEN-BELT",
        "DIY-FAILURE-CATALOG",
        "DIY-WHEEL-RETENTION",
        "DIY-ENCLOSURE-MOUNT",
    }
    missing_refs = sorted(required_refs - ref_ids)
    if missing_refs:
        errors.append("missing mechanical benchmark refs: " + ", ".join(missing_refs))
    for ref in refs:
        if not isinstance(ref, dict):
            errors.append("mechanical benchmark entry must be an object")
            continue
        if not str(ref.get("url", "")).startswith("https://"):
            errors.append(f"benchmark {ref.get('id')} lacks https URL")
        if not ref.get("observed_architecture") or not ref.get("x1_lesson"):
            errors.append(f"benchmark {ref.get('id')} lacks architecture lesson")

    if risks.get("schema_version") != 1:
        errors.append("mechanical risk register schema_version must be 1")
    risk_items = risks.get("risks", [])
    risk_ids = [x.get("id") for x in risk_items if isinstance(x, dict)]
    if len(risk_ids) != len(set(risk_ids)):
        errors.append("duplicate mechanical risk ids")
    if len(risk_ids) < 15:
        errors.append("mechanical risk register is unexpectedly incomplete")
    risk_map = {x.get("id"): x for x in risk_items if isinstance(x, dict) and x.get("id")}
    for risk in risk_items:
        if not isinstance(risk, dict):
            errors.append("mechanical risk entry must be an object")
            continue
        s = risk.get("severity")
        l = risk.get("likelihood")
        d = risk.get("detectability")
        if not all(isinstance(v, int) and 1 <= v <= 5 for v in (s, l, d)):
            errors.append(f"risk {risk.get('id')} has invalid scoring")
            continue
        if risk.get("priority_score") != s * l * d:
            errors.append(f"risk {risk.get('id')} priority score mismatch")
        if not risk.get("prevention") or not risk.get("verification"):
            errors.append(f"risk {risk.get('id')} lacks prevention/verification")
        if s == 5 and not risk.get("verification"):
            errors.append(f"severity-5 risk lacks physical verification: {risk.get('id')}")
        if not risk.get("must_close_before"):
            errors.append(f"risk {risk.get('id')} lacks release gate")

    for risk_id in ("M13", "M18"):
        risk = risk_map.get(risk_id, {})
        if risk.get("must_close_before") != "dummy_pack_mount_qualified":
            errors.append(f"{risk_id} must close at dummy_pack_mount_qualified")
    if risks.get("rules", {}).get("final_power_freeze_requires_dummy_pack_mount_authority") is not True:
        errors.append("risk rules must require dummy-pack authority before final power freeze")

    # Donor-grounded reference must reflect the selected Comp 95 family while
    # remaining explicitly catalog-derived until the received board is measured.
    if BRAKE_FIRST.wheel.diameter_mm != 194.0:
        errors.append("brake-first wheel must use published 194 mm T1 diameter reference")
    if BRAKE_FIRST.wheel.width_mm != 51.0:
        errors.append("brake-first wheel must use published 51 mm T1 width reference")
    if BRAKE_FIRST.wheelbase_mm != 940.0:
        errors.append("brake-first wheelbase must use published 940 mm Comp 95 reference")
    if BRAKE_FIRST.deck_length_mm != 950.0 or BRAKE_FIRST.deck_max_width_mm != 251.0:
        errors.append("brake-first deck must use published Comp 95 deck envelope")
    if BRAKE_FIRST.vendor_envelopes_verified:
        errors.append("published donor dimensions must not masquerade as received-part verification")
    if BRAKE_FIRST.validate():
        errors.append("donor-grounded brake-first geometry failed internal validation")
    if DRIVE_CLEARANCE.truck.brake_reference_compatible is not False:
        errors.append("420 mm drive reference must remain brake-incompatible")
    if BRAKE_HANGER_70MM_TOPOLOGY_STUDY.truck.total_width_mm != 440.0:
        errors.append("300 mm hanger + 70 mm axle study must remain 440 mm reference")
    if BRAKE_HANGER_70MM_TOPOLOGY_STUDY.truck.brake_reference_compatible is not False:
        errors.append("70 mm axle brake alignment must remain unqualified, never assumed true")

    gates = build.get("gates", {})
    topology = gates.get("brake_drive_topology_qualified")
    if not isinstance(topology, dict):
        errors.append("build authority lacks brake_drive_topology_qualified gate")
    else:
        if topology.get("issue") != 19:
            errors.append("brake-drive topology gate must point to Issue #19")
        required = set(topology.get("requires", []))
        if not {"brake_interface_qualified", "rolling_chassis_physical_qualified"}.issubset(required):
            errors.append("brake-drive topology gate lacks physical brake/chassis prerequisites")

    packaging = gates.get("power_packaging_candidate_defined")
    if not isinstance(packaging, dict):
        errors.append("build authority lacks power_packaging_candidate_defined gate")
    else:
        required = set(packaging.get("requires", []))
        if not {"brake_drive_topology_qualified", "rev_b_template_qualified"}.issubset(required):
            errors.append("power packaging candidate lacks topology/Rev-B prerequisites")

    dummy = gates.get("dummy_pack_mount_qualified")
    if not isinstance(dummy, dict):
        errors.append("build authority lacks dummy_pack_mount_qualified gate")
    else:
        if dummy.get("issue") != 21:
            errors.append("dummy-pack mount gate must point to Issue #21")
        required = set(dummy.get("requires", []))
        if not {"power_packaging_candidate_defined", "rolling_chassis_physical_qualified"}.issubset(required):
            errors.append("dummy-pack mount gate lacks candidate/chassis prerequisites")

    power = gates.get("power_architecture_frozen", {})
    required_power = set(power.get("requires", []))
    if "brake_drive_topology_qualified" not in required_power:
        errors.append("power architecture can freeze without brake-drive topology authority")
    if "dummy_pack_mount_qualified" not in required_power:
        errors.append("power architecture can freeze without inert dummy-pack mount authority")
    if "rev_b_template_qualified" not in required_power:
        errors.append("power architecture can freeze without Rev-B template authority")

    subsystems = {x.get("id"): x for x in planned_bom.get("subsystems", []) if isinstance(x, dict)}
    topology_subsystem = subsystems.get("BRAKE-DRIVE-TOPOLOGY")
    if not topology_subsystem or topology_subsystem.get("freeze_gate") != "brake_drive_topology_qualified":
        errors.append("planned BOM must preserve explicit BRAKE-DRIVE-TOPOLOGY subsystem")
    packaging_subsystem = subsystems.get("POWER-PACKAGING-CANDIDATE")
    if not packaging_subsystem or packaging_subsystem.get("freeze_gate") != "power_packaging_candidate_defined":
        errors.append("planned BOM must preserve explicit POWER-PACKAGING-CANDIDATE subsystem")
    dummy_subsystem = subsystems.get("DUMMY-PACK-MOUNT")
    if not dummy_subsystem or dummy_subsystem.get("freeze_gate") != "dummy_pack_mount_qualified":
        errors.append("planned BOM must preserve explicit DUMMY-PACK-MOUNT subsystem")
    if planned_bom.get("rules", {}).get("final_power_freeze_requires_inert_dummy_pack_mount") is not True:
        errors.append("planned BOM must require inert dummy-pack mount before final power freeze")

    for sid in ("DRIVE", "MOTOR-CONTROL", "TRACTION-BATTERY"):
        item = subsystems.get(sid)
        if not item or item.get("status") != "POWER_GATED_TBD":
            errors.append(f"{sid} must remain POWER_GATED_TBD")
        elif item.get("freeze_gate") != "power_architecture_frozen":
            errors.append(f"{sid} must freeze only after power_architecture_frozen")

    return errors


def main() -> None:
    benchmarks = json.loads((ROOT / "hardware/mechanical_reference_benchmarks_2026-09-11.json").read_text())
    risks = json.loads((ROOT / "hardware/mechanical_risk_register.json").read_text())
    build = json.loads((ROOT / "hardware/build_authority.json").read_text())
    planned_bom = json.loads((ROOT / "hardware/planned_system_bom.json").read_text())
    errors = validate(benchmarks, risks, build, planned_bom)
    report = {
        "valid": not errors,
        "errors": errors,
        "risk_count": len(risks.get("risks", [])),
        "benchmark_count": len(benchmarks.get("references", [])),
    }
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
