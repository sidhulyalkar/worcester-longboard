// Read-only, non-authoritative evidence views for Board Builder v1.1.
const CHECKS = {
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
};
const EVIDENCE_REQUIRED = "Obtain exact-revision dimensioned manufacturer evidence or recorded physical measurements; resolve clearance/retention and pass the separate qualification gate.";
const AUTHORITY = {
  procurement_authorized: false,
  fabrication_authorized: false,
  charging_authorized: false,
  powered_operation_authorized: false,
  generic_builder_may_promote_x1_authority: false,
};
const alphabetic = (a, b) => a < b ? -1 : a > b ? 1 : 0;
const uniqueSorted = values => [...new Set(values)].sort(alphabetic);
const MAINTENANCE = new Set(["REFRESH_DUE", "STALE", "MISSING_PROVENANCE", "HEALTH_UNAVAILABLE"]);

export function buildEvidenceExplorer(candidate, catalog, health = null) {
  const components = new Map((catalog.components || []).map(row => [row.id, row]));
  const healthRows = new Map((health?.component_health || []).map(row => [row.component_id, row]));
  const physicalIds = candidate.composition?.physical_interface_ids ??
    candidate.compatibility_interface_ids;
  const physicalBasis = physicalIds === undefined || physicalIds === null
    ? "REFERENCE_BOM_ONLY" : "EXPANDED_COMPONENT_GRAPH";
  const selectedIds = uniqueSorted([
    ...(candidate.bom || []).map(row => row.component_id),
    ...(physicalIds || []),
  ]);
  const sourceRow = id => {
    const item = components.get(id) || {};
    const source = item.source || {};
    const info = healthRows.get(id);
    return {
      component_id: id,
      label: item.label || id,
      category: item.category ?? null,
      source_url: source.url ?? null,
      snapshot_id: source.snapshot_id ?? null,
      verified_as_of: info?.verified_as_of ?? null,
      health_status: info?.status ?? "HEALTH_UNAVAILABLE",
      source_kind: source.kind ?? null,
    };
  };
  const sourceEvidence = selectedIds.map(sourceRow);
  const sourceIndex = new Map(sourceEvidence.map(row => [row.component_id, row]));
  const findings = [], worklist = [];
  for (const f of [...(candidate.compatibility_findings || [])].sort((a,b) => alphabetic(a.id,b.id))) {
    const a = f.a, b = f.b;
    const categoryPair = uniqueSorted([
      components.get(a)?.category || "unknown", components.get(b)?.category || "unknown",
    ]).join(":");
    const fallback = f.source === "category_default" || String(f.id).startsWith("default:");
    const finding = {
      id: f.id,
      a, b,
      a_label: components.get(a)?.label || a,
      b_label: components.get(b)?.label || b,
      category_pair: categoryPair,
      state: f.state,
      evidence_kind: fallback ? "CONSERVATIVE_CATEGORY_FALLBACK" : "EXPLICIT_CATALOG_RULE",
      reason: f.reason,
      sources: uniqueSorted([a, b]).map(id => sourceIndex.get(id) || sourceRow(id)),
    };
    findings.push(finding);
    if (f.state === "UNKNOWN" || f.state === "MEASURE_FIRST") {
      worklist.push({
        id: f.id,
        component_ids: uniqueSorted([a, b]),
        state: f.state,
        category_pair: categoryPair,
        question: CHECKS[categoryPair] || "Establish the exact selected-revision mechanical interface and its coexistence constraints.",
        evidence_required: EVIDENCE_REQUIRED,
        reason: f.reason,
      });
    }
  }
  const issues = sourceEvidence.filter(row => MAINTENANCE.has(row.health_status))
    .sort((a,b) => alphabetic(a.component_id,b.component_id));
  const unpriced = uniqueSorted(candidate.cost?.unpriced_component_ids || []);
  const linkedReasons = new Set(findings.map(f => f.reason));
  const otherUnknowns = uniqueSorted((candidate.unknowns || []).filter(x => !linkedReasons.has(x)));
  const summary = {
    explicit_rules: findings.filter(f => f.evidence_kind === "EXPLICIT_CATALOG_RULE").length,
    conservative_fallbacks: findings.filter(f => f.evidence_kind === "CONSERVATIVE_CATEGORY_FALLBACK").length,
    open_interfaces: worklist.length,
    incompatible_interfaces: findings.filter(f => f.state === "INCOMPATIBLE").length,
    source_refresh_or_integrity_issues: issues.length,
    unpriced_items: unpriced.length,
    price_complete: unpriced.length === 0,
    physical_basis: physicalBasis,
  };
  return {
    schema_version: 1,
    scope: "non_authoritative_catalog_evidence_explorer",
    candidate_id: candidate.id || "custom_study",
    origin: candidate.origin || "SWAP_STUDY",
    readiness: candidate.readiness ?? null,
    checkout_state: candidate.checkout_state ?? null,
    summary,
    interfaces: findings,
    measurement_worklist: worklist,
    source_evidence: sourceEvidence,
    source_maintenance: issues,
    other_uncertainties: otherUnknowns,
    hard_blockers: uniqueSorted(candidate.blockers || []),
    unpriced_component_ids: unpriced,
    price_basis: "KNOWN_USD_SUBTOTAL_ONLY",
    score_basis: "PLANNING_PREFERENCE_NOT_SAFETY",
    qualification_note: "Catalog rules and source freshness are not physical qualification. Measurement worklists cannot release procurement, fabrication, charging or powered operation.",
    authority: {...AUTHORITY},
  };
}
