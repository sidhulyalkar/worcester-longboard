// Compare two non-authoritative candidate studies without altering ranking or qualification.
import {visualStateFromCandidate} from "./visual_state.mjs";
import {assemblyGuide} from "./assembly_guide.mjs";
const authority=()=>({
  procurement_authorized:false,
  fabrication_authorized:false,
  charging_authorized:false,
  powered_operation_authorized:false,
  generic_builder_may_promote_x1_authority:false
});
const uniq = a => [...new Set(a)].sort();
export function defaultComparisonIds(candidates) {
  const a = candidates.find(x => x.id === "brake_first_trail_core") || candidates[0];
  const b = candidates.find(x => x.id === "trampa_hydraulic_freeride") ||
    candidates.find(x => x.id !== a?.id && (x.deck_candidate_id !== a.deck_candidate_id || x.topology_id !== a.topology_id));
  return a && b ? [a.id,b.id] : [];
}
export function compareCandidates(left,right,geometry,catalog) {
  if (!left || !right || left.id === right.id) throw new Error("Choose two distinct board candidates");
  const construct = candidate => {
    if (!candidate.evidence) throw new Error("Evidence is required for comparison");
    const visual = visualStateFromCandidate(candidate,geometry,catalog);
    const assembly = assemblyGuide(candidate);
    return {
      id:candidate.id,label:candidate.label,vendor_family:candidate.vendor_family,
      origin:candidate.origin,fit_score:candidate.fit_score,readiness:candidate.readiness,
      checkout_state:candidate.checkout_state,
      geometry:{
        deck_id:visual.deck.id,deck_length_mm:visual.deck.length_mm,deck_width_mm:visual.deck.width_mm,
        deck_evidence_state:visual.deck.evidence_state,
        truck_id:visual.topology.id,truck_width_mm:visual.topology.truck_total_width_mm,
        axle_diameter_mm:visual.topology.axle_diameter_mm,
        topology_evidence_state:visual.topology.evidence_state,
        visual_geometry_state:visual.topology.visual_geometry_state,
        wheel_id:visual.wheel.study_id,wheel_diameter_mm:visual.wheel.diameter_mm,
        brake:visual.visual_style.brake_family,drive:visual.visual_style.drive_type
      },
      cost:{
        known_min_usd:candidate.cost.known_min_usd,known_max_usd:candidate.cost.known_max_usd,
        unpriced_component_ids:uniq(candidate.cost.unpriced_component_ids || []),
        source_native_price_incomplete:!!candidate.cost.unpriced_component_ids?.length,
        excluded:["Shipping","Tax","Assembly and professional labor","Tools, safety gear and validation"]
      },
      evidence:{
        open_interfaces:candidate.evidence.summary.open_interfaces,
        incompatible_interfaces:candidate.evidence.summary.incompatible_interfaces,
        physical_basis:candidate.evidence.summary.physical_basis,
        source_followups:candidate.evidence.summary.source_refresh_or_integrity_issues,
        worklist:candidate.evidence.measurement_worklist.map(t=>({
          id:t.id,category_pair:t.category_pair,question:t.question,state:t.state,component_ids:t.component_ids
        })),
        blockers:uniq(candidate.evidence.hard_blockers||[]),
        sources:candidate.evidence.source_evidence.map(s=>({component_id:s.component_id,health_status:s.health_status,source_url:s.source_url,snapshot_id:s.snapshot_id,verified_as_of:s.verified_as_of})),
      },
      assembly,
      visual,
      authority:authority()
    };
  };
  const a=construct(left),b=construct(right);
  const physical = x=>[x.geometry.deck_id,x.geometry.truck_id,x.geometry.wheel_id,x.geometry.brake,x.geometry.drive].join("|");
  const exactMechanics=physical(a)===physical(b);
  const idsA=new Set(a.evidence.worklist.map(t=>t.id)),idsB=new Set(b.evidence.worklist.map(t=>t.id));
  return {
    schema_version:1,scope:"non_authoritative_board_comparison",candidates:[a,b],
    mechanically_distinct:!exactMechanics,
    differentiators:{
      interface_checks_unique_to_first:a.evidence.worklist.filter(t=>!idsB.has(t.id)),
      interface_checks_unique_to_second:b.evidence.worklist.filter(t=>!idsA.has(t.id)),
      shared_open_interface_ids:uniq([...idsA].filter(id=>idsB.has(id))),
      geometry_fields_changed:Object.keys(a.geometry).filter(k=>a.geometry[k]!==b.geometry[k])
    },
    comparison_note:"Both studies share a rider profile, but fit scores are preferences, not safety ratings. Catalog reference, visuals and price subtotals are not proof of fit, stock, purchase or assembly authority.",
    authority:authority()
  };
}
