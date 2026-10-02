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
        requires = gate.get("requires", [])
        for dep in requires:
            if dep not in gates:
                raise ValueError(f"gate {name} requires unknown gate {dep}")
        if not isinstance(gate.get("evidence"), list) or not gate["evidence"]:
            raise ValueError(f"gate {name} requires a nonempty evidence contract")
        links = gate.get("evidence_links", [])
        if not isinstance(links, list):
            raise ValueError(f"gate {name} evidence_links must be a list")
        for link in links:
            if not isinstance(link, dict):
                raise ValueError(f"gate {name} evidence link must be an object")
            dep_gate = link.get("gate")
            if dep_gate not in gates:
                raise ValueError(
                    f"gate {name} evidence link references unknown gate {dep_gate}"
                )
            if dep_gate not in requires:
                raise ValueError(
                    f"gate {name} evidence link gate {dep_gate} must also be a dependency"
                )
            if not isinstance(link.get("path"), str) or not link["path"]:
                raise ValueError(f"gate {name} evidence link requires path")
            target_path = link.get("target_path", "authority_fingerprint_sha256")
            if not isinstance(target_path, str) or not target_path:
                raise ValueError(f"gate {name} evidence link requires target_path")

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


def _procurement_authority(
    procurement: dict,
    gate_state: dict[str, dict] | None = None,
    gate_evidence: dict[str, dict] | None = None,
) -> tuple[dict[str, bool], dict[str, dict]]:
    """Evaluate orderability per item, including evidence-backed release gates."""
    rules = procurement.get("rules", {})
    items = procurement.get("items", [])
    instantiated_item_id = rules.get("instantiated_chassis_item_id")
    gate_state = gate_state or {}
    gate_evidence = gate_evidence or {}
    item_state: dict[str, dict] = {}

    for index, item in enumerate(items):
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            item_id = f"<invalid-item-{index}>"

        stage = item.get("stage")
        blockers: list[str] = []
        if stage not in {"BUY_NOW", "MEASURE_FIRST", "POWER_GATED"}:
            blockers.append(f"unknown procurement stage: {stage}")

        if stage == "MEASURE_FIRST":
            if rules.get("measure_first_requires_issue") is True and not item.get("required_for"):
                blockers.append("MEASURE_FIRST item lacks required_for issue authority")
            required_gate = item.get("requires_gate")
            if required_gate:
                if required_gate not in gate_state:
                    blockers.append(f"unknown procurement release gate: {required_gate}")
                elif not gate_state[required_gate]["satisfied"]:
                    blockers.append(f"required release gate blocked: {required_gate}")
            raw_selections = item.get("requires_gate_selections")
            if raw_selections is None and item.get("requires_gate_selection") is not None:
                raw_selections = [item["requires_gate_selection"]]
            for selection in raw_selections or []:
                selection_gate = selection.get("gate") or required_gate
                if not isinstance(selection_gate, str) or not selection_gate:
                    blockers.append("requires_gate_selection lacks gate")
                    continue
                if selection_gate not in gate_state:
                    blockers.append(
                        f"unknown procurement selection gate: {selection_gate}"
                    )
                    continue
                if not gate_state[selection_gate]["satisfied"]:
                    blockers.append(
                        f"selection gate blocked: {selection_gate}"
                    )
                    continue
                authority_doc = gate_evidence.get(selection_gate)
                expected = selection.get("equals")
                actual = (
                    _value_at(authority_doc, selection.get("path", ""))
                    if authority_doc is not None
                    else None
                )
                if actual != expected:
                    blockers.append(
                        "release selection mismatch: "
                        f"{selection.get('path')}={actual!r}, expected {expected!r}"
                    )
            if item.get("defer_until"):
                blockers.append(f"deferred until: {item['defer_until']}")
            if instantiated_item_id and item.get("alternative_to") == instantiated_item_id:
                blockers.append(
                    f"fallback blocked while instantiated chassis path is active: {instantiated_item_id}"
                )

        if stage == "POWER_GATED" and rules.get("power_gated_authorized") is not True:
            blockers.append("POWER_GATED is not authorized")

        item_state[item_id] = {
            "stage": stage,
            "orderable": not blockers,
            "blockers": blockers,
            "required_for": item.get("required_for"),
            "requires_gate": item.get("requires_gate"),
            "requires_gate_selections": item.get("requires_gate_selections")
            or (
                [item["requires_gate_selection"]]
                if item.get("requires_gate_selection") is not None
                else []
            ),
            "defer_until": item.get("defer_until"),
            "alternative_to": item.get("alternative_to"),
        }

    stage_allowed = {
        stage: any(
            state["stage"] == stage and state["orderable"]
            for state in item_state.values()
        )
        for stage in ("BUY_NOW", "MEASURE_FIRST", "POWER_GATED")
    }
    return stage_allowed, item_state


def evaluate(plan: dict, procurement: dict, evidence_docs: list[dict]) -> dict:
    _validate_plan(plan)
    gates = plan["gates"]

    direct_match: dict[str, bool] = {}
    gate_evidence: dict[str, dict] = {}
    for name, gate in gates.items():
        matched = next(
            (
                doc
                for doc in evidence_docs
                if _evidence_matches(doc, gate["evidence"])
            ),
            None,
        )
        direct_match[name] = matched is not None
        if matched is not None:
            gate_evidence[name] = matched

    gate_state: dict[str, dict] = {}

    def resolve(name: str) -> bool:
        if name in gate_state:
            return gate_state[name]["satisfied"]
        gate = gates[name]
        missing_dependencies = [dep for dep in gate.get("requires", []) if not resolve(dep)]
        evidence_matched = direct_match[name]
        blockers: list[str] = []
        if not evidence_matched:
            blockers.append("matching authority evidence not supplied")
        blockers.extend(f"upstream gate blocked: {dep}" for dep in missing_dependencies)

        evidence_link_blockers: list[str] = []
        matched_doc = gate_evidence.get(name)
        if matched_doc is not None:
            for link in gate.get("evidence_links", []):
                dep_gate = link["gate"]
                dep_doc = gate_evidence.get(dep_gate)
                if dep_doc is None:
                    evidence_link_blockers.append(
                        f"linked upstream evidence unavailable: {dep_gate}"
                    )
                    continue
                actual = _value_at(matched_doc, link["path"])
                target_path = link.get(
                    "target_path", "authority_fingerprint_sha256"
                )
                expected = _value_at(dep_doc, target_path)
                if actual != expected:
                    evidence_link_blockers.append(
                        "evidence link mismatch: "
                        f"{link['path']}={actual!r}, expected "
                        f"{dep_gate}.{target_path}={expected!r}"
                    )
        blockers.extend(evidence_link_blockers)
        satisfied = (
            evidence_matched
            and not missing_dependencies
            and not evidence_link_blockers
        )
        gate_state[name] = {
            "satisfied": satisfied,
            "evidence_matched": evidence_matched,
            "blockers": blockers,
            "issue": gate.get("issue"),
        }
        return satisfied

    for name in gates:
        resolve(name)

    stage_allowed, procurement_items = _procurement_authority(
        procurement, gate_state, gate_evidence
    )

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
        "procurement_items": procurement_items,
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
