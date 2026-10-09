// Assembly onboarding is a learning / inspection roadmap, never a build permit.
// No general catalog candidate can unlock procurement, charging or powered operation.
const LOCKED_AUTHORITY = Object.freeze({
  procurement_authorized:false,
  fabrication_authorized:false,
  charging_authorized:false,
  powered_operation_authorized:false,
  generic_builder_may_promote_x1_authority:false,
});
export function assemblyGuide(candidate) {
  if (!candidate || !candidate.evidence) throw new Error("Assembly roadmap requires candidate evidence");
  const categories = new Set((candidate.bom || []).map(x=>x.category));
  const powered = ["drive","motor","esc","battery","charger"].some(c=>categories.has(c)) ||
    candidate.capabilities?.drive_path && candidate.capabilities.drive_path !== "NOT_PRESENT";
  const brake = categories.has("brake");
  const open = Number(candidate.evidence.summary.open_interfaces || 0);
  const incompat = Number(candidate.evidence.summary.incompatible_interfaces || 0);
  const blockers = (candidate.blockers || []).length;
  const unpriced = (candidate.cost?.unpriced_component_ids || []).length;
  const stages = [
    {id:"study",label:"Understand design + evidence",status:"STUDY_ONLY",skill:"Beginner-friendly planning",description:"Inspect CAD previews, exact component revisions, manufacturer manuals, source snapshots, dimensioned interfaces and missing-cost items. No purchase permission.",deliverable:"Versioned parts list, unresolved interface worklist and complete-cost estimate"},
    {id:"fit",label:"Physical fit and brake validation",status:"MEASURE_FIRST",skill:"Mechanical measurement expertise",description:"Obtain exact-revision mounting, axle, hub, brake and drive coexistence measurements. Explicit incompatibilities cannot be cleared by visual inspection alone.",deliverable:"Reviewed dimensions and recorded brake path evidence from the separate qualification process"},
    {id:"mechanical",label:"Chassis and mechanical assembly",status:"QUALIFICATION_REQUIRED",skill:"Experienced hobbyist with manufacturer instructions and independent inspection",description:"A qualified chassis/brake parts subset may eventually be assembled using manufacturer-specific methods, rated fasteners and torque data. None of these generic candidates is released.",deliverable:"Revision-matched inspection records, fastener checks and mechanical safety sign-off"},
    {id:"electrical",label:"Drive electronics and battery integration",status:powered?"POWER_GATED":"NOT_APPLICABLE",skill:powered?"Qualified battery/electrical specialist":"Not part of this manual design",description:powered?"BMS, fused pack, charger, wiring protection, enclosures and controller interfaces require a separately qualified system, component-specific documentation and competent electrical review. Do not build a loose-cell battery pack from this catalog.":"No traction battery, motor or ESC is included in this reference study.",deliverable:powered?"Professional electrical design review and traceable pack/charger documentation":"No powered system"},
    {id:"commission",label:"Bench validation + controlled commissioning",status:powered?"POWER_GATED":"QUALIFICATION_REQUIRED",skill:"Independent system verification",description:"Structural, brake, protection, interlock, thermal and failure-behavior checks belong to a separately authorized test plan. UI exports and assembly notes do not authorize energizing or riding.",deliverable:"Separately approved test evidence and release decision"},
  ];
  return {
    schema_version:1,scope:"non_authoritative_assembly_readiness",
    candidate_id:candidate.id, powered:Boolean(powered), independent_brake_in_bom:brake,
    complexity:powered?"ADVANCED_PROFESSIONAL_ELECTRICAL":"MECHANICAL_WITH_MEASUREMENT",
    unresolved_interfaces:open, incompatible_interfaces:incompat,
    blockers,unpriced_components:unpriced,
    planning_complete:unpriced===0&&open===0&&incompat===0&&blockers===0,
    planning_note:"Planning completeness is not construction readiness, stock verification or mechanical qualification.",
    budget_exclusions:["Shipping and tax","Tools and consumables","Manufacturer-specific fasteners and spares","Professional inspection or electrical integration","Safety gear and testing"],
    stages,authority:{...LOCKED_AUTHORITY}
  };
}
