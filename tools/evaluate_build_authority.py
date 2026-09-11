#!/usr/bin/env python3
"""Compose Worcester X1 build gates with procurement policy and local evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _value_at(data: dict, dotted_path: str) -> Any:
    value: Any = data
    for key in dotted_path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _predicate_matches(data: dict, predicate: dict) -> bool:
    value = _value_at(data, predicate["path"])
    if "equals" in predicate:
        return value == predicate["equals"]
    if predicate.get("type") == "nonempty_string":
        return isinstance(value, str) and bool(value.strip())
    if predicate.get("type") == "valid_authority_fingerprint":
        if not isinstance(value, str) or not value:
            return False
        unsigned = dict(data)
        unsigned.pop("authority_fingerprint_sha256", None)
        try:
            payload = json.dumps(
                unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError):
            return False
        expected = hashlib.sha256(payload).hexdigest()
        return value == expected
    raise ValueError(f"unsupported evidence predicate: {predicate}")


def _evidence_matches(data: dict, predicates: list[dict]) -> bool:
    return bool(predicates) and all(_predicate_matches(data, p) for p in predicates)


def _validate_plan(plan: dict) -> None:
    if plan.get("schema_version") != 1:
        raise ValueError("build authority schema_version must be 1")

    gates = plan.get("gates")
    capabilities = plan.get("capabilities")
    if not isinstance(gates, dict) or not isinstance(capabilities, dict):
        raise ValueError("plan requires gates and capabilities objects")

    for name, gate in gates.items():
        for dep in gate.get("requires", []):
            if dep not in gates:
                raise ValueError(f"gate {name} requires unknown gate {dep}")
        if not isinstance(gate.get("evidence"), list) or not gate["evidence"]:
            raise ValueError(f"gate {name} requires a nonempty evidence contract")

    for name, cap in capabilities.items():
        for dep in cap.get("requires", []):
            if dep not in gates:
                raise ValueError(f"capability {name} requires unknown gate {dep}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise ValueError(f"gate dependency cycle at {name}")
        visiting.add(name)
        for dep in gates[name].get("requires", []):
            visit(dep)
        visiting.remove(name)
        visited.add(name)

    for name in gates:
        visit(name)


def _stage_authority(procurement: dict) -> dict[str, bool]:
    rules = procurement.get("rules", {})
    items = procurement.get("items", [])
    measure_items = [x for x in items if x.get("stage") == "MEASURE_FIRST"]
    measure_ok = True
    if rules.get("measure_first_requires_issue") is True:
        measure_ok = bool(measure_items) and all(bool(x.get("required_for")) for x in measure_items)
    return {
        "BUY_NOW": True,
        "MEASURE_FIRST": measure_ok,
        "POWER_GATED": rules.get("power_gated_authorized") is True,
    }


def evaluate(plan: dict, procurement: dict, evidence_docs: list[dict]) -> dict:
    _validate_plan(plan)
    stage_allowed = _stage_authority(procurement)
    gates = plan["gates"]

    direct_match: dict[str, bool] = {}
    for name, gate in gates.items():
        direct_match[name] = any(
            _evidence_matches(doc, gate["evidence"]) for doc in evidence_docs
        )

    gate_state: dict[str, dict] = {}

    def resolve(name: str) -> bool:
        if name in gate_state:
            return gate_state[name]["satisfied"]
        gate = gates[name]
        missing_dependencies = [dep for dep in gate.get("requires", []) if not resolve(dep)]
        evidence_matched = direct_match[name]
        satisfied = evidence_matched and not missing_dependencies
        blockers: list[str] = []
        if not evidence_matched:
            blockers.append("matching physical authority evidence not supplied")
        blockers.extend(f"upstream gate blocked: {dep}" for dep in missing_dependencies)
        gate_state[name] = {
            "satisfied": satisfied,
            "evidence_matched": evidence_matched,
            "blockers": blockers,
            "issue": gate.get("issue"),
        }
        return satisfied

    for name in gates:
        resolve(name)

    capability_state: dict[str, dict] = {}
    for name, cap in plan["capabilities"].items():
        blockers = [
            f"required gate blocked: {dep}"
            for dep in cap.get("requires", [])
            if not gate_state[dep]["satisfied"]
        ]
        stage = cap.get("procurement_stage")
        if stage is not None and not stage_allowed.get(stage, False):
            blockers.append(f"procurement stage blocked: {stage}")
        if cap.get("hard_blocked") is True:
            blockers.append(cap.get("block_reason", "hard blocked by current authority"))
        capability_state[name] = {
            "allowed": not blockers,
            "blockers": blockers,
            "procurement_stage": stage,
        }

    return {
        "schema_version": 1,
        "project": plan.get("project"),
        "public_baseline": plan.get("public_baseline"),
        "evidence_documents_supplied": len(evidence_docs),
        "procurement_stage_authorized": stage_allowed,
        "gates": gate_state,
        "capabilities": capability_state,
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    p.add_argument("procurement", type=Path)
    p.add_argument("--evidence", action="append", default=[], type=Path)
    p.add_argument("--out", type=Path)
    return p


def main() -> None:
    args = _parser().parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    procurement = json.loads(args.procurement.read_text(encoding="utf-8"))
    evidence = [json.loads(path.read_text(encoding="utf-8")) for path in args.evidence]
    report = evaluate(plan, procurement, evidence)
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
