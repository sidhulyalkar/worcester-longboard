#!/usr/bin/env python3
"""Build a public, fail-closed runtime manifest for the X1 design viewer."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from evaluate_build_authority import evaluate as evaluate_build_authority

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


def validate_seed(seed: dict[str, Any]) -> None:
    if seed.get("powered_operation_authorized") is not False:
        raise ValueError("Seed manifest must explicitly keep powered operation unauthorized")
    if seed.get("physical_authority") is not False:
        raise ValueError("Seed manifest must explicitly keep physical authority false")

    ids: set[str] = set()
    for component in seed.get("components", []):
        cid = component.get("id")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError("Every component requires a nonempty id")
        if cid in ids:
            raise ValueError(f"Duplicate component id: {cid}")
        ids.add(cid)
        state = component.get("evidence_state")
        if state not in ALLOWED_STATES:
            raise ValueError(f"{cid}: unknown evidence_state {state!r}")


def sanitize_evidence_documents(paths: list[Path]) -> list[dict[str, Any]]:
    docs = []
    for path in paths:
        doc = load_json(path)
        if doc.get("powered_operation_authorized") is True:
            raise ValueError(
                f"{path}: pre-hardware showcase refuses powered-operation authority"
            )
        docs.append(doc)
    return docs


def promote_components(
    seed: dict[str, Any], gate_state: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    components = []
    for raw in seed.get("components", []):
        component = dict(raw)
        gate_name = component.get("authority_gate")
        if gate_name:
            if gate_name not in gate_state:
                raise ValueError(
                    f"{component.get('id')}: unknown authority gate {gate_name!r}"
                )
            gate = gate_state[gate_name]
            component["gate_qualified"] = bool(gate["satisfied"])
            component["gate_blockers"] = list(gate.get("blockers", []))
            if gate["satisfied"]:
                component["evidence_state"] = "QUALIFIED"
        else:
            component["gate_qualified"] = False
            component["gate_blockers"] = []
        components.append(component)
    return components


def build(
    seed_path: Path,
    authority_path: Path,
    procurement_path: Path,
    evidence_paths: list[Path],
) -> dict[str, Any]:
    seed = load_json(seed_path)
    authority = load_json(authority_path)
    procurement = load_json(procurement_path)
    validate_seed(seed)

    evidence_docs = sanitize_evidence_documents(evidence_paths)
    authority_report = evaluate_build_authority(authority, procurement, evidence_docs)
    gate_state = authority_report["gates"]
    components = promote_components(seed, gate_state)

    return {
        "schema_version": 1,
        "project": seed.get("project", "Worcester X1"),
        "configuration": seed.get("configuration"),
        "generated_from": {
            "seed": str(seed_path.relative_to(ROOT)),
            "seed_sha256": sha256_file(seed_path),
            "build_authority": str(authority_path.relative_to(ROOT)),
            "build_authority_sha256": sha256_file(authority_path),
            "procurement_manifest": str(procurement_path.relative_to(ROOT)),
            "procurement_manifest_sha256": sha256_file(procurement_path),
            "evidence_documents_supplied": len(evidence_docs),
        },
        "physical_authority": False,
        "procurement_authority": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "components": components,
        "gates": gate_state,
        "viewer_notice": (
            "Visualization only. Gate state is recomputed with the repository build-authority "
            "evaluator. Missing or invalid evidence fails closed."
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
    p.add_argument(
        "--procurement",
        type=Path,
        default=ROOT / "hardware" / "procurement_manifest.json",
    )
    p.add_argument(
        "--evidence",
        action="append",
        default=[],
        type=Path,
        help="Fingerprint-valid authority JSON. May be supplied multiple times.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "showcase" / "x1_runtime_manifest.json",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    runtime = build(
        args.seed,
        args.build_authority,
        args.procurement,
        args.evidence,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    print("physical_authority=false powered_operation_authorized=false")


if __name__ == "__main__":
    main()
