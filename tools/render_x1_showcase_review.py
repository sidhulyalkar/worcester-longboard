#!/usr/bin/env python3
"""Render a deterministic human-readable X1 design review from the runtime manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "showcase" / "x1_runtime_manifest.json"
DEFAULT_OUT = ROOT / "showcase" / "generated" / "design_review.md"


def _yes_no(value: Any) -> str:
    return "yes" if value is True else "no"


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(manifest: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Worcester X1 digital-twin design review",
        "",
        "> Visualization and design-review output only. This document creates no procurement, fabrication, ride, or powered-operation authority.",
        "",
        "- Configuration: " + _cell(manifest.get("configuration")),
        "- Physical authority: **" + _yes_no(manifest.get("physical_authority")) + "**",
        "- Procurement authority: **" + _yes_no(manifest.get("procurement_authority")) + "**",
        "- Fabrication authority: **" + _yes_no(manifest.get("fabrication_authority")) + "**",
        "- Powered operation authorized: **" + _yes_no(manifest.get("powered_operation_authorized")) + "**",
        "",
        "## Component maturity",
        "",
        "| Component | Visual state | Physical gate | Gate passed? |",
        "| --- | --- | --- | --- |",
    ]

    for component in manifest.get("components", []):
        gate = component.get("authority_gate") or "concept-only"
        lines.append(
            "| {} | {} | {} | {} |".format(
                _cell(component.get("label")),
                _cell(component.get("evidence_state")),
                _cell(gate),
                _yes_no(component.get("gate_qualified")),
            )
        )

    studies = manifest.get("design_studies", {})
    deck_selection = manifest.get("deck_comparison_selection")
    lines += [
        "",
        "## Deck-envelope study",
        "",
        "| Candidate | Length (mm) | Max width (mm) | State | Physical pick? |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    selected_authority_id = (
        deck_selection.get("selected_candidate_id")
        if isinstance(deck_selection, dict)
        else None
    )
    for deck in studies.get("deck_candidates", []):
        physically_selected = (
            selected_authority_id is not None
            and deck.get("authority_candidate_id") == selected_authority_id
        )
        lines.append(
            "| {} | {} | {} | {} | {} |".format(
                _cell(deck.get("label")),
                _cell(deck.get("length_mm")),
                _cell(deck.get("width_mm")),
                _cell(deck.get("evidence_state")),
                "yes" if physically_selected else "no",
            )
        )
    if isinstance(deck_selection, dict):
        lines += [
            "",
            "A fingerprint-valid full-scale deck comparison selected "
            + _cell(deck_selection.get("selected_candidate_id"))
            + ". This observation does not qualify the chassis or unlock procurement.",
        ]

    lines += [
        "",
        "## Brake / drive topology references",
        "",
        "| Branch | Truck width (mm) | Wheel-center lateral (mm) | Brake ref | Drive ref |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for topology in studies.get("topology_branches", []):
        lines.append(
            "| {} | {} | {} | {} | {} |".format(
                _cell(topology.get("label")),
                _cell(topology.get("truck_total_width_mm")),
                _cell(topology.get("wheel_center_lateral_mm")),
                _cell(topology.get("brake_reference_compatible")),
                _cell(topology.get("drive_reference_compatible")),
            )
        )

    lab = studies.get("configuration_lab")
    if isinstance(lab, dict):
        lines += [
            "",
            "## Configuration-lab presets",
            "",
            "> Non-authoritative visualization states only. No preset selects a winner or changes build authority.",
            "",
            "| Preset | Deck | Topology | Brake | Drive | Pack | SnowDeck | Armor | Dock |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        decks_by_id = {
            row.get("id"): row.get("label")
            for row in studies.get("deck_candidates", [])
            if isinstance(row, dict)
        }
        topology_by_id = {
            row.get("id"): row.get("short_label") or row.get("label")
            for row in studies.get("topology_branches", [])
            if isinstance(row, dict)
        }
        for preset in lab.get("presets", []):
            layers = preset.get("layers", {})
            lines.append(
                "| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                    _cell(preset.get("label")),
                    _cell(decks_by_id.get(preset.get("deck_candidate_id"), preset.get("deck_candidate_id"))),
                    _cell(topology_by_id.get(preset.get("topology_id"), preset.get("topology_id"))),
                    _yes_no(layers.get("brake")),
                    _yes_no(layers.get("drive")),
                    _yes_no(layers.get("pack")),
                    _yes_no(layers.get("snowdeck")),
                    _yes_no(layers.get("armor")),
                    _yes_no(layers.get("dock")),
                )
            )
        lines += [
            "",
            "A/B comparison is descriptive only. It may expose geometry or compatibility differences, "
            "but it does not infer ride quality, strength, stopping performance, range, or safety.",
        ]

    armor = studies.get("trail_armor")
    if isinstance(armor, dict):
        lines += [
            "",
            "## Sacrificial trail-armor study",
            "",
            "- State: **" + _cell(armor.get("evidence_state")) + "**",
            "- Source: " + _cell(armor.get("source")),
            "- Note: " + _cell(armor.get("note")),
        ]
        for goal in armor.get("goals", []):
            lines.append("- " + _cell(goal))

    signature = manifest.get("snowdeck_bench_signature")
    if isinstance(signature, dict):
        lines += [
            "",
            "## SnowDeck bench response",
            "",
            "- Condition: " + _cell(signature.get("condition_id")),
            "- Trials: " + _cell(signature.get("trial_count")),
            "- Synthetic fixture: **" + _yes_no(signature.get("synthetic_fixture")) + "**",
            "- Physical-evidence eligible: **" + _yes_no(signature.get("physical_evidence_eligible")) + "**",
            "- Eligible for further bench comparison: **"
            + _yes_no(signature.get("eligible_for_further_bench_comparison"))
            + "**",
        ]
        rejects = signature.get("mechanical_rejects", [])
        lines.append(
            "- Mechanical rejects: "
            + ("none recorded" if not rejects else "; ".join(_cell(x) for x in rejects))
        )

        neutral = signature.get("neutral", {})
        transfer = signature.get("heel_to_toe_forefoot_transfer", {})
        lines += [
            "",
            "| Metric | Mean | SD |",
            "| --- | ---: | ---: |",
            "| Neutral left-load fraction | {} | {} |".format(
                _cell((neutral.get("left_load_fraction") or {}).get("mean")),
                _cell((neutral.get("left_load_fraction") or {}).get("sd")),
            ),
            "| Left heel-to-toe transfer | {} | {} |".format(
                _cell((transfer.get("left") or {}).get("mean")),
                _cell((transfer.get("left") or {}).get("sd")),
            ),
            "| Right heel-to-toe transfer | {} | {} |".format(
                _cell((transfer.get("right") or {}).get("mean")),
                _cell((transfer.get("right") or {}).get("sd")),
            ),
            "| Neutral total load | {} | {} |".format(
                _cell((neutral.get("total_load") or {}).get("mean")),
                _cell((neutral.get("total_load") or {}).get("sd")),
            ),
        ]

        comparison = manifest.get("snowdeck_bench_comparison")
        if isinstance(comparison, dict):
            lines += [
                "",
                "### Signed variant-minus-baseline deltas",
                "",
                "No direction is automatically preferred. No winner is selected.",
                "",
            ]
            for key, value in comparison.get("signed_variant_minus_baseline", {}).items():
                lines.append("- {}: {}".format(_cell(key), _cell(value)))

    lines += [
        "",
        "## Highest open mechanical risks",
        "",
        "| ID | Subsystem | Failure mode | Priority | Must close before |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for risk in manifest.get("risk_summary", []):
        lines.append(
            "| {} | {} | {} | {} | {} |".format(
                _cell(risk.get("id")),
                _cell(str(risk.get("subsystem", "")).replace("_", " ")),
                _cell(risk.get("failure_mode")),
                _cell(risk.get("priority_score")),
                _cell(risk.get("must_close_before")),
            )
        )

    gate_names = (
        "fit_pilot_qualified",
        "fit_platform_repeatability_qualified",
        "rev_c_chassis_release_qualified",
        "brake_interface_qualified",
        "rolling_chassis_physical_qualified",
        "brake_drive_topology_qualified",
        "rider_fit_qualified",
        "dummy_pack_mount_qualified",
        "power_architecture_frozen",
    )
    gates = manifest.get("gates", {})
    lines += [
        "",
        "## Physical progression gates",
        "",
        "| Gate | Satisfied? | Current blockers |",
        "| --- | --- | --- |",
    ]
    for name in gate_names:
        gate = gates.get(name)
        if not isinstance(gate, dict):
            continue
        blockers = "; ".join(_cell(x) for x in gate.get("blockers", [])) or "none"
        lines.append(
            "| {} | {} | {} |".format(
                _cell(name),
                _yes_no(gate.get("satisfied")),
                blockers,
            )
        )

    lines += [
        "",
        "## Interpretation boundary",
        "",
        "Reference, assumed, and blocked geometry is useful for review but is not received-unit evidence. "
        "Synthetic SnowDeck data is a visualization fixture only. The next authoritative information still "
        "comes from the physical Issue #25 deck experiment and the provenance-locked Fit Rig sequence.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("physical_authority") is not False:
        raise ValueError("design review requires physical_authority=false")
    if manifest.get("fabrication_authority") is not False:
        raise ValueError("design review requires fabrication_authority=false")
    if manifest.get("powered_operation_authorized") is not False:
        raise ValueError("design review requires powered_operation_authorized=false")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(manifest), encoding="utf-8")
    print("Wrote " + str(args.out))
    print("design-review only; no physical or powered authority")


if __name__ == "__main__":
    main()
