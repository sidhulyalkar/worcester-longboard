#!/usr/bin/env python3
"""Analyze measured X1 brake/drive axial intervals from a shared datum.

This tool is intentionally one-dimensional. It is useful for quickly rejecting
Candidate A layouts when rotor, pad, coupler, guard, hub, or brake-arm swept
volumes already conflict axially. A PASS here is never sufficient to qualify the
topology because 3-D steering/lean sweeps, retention, serviceability, and physical
tests remain mandatory.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _interval(entry: dict) -> tuple[float, float] | None:
    start = entry.get("start_mm")
    end = entry.get("end_mm")
    if not _finite(start) or not _finite(end):
        return None
    start, end = float(start), float(end)
    if start > end:
        return None
    return start, end


def interval_gap(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Positive separation, zero touch, negative overlap depth."""
    if a[1] < b[0]:
        return b[0] - a[1]
    if b[1] < a[0]:
        return a[0] - b[1]
    return -min(a[1], b[1]) + max(a[0], b[0])


def analyze(config: dict) -> dict:
    errors: list[str] = []
    if config.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if config.get("scope") != "brake_drive_axial_stack_analysis":
        errors.append("wrong axial-stack scope")
    datum = config.get("datum")
    if not isinstance(datum, str) or not datum.strip():
        errors.append("shared datum description is required")

    raw_components = config.get("components")
    components: dict[str, tuple[float, float]] = {}
    if not isinstance(raw_components, list) or not raw_components:
        errors.append("components must be a nonempty list")
    else:
        for entry in raw_components:
            if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"].strip():
                errors.append("every component requires a nonempty id")
                continue
            cid = entry["id"]
            if cid in components:
                errors.append(f"duplicate component id: {cid}")
                continue
            interval = _interval(entry)
            if interval is None:
                errors.append(f"invalid interval: {cid}")
                continue
            components[cid] = interval

    containment_results = []
    for rule in config.get("containment_rules", []):
        child = rule.get("child") if isinstance(rule, dict) else None
        container = rule.get("container") if isinstance(rule, dict) else None
        margin = rule.get("minimum_edge_margin_mm", 0.0) if isinstance(rule, dict) else None
        if child not in components or container not in components:
            errors.append(f"containment rule references unknown component: {child}/{container}")
            continue
        if not _finite(margin) or float(margin) < 0:
            errors.append(f"invalid containment margin: {child}/{container}")
            continue
        margin = float(margin)
        c = components[child]
        box = components[container]
        left_margin = c[0] - box[0]
        right_margin = box[1] - c[1]
        passed = left_margin >= margin and right_margin >= margin
        containment_results.append(
            {
                "child": child,
                "container": container,
                "minimum_edge_margin_mm": margin,
                "left_margin_mm": left_margin,
                "right_margin_mm": right_margin,
                "passed": passed,
            }
        )

    separation_results = []
    for rule in config.get("separation_rules", []):
        a_id = rule.get("a") if isinstance(rule, dict) else None
        b_id = rule.get("b") if isinstance(rule, dict) else None
        minimum = rule.get("minimum_gap_mm") if isinstance(rule, dict) else None
        if a_id not in components or b_id not in components:
            errors.append(f"separation rule references unknown component: {a_id}/{b_id}")
            continue
        if not _finite(minimum) or float(minimum) < 0:
            errors.append(f"invalid minimum gap: {a_id}/{b_id}")
            continue
        gap = interval_gap(components[a_id], components[b_id])
        minimum = float(minimum)
        separation_results.append(
            {
                "a": a_id,
                "b": b_id,
                "minimum_gap_mm": minimum,
                "actual_gap_mm": gap,
                "overlap_depth_mm": max(0.0, -gap),
                "passed": gap >= minimum,
            }
        )

    rules_complete = bool(config.get("containment_rules") or config.get("separation_rules"))
    if not rules_complete:
        errors.append("at least one containment or separation rule is required")

    rule_pass = all(r["passed"] for r in containment_results + separation_results)
    return {
        "schema_version": 1,
        "scope": "brake_drive_axial_stack_analysis_result",
        "valid": not errors,
        "errors": errors,
        "analysis_passed": not errors and rule_pass,
        "physical_authority": False,
        "datum": datum,
        "components_mm": {
            cid: {"start_mm": interval[0], "end_mm": interval[1]}
            for cid, interval in sorted(components.items())
        },
        "containment_results": containment_results,
        "separation_results": separation_results,
        "limitations": [
            "1-D axial analysis only",
            "does not model steering/lean swept volumes",
            "does not qualify brake-arm structural loading",
            "does not qualify drivetrain retention or torque capacity",
            "does not replace Issue #19 physical authority",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    report = analyze(json.loads(args.config.read_text(encoding="utf-8")))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
