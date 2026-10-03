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


def sanitize_snowdeck_signature(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("scope") != "x1_snowdeck_bench_signature":
        raise ValueError("SnowDeck signature has wrong scope")
    for key in (
        "physical_authority",
        "fabrication_authority",
        "ride_authority",
        "powered_operation_authorized",
    ):
        if data.get(key) is not False:
            raise ValueError(f"SnowDeck signature must keep {key}=false")
    return {
        "condition_id": data.get("condition_id"),
        "synthetic_fixture": bool(data.get("synthetic_fixture")),
        "physical_evidence_eligible": bool(data.get("physical_evidence_eligible")),
        "trial_count": data.get("trial_count"),
        "neutral": data.get("neutral", {}),
        "heel_to_toe_forefoot_transfer": data.get(
            "heel_to_toe_forefoot_transfer", {}
        ),
        "deep_knee_delta_from_neutral": data.get(
            "deep_knee_delta_from_neutral", {}
        ),
        "mechanical_rejects": list(data.get("mechanical_rejects", [])),
        "eligible_for_further_bench_comparison": bool(
            data.get("eligible_for_further_bench_comparison")
        ),
        "source_force_log_sha256": data.get("source_force_log_sha256"),
        "source_session_sha256": data.get("source_session_sha256"),
    }


def sanitize_snowdeck_comparison(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("scope") != "x1_snowdeck_bench_signature_comparison":
        raise ValueError("SnowDeck comparison has wrong scope")
    for key in (
        "physical_authority",
        "fabrication_authority",
        "ride_authority",
        "powered_operation_authorized",
    ):
        if data.get(key) is not False:
            raise ValueError(f"SnowDeck comparison must keep {key}=false")
    if data.get("winner_selected") is not False:
        raise ValueError("SnowDeck comparison must not select a winner")
    return {
        "baseline": {
            "condition_id": (data.get("baseline") or {}).get("condition_id"),
            "mechanical_rejects": list(
                (data.get("baseline") or {}).get("mechanical_rejects", [])
            ),
        },
        "variant": {
            "condition_id": (data.get("variant") or {}).get("condition_id"),
            "mechanical_rejects": list(
                (data.get("variant") or {}).get("mechanical_rejects", [])
            ),
        },
        "signed_variant_minus_baseline": dict(
            data.get("signed_variant_minus_baseline", {})
        ),
        "variant_eligible_for_further_bench_comparison": bool(
            data.get("variant_eligible_for_further_bench_comparison")
        ),
        "synthetic_fixture": bool(data.get("synthetic_fixture")),
        "physical_evidence_eligible": bool(data.get("physical_evidence_eligible")),
        "winner_selected": False,
    }


def summarize_risks(risk_register: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    risks = risk_register.get("risks", [])
    ranked = sorted(
        (r for r in risks if isinstance(r, dict)),
        key=lambda r: (-int(r.get("priority_score", 0)), str(r.get("id", ""))),
    )
    fields = (
        "id",
        "subsystem",
        "failure_mode",
        "effect",
        "priority_score",
        "status",
        "must_close_before",
    )
    return [
        {field: risk.get(field) for field in fields}
        for risk in ranked[:limit]
    ]


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

        context_states = []
        for context_gate in component.get("context_gates", []):
            if context_gate not in gate_state:
                raise ValueError(
                    f"{component.get('id')}: unknown context gate {context_gate!r}"
                )
            context = gate_state[context_gate]
            context_states.append(
                {
                    "gate": context_gate,
                    "satisfied": bool(context["satisfied"]),
                    "blockers": list(context.get("blockers", [])),
                }
            )
        component["context_gate_states"] = context_states
        components.append(component)
    return components


def build(
    seed_path: Path,
    authority_path: Path,
    procurement_path: Path,
    evidence_paths: list[Path],
    risk_path: Path | None = None,
    snowdeck_signature_path: Path | None = None,
    snowdeck_comparison_path: Path | None = None,
) -> dict[str, Any]:
    seed = load_json(seed_path)
    authority = load_json(authority_path)
    procurement = load_json(procurement_path)
    validate_seed(seed)

    evidence_docs = sanitize_evidence_documents(evidence_paths)
    authority_report = evaluate_build_authority(authority, procurement, evidence_docs)
    gate_state = authority_report["gates"]
    components = promote_components(seed, gate_state)
    risk_register = load_json(risk_path) if risk_path is not None else {}
    risk_summary = summarize_risks(risk_register)
    snowdeck_signature = (
        sanitize_snowdeck_signature(load_json(snowdeck_signature_path))
        if snowdeck_signature_path is not None
        else None
    )
    snowdeck_comparison = (
        sanitize_snowdeck_comparison(load_json(snowdeck_comparison_path))
        if snowdeck_comparison_path is not None
        else None
    )

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
            "mechanical_risk_register": (
                str(risk_path.relative_to(ROOT)) if risk_path is not None else None
            ),
            "mechanical_risk_register_sha256": (
                sha256_file(risk_path) if risk_path is not None else None
            ),
            "snowdeck_signature_sha256": (
                sha256_file(snowdeck_signature_path)
                if snowdeck_signature_path is not None else None
            ),
            "snowdeck_comparison_sha256": (
                sha256_file(snowdeck_comparison_path)
                if snowdeck_comparison_path is not None else None
            ),
        },
        "physical_authority": False,
        "procurement_authority": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "components": components,
        "design_studies": seed.get("design_studies", {}),
        "risk_summary": risk_summary,
        "snowdeck_bench_signature": snowdeck_signature,
        "snowdeck_bench_comparison": snowdeck_comparison,
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
        "--risk-register",
        type=Path,
        default=ROOT / "hardware" / "mechanical_risk_register.json",
    )
    p.add_argument(
        "--evidence",
        action="append",
        default=[],
        type=Path,
        help="Fingerprint-valid authority JSON. May be supplied multiple times.",
    )
    p.add_argument(
        "--snowdeck-signature",
        type=Path,
        help="Optional local x1_snowdeck_bench_signature aggregate JSON.",
    )
    p.add_argument(
        "--snowdeck-comparison",
        type=Path,
        help="Optional local non-ranking SnowDeck comparison JSON.",
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
        args.risk_register,
        args.snowdeck_signature,
        args.snowdeck_comparison,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    print("physical_authority=false powered_operation_authorized=false")


if __name__ == "__main__":
    main()
