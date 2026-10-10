// An explanatory, physically diverse shortlist of planning studies.
// This module never chooses a safe, purchasable or ride-authorized winner.
const AXES=["deck","truck","wheel","brake","drive"];
const AUTHORITY=Object.freeze({
  procurement_authorized:false,fabrication_authorized:false,
  charging_authorized:false,powered_operation_authorized:false,
  generic_builder_may_promote_x1_authority:false
});
const asId=value=>value===null || value===undefined || value==="" ? "UNKNOWN" : String(value);
function categoryPart(candidate,category) {
  const ids=(candidate.bom || []).filter(row=>row.category===category)
    .map(row=>row.component_id).filter(Boolean).sort();
  return ids.length ? ids.join("+") : null;
}
export function mechanicalSignature(candidate) {
  const selected=candidate.composition?.selection || candidate.swap_defaults || {};
  return {
    deck:asId(candidate.deck_candidate_id || selected.deck),
    truck:asId(candidate.topology_id || selected.truck),
    wheel:asId(selected.wheel || categoryPart(candidate,"wheel") ||
      candidate.capabilities?.wheel_class),
    brake:asId(selected.brake || categoryPart(candidate,"brake") || "NOT_SPECIFIED"),
    drive:asId(selected.drive || categoryPart(candidate,"drive") || "NOT_SPECIFIED")
  };
}
const evidenceForAxis=value=>value!=="UNKNOWN" && value!=="NOT_SPECIFIED";
const difference=(a,b)=>AXES.filter(axis=>evidenceForAxis(a[axis]) && evidenceForAxis(b[axis]) && a[axis]!==b[axis]);
const materiallyDistinct=(a,b)=>{
  const differences=difference(a,b);
  return differences.length>=2 && (differences.includes("deck") || differences.includes("truck"));
};
function exclusion(candidate,maxBudget){
  if(!candidate || !candidate.id || typeof candidate.fit_score!=="number" || !Number.isFinite(candidate.fit_score))
    return "INVALID_PLANNING_CANDIDATE";
  if((candidate.blockers || []).length) return "HARD_MECHANICAL_OR_MISSION_BLOCKER";
  if((candidate.compatibility_findings || []).some(row=>row.state==="INCOMPATIBLE") ||
    Number(candidate.evidence?.summary?.incompatible_interfaces || 0)>0)
    return "INCOMPATIBLE_INTERFACE";
  // Known parts alone over the ceiling is enough to reject; an apparent
  // under-budget subtotal NEVER establishes all-in budget feasibility.
  const knownMin=candidate.cost?.known_min_usd;
  if(Number.isFinite(maxBudget) && typeof knownMin==="number" &&
     Number.isFinite(knownMin) && knownMin>maxBudget)
    return "KNOWN_COMPONENT_COST_EXCEEDS_HARD_BUDGET";
  return null;
}
export function buildDiverseShortlist(candidates,hardBudgetUsd=null,limit=3){
  if(!Array.isArray(candidates))throw new Error("Candidates must be an array");
  if(!Number.isInteger(limit) || limit<1 || limit>5)
    throw new Error("Invalid shortlist size");
  const budget=typeof hardBudgetUsd==="number" && Number.isFinite(hardBudgetUsd)
    ? hardBudgetUsd : null;
  const viable=[],excluded=[],seen=new Set();
  // Candidate labels are locale-sorted by the UI. Normalize comparison order
  // independently so Python and JavaScript choose the same physical shortlist.
  const score=c=>typeof c?.fit_score==="number" && Number.isFinite(c.fit_score)
    ? c.fit_score : -1;
  const ordered=[...candidates].sort((a,b)=>score(b)-score(a) ||
    (String(a?.id || "")<String(b?.id || "")?-1:
      String(a?.id || "")>String(b?.id || "")?1:0));
  for(const candidate of ordered){
    if(candidate?.id && seen.has(candidate.id)) {
      excluded.push({id:candidate.id,reason:"DUPLICATE_ID"});
      continue;
    }
    if(candidate?.id)seen.add(candidate.id);
    const why=exclusion(candidate,budget);
    if(why)excluded.push({id:candidate?.id || "UNKNOWN",reason:why});
    else viable.push({candidate,signature:mechanicalSignature(candidate)});
  }
  // The input comes from the unified deterministic candidate scorer,
  // highest-fit first. Preserve that ordering for the initial anchor.
  const chosen=viable.length?[viable[0]]:[];
  while(chosen.length<limit){
    const eligible=viable.filter(row=>!chosen.some(
      prior=>prior.candidate.id===row.candidate.id ||
      !materiallyDistinct(prior.signature,row.signature)));
    if(!eligible.length)break;
    // Prefer meaningful mechanical novelty over a fractional soft score.
    const novelty=row=>AXES.reduce((total,key)=>
      total+((!evidenceForAxis(row.signature[key]) || chosen.some(prior=>!evidenceForAxis(prior.signature[key]) || prior.signature[key]===row.signature[key]))?0:
        (key==="deck" || key==="truck" ? 2 : 1)),0);
    let next=eligible[0],best=novelty(next);
    for(const row of eligible.slice(1)){
      const value=novelty(row);
      if(value>best) {next=row;best=value;}
    }
    chosen.push(next);
  }
  const selectedIds=new Set(chosen.map(row=>row.candidate.id));
  const detailed=chosen.map((row,index)=>({
    id:row.candidate.id,
    mechanical_signature:row.signature,
    differing_axes_from_first:index ? difference(chosen[0].signature,row.signature) : [],
    open_interfaces:Number(row.candidate.evidence?.summary?.open_interfaces || 0),
    unpriced_component_count:(row.candidate.cost?.unpriced_component_ids || []).length,
    known_parts_cost_min_usd:row.candidate.cost?.known_min_usd ?? null,
    evidence_state:"PLANNING_STUDY_NOT_PHYSICALLY_QUALIFIED"
  }));
  for(const row of viable)if(!selectedIds.has(row.candidate.id))
    excluded.push({id:row.candidate.id,reason:"NOT_SELECTED_OR_INSUFFICIENT_MECHANICAL_DIVERSITY"});
  return {
    schema_version:1,scope:"non_authoritative_diverse_board_shortlist",
    target_count:limit,considered_count:candidates.length,eligible_count:viable.length,
    selected_ids:chosen.map(row=>row.candidate.id),studies:detailed,excluded,
    shortage_reason:chosen.length<limit
      ? "Only "+chosen.length+" mechanically distinct, non-hard-blocked planning studies satisfy the shortlist rules. Check exclusions and unresolved interfaces."
      : null,
    interpretation:"Different mechanical concepts for comparison, not verified assemblies, compatible kits, complete quotes or safe ride recommendations.",
    authority:{...AUTHORITY}
  };
}
