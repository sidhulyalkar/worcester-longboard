#!/usr/bin/env python3
"""Build a public, fail-closed runtime manifest for the X1 design viewer."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATES = {"QUALIFIED", "REFERENCE", "ASSUMED", "BLOCKED", "NOT_PRESENT"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_authority(gate: dict[str, Any]) -> str | None:
    for rule in gate.get("evidence", []):
        if rule.get("path") == "authority" and isinstance(rule.get("equals"), str):
            return rule["equals"]
    return None


def validate_evidence_index(
    gates: dict[str, Any], evidence_index: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    unknown = sorted(set(evidence_index) - set(gates))
    if unknown:
        raise ValueError("Unknown gate(s) in evidence index: " + ", ".join(unknown))

    for gate_name, gate in gates.items():
        supplied = evidence_index.get(gate_name)
        status = {
            "gate": gate_name,
            "issue": gate.get("issue"),
            "requires": gate.get("requires", []),
            "evidence_supplied": supplied is not None,
            "qualified": False,
            "expected_authority": expected_authority(gate),
        }
        if supplied is not None:
            if not isinstance(supplied, dict):
                raise ValueError(f"{gate_name}: supplied evidence must be an object")
            if supplied.get("powered_operation_authorized") is True:
                raise ValueError(f"{gate_name}: showcase refuses powered-operation authority")
            exp = status["expected_authority"]
            got = supplied.get("authority")
            if exp is not None and got != exp:
                raise ValueError(f"{gate_name}: expected authority {exp!r}, got {got!r}")
            status["qualified"] = supplied.get("qualified") is True or any(
                rule.get("path") == "qualified_for_four_zone_duplication"
                and supplied.get("qualified_for_four_zone_duplication") is True
                for rule in gate.get("evidence", [])
            )
            if not status["qualified"]:
                # Some authorities use a nested readiness field rather than qualified=true.
                status["qualified"] = bool(supplied.get("showcase_gate_satisfied", False))
            fp = supplied.get("authority_fingerprint_sha256")
            if fp is not None:
                status["authority_fingerprint_sha256"] = fp
        statuses[gate_name] = status
    return statuses


def promote_components(
    seed: dict[str, Any], gate_status: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    components = []
    for raw in seed.get("components", []):
        component = dict(raw)
        state = component.get("evidence_state")
        if state not in ALLOWED_STATES:
            raise ValueError(f"{component.get('id')}: unknown evidence_state {state!r}")

        gate_name = component.get("authority_gate")
        if gate_name:
            if gate_name not in gate_status:
                raise ValueError(f"{component.get('id')}: unknown authority gate {gate_name!r}")
            gate = gate_status[gate_name]
            component["gate_qualified"] = bool(gate["qualified"])
            if gate["qualified"]:
                component["evidence_state"] = "QUALIFIED"
        else:
            component["gate_qualified"] = False

        components.append(component)
    return components


def build(seed_path: Path, authority_path: Path, evidence_path: Path | None) -> dict[str, Any]:
    seed = load_json(seed_path)
    authority = load_json(authority_path)
    if seed.get("powered_operation_authorized") is not False:
        raise ValueError("Seed manifest must explicitly keep powered operation unauthorized")

    evidence_index = load_json(evidence_path) if evidence_path else {}
    gates = authority.get("gates", {})
    gate_status = validate_evidence_index(gates, evidence_index)
    components = promote_components(seed, gate_status)

    return {
        "schema_version": 1,
        "project": seed.get("project", "Worcester X1"),
        "configuration": seed.get("configuration"),
        "generated_from": {
            "seed": str(seed_path.relative_to(ROOT)),
            "seed_sha256": sha256_file(seed_path),
            "build_authority": str(authority_path.relative_to(ROOT)),
            "build_authority_sha256": sha256_file(authority_path),
            "evidence_index_supplied": evidence_path is not None,
        },
        "physical_authority": False,
        "procurement_authority": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "components": components,
        "gates": gate_status,
        "viewer_notice": (
            "Visualization only. Missing evidence is fail-closed; manufacturer references "
            "and assumed envelopes are not received-unit measurements."
        ),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=Path, default=ROOT / "showcase" / "x1_rev_c.json")
    p.add_argument(
        "--build-authority",
        type=Path,
        default=ROOT / "hardware" / "build_authority.json",
    )
    p.add_argument("--evidence-index", type=Path)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "showcase" / "x1_runtime_manifest.json",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    runtime = build(args.seed, args.build_authority, args.evidence_index)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    print("physical_authority=false powered_operation_authorized=false")


if __name__ == "__main__":
    main()
