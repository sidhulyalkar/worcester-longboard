"""Read-only, non-authoritative evidence views for Board Builder v1.1.

This module describes recorded reference rules and measurement gaps. It does
not establish mechanical compatibility, qualification, stock or purchase authority.
"""
from __future__ import annotations

from typing import Any

INTERFACE_CHECKS = {
    "deck:truck": "Confirm exact mounting pattern, deck tip angle, truck orientation and structural load path.",
    "truck:wheel": "Confirm axle diameter, bearing/spacer stack, wheel offset, retention and full steering clearance.",
    "brake:truck": "Confirm the exact brake hanger mount, fasteners, actuator travel and steering-sweep clearance.",
    "brake:wheel": "Confirm rotor mounting, hub interface, braking alignment and full-rotation clearance.",
    "brake:hub": "Confirm hub rotor interface, bolt pattern, retention and brake alignment.",
    "drive:truck": "Confirm drive-mount geometry, axle stack, retention, steering sweep and brake/drive coexistence.",
    "drive:wheel": "Confirm wheel gear or pulley engagement, wheel offset, guard clearance and retention.",
    "drive:hub": "Confirm hub adapter/gear interface, fasteners, offset and retention.",
    "axle:drive": "Confirm exact axle dimensions, drive attachment and retention geometry.",
    "axle:brake": "Confirm rotor alignment, brake clearance and axle retention.",
}
EVIDENCE_REQUIRED = (
    "Obtain exact-revision dimensioned manufacturer evidence or recorded physical "
    "measurements; resolve clearance/retention and pass the separate qualification gate."
)
OPEN_STATES = {"UNKNOWN", "MEASURE_FIRST"}
MAINTENANCE_STATES = {"REFRESH_DUE", "STALE", "MISSING_PROVENANCE", "HEALTH_UNAVAILABLE"}
AUTHORITY = {
    "procurement_authorized": False,
    "fabrication_authorized": False,
    "charging_authorized": False,
    "powered_operation_authorized": False,
    "generic_builder_may_promote_x1_authority": False,
}


def build_evidence_explorer(
    candidate: dict[str, Any],
    catalog: dict[str, Any],
    health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    components = {row["id"]: row for row in catalog.get("components", [])}
    health_rows = {row["component_id"]: row for row in (health or {}).get("component_health", [])}
    physical_ids = (candidate.get("composition") or {}).get("physical_interface_ids")
    if physical_ids is None:
        physical_ids = candidate.get("compatibility_interface_ids")
    physical_basis = "EXPANDED_COMPONENT_GRAPH" if physical_ids is not None else "REFERENCE_BOM_ONLY"
    selected_ids = sorted(set(
        [row["component_id"] for row in candidate.get("bom", [])]
        + list(physical_ids or [])
    ))

    def source_row(cid: str) -> dict[str, Any]:
        item = components.get(cid) or {}
        source = item.get("source") or {}
        info = health_rows.get(cid)
        return {
            "component_id": cid,
            "label": item.get("label") or cid,
            "category": item.get("category"),
            "source_url": source.get("url"),
            "snapshot_id": source.get("snapshot_id"),
            "verified_as_of": info.get("verified_as_of") if info else None,
            "health_status": info.get("status") if info else "HEALTH_UNAVAILABLE",
            "source_kind": source.get("kind"),
        }

    source_evidence = [source_row(cid) for cid in selected_ids]
    source_index = {row["component_id"]: row for row in source_evidence}
    findings = []
    worklist = []
    for f in sorted(candidate.get("compatibility_findings", []), key=lambda row: row["id"]):
        a, b = f.get("a"), f.get("b")
        category_pair = ":".join(sorted([
            str((components.get(a) or {}).get("category") or "unknown"),
            str((components.get(b) or {}).get("category") or "unknown"),
        ]))
        fallback = f.get("source") == "category_default" or str(f["id"]).startswith("default:")
        finding = {
            "id": f["id"],
            "a": a,
            "b": b,
            "a_label": (components.get(a) or {}).get("label") or a,
            "b_label": (components.get(b) or {}).get("label") or b,
            "category_pair": category_pair,
            "state": f["state"],
            "evidence_kind": "CONSERVATIVE_CATEGORY_FALLBACK" if fallback else "EXPLICIT_CATALOG_RULE",
            "reason": f["reason"],
            "sources": [
                source_index.get(cid) or source_row(cid)
                for cid in sorted(set([a, b]))
            ],
        }
        findings.append(finding)
        if f["state"] in OPEN_STATES:
            worklist.append({
                "id": f["id"],
                "component_ids": sorted(set([a, b])),
                "state": f["state"],
                "category_pair": category_pair,
                "question": INTERFACE_CHECKS.get(
                    category_pair,
                    "Establish the exact selected-revision mechanical interface and its coexistence constraints.",
                ),
                "evidence_required": EVIDENCE_REQUIRED,
                "reason": f["reason"],
            })

    issues = sorted(
        (row for row in source_evidence if row["health_status"] in MAINTENANCE_STATES),
        key=lambda row: row["component_id"],
    )
    unpriced = sorted(set((candidate.get("cost") or {}).get("unpriced_component_ids") or []))
    linked_reasons = {f["reason"] for f in findings}
    other_unknowns = sorted(set(candidate.get("unknowns") or []) - linked_reasons)
    counts = {
        "explicit_rules": sum(f["evidence_kind"] == "EXPLICIT_CATALOG_RULE" for f in findings),
        "conservative_fallbacks": sum(f["evidence_kind"] == "CONSERVATIVE_CATEGORY_FALLBACK" for f in findings),
        "open_interfaces": len(worklist),
        "incompatible_interfaces": sum(f["state"] == "INCOMPATIBLE" for f in findings),
        "source_refresh_or_integrity_issues": len(issues),
        "unpriced_items": len(unpriced),
        "price_complete": not bool(unpriced),
        "physical_basis": physical_basis,
    }
    return {
        "schema_version": 1,
        "scope": "non_authoritative_catalog_evidence_explorer",
        "candidate_id": candidate.get("id") or "custom_study",
        "origin": candidate.get("origin") or "SWAP_STUDY",
        "readiness": candidate.get("readiness"),
        "checkout_state": candidate.get("checkout_state"),
        "summary": counts,
        "interfaces": findings,
        "measurement_worklist": worklist,
        "source_evidence": source_evidence,
        "source_maintenance": issues,
        "other_uncertainties": other_unknowns,
        "hard_blockers": sorted(set(candidate.get("blockers") or [])),
        "unpriced_component_ids": unpriced,
        "price_basis": "KNOWN_USD_SUBTOTAL_ONLY",
        "score_basis": "PLANNING_PREFERENCE_NOT_SAFETY",
        "qualification_note": (
            "Catalog rules and source freshness are not physical qualification. "
            "Measurement worklists cannot release procurement, fabrication, charging or powered operation."
        ),
        "authority": dict(AUTHORITY),
    }
