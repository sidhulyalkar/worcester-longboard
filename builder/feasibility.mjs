// A candidate feasibility *receipt*, not mechanical certification or a purchase gate.
// The physical qualification pipeline does not consume this report.
const authority=()=>({
  procurement_authorized:false,
  fabrication_authorized:false,
  charging_authorized:false,
  powered_operation_authorized:false,
  generic_builder_may_promote_x1_authority:false
});
const numeric=x=>typeof x==="number" && Number.isFinite(x) ? x : null;
const uniqSorted=items=>[...new Set(items)].sort();
const costInstruction="Confirm exact supplier variants and quotations; known parts exclude shipping, tax, tools, specialist labor and validation.";
const physicalInstruction="Obtain independent exact-revision fit, braking, structural and electrical qualification before any physical release.";
const reasonLabels={
  HARD_MECHANICAL_OR_MISSION_BLOCKER:"Blocked by a recorded mechanical or mission requirement",
  INCOMPATIBLE_INTERFACE:"Recorded component interface incompatibility",
  KNOWN_COMPONENT_COST_EXCEEDS_HARD_BUDGET:"Known parts already exceed the stated maximum",
  NOT_SELECTED_OR_INSUFFICIENT_MECHANICAL_DIVERSITY:"Not included in a mechanically distinct three-way sample",
  DUPLICATE_ID:"Duplicate candidate identity",
  INVALID_PLANNING_CANDIDATE:"Invalid candidate source record"
};
export function buildFeasibilityReport(candidates,shortlist,hardBudgetUsd=null){
  if(!Array.isArray(candidates) || shortlist?.scope!=="non_authoritative_diverse_board_shortlist")
    throw new Error("Feasibility requires candidates and a valid diverse shortlist");
  const hardBudget=numeric(hardBudgetUsd);
  const selected=new Set(shortlist.selected_ids || []);
  const omitted=new Map((shortlist.excluded || []).map(row=>[row.id,row.reason]));
  const ordered=[...candidates].sort((a,b)=>
    String(a.id)<String(b.id)?-1:String(a.id)>String(b.id)?1:0);
  const records=ordered.map(candidate=>{
    const blockers=uniqSorted((candidate.blockers || []).map(String));
    const pairIncompatible=(candidate.compatibility_findings || [])
      .filter(row=>row.state==="INCOMPATIBLE").length;
    const summary=candidate.evidence?.summary || {};
    const incompatible=Math.max(pairIncompatible,numeric(summary.incompatible_interfaces) ?? 0);
    const openInterfaces=numeric(summary.open_interfaces) ?? 0;
    const sourceIssues=numeric(summary.source_refresh_or_integrity_issues) ?? 0;
    const unpriced=(candidate.cost?.unpriced_component_ids || []).length;
    const knownMin=numeric(candidate.cost?.known_min_usd);
    const aboveBudget=hardBudget!==null && knownMin!==null && knownMin>hardBudget;
    const blocked=!!blockers.length || incompatible>0 ||
      candidate.readiness==="BLOCKED" || aboveBudget;
    const issues=[];
    if(blockers.length)issues.push("RECORDED_HARD_BLOCKER");
    if(incompatible>0)issues.push("INCOMPATIBLE_COMPONENT_INTERFACES");
    if(candidate.readiness==="BLOCKED")issues.push("CATALOG_READINESS_BLOCKED");
    if(aboveBudget)issues.push("KNOWN_MINIMUM_PARTS_ABOVE_BUDGET");
    if(openInterfaces>0)issues.push("UNRESOLVED_INTERFACE_EVIDENCE");
    if(sourceIssues>0)issues.push("SOURCE_EVIDENCE_REFRESH_REQUIRED");
    if(unpriced>0)issues.push("UNPRICED_COMPONENTS");
    const next=[];
    if(blockers.length || candidate.readiness==="BLOCKED")
      next.push("Resolve the documented mission or mechanical blocker; do not fabricate or purchase from this proposal.");
    if(incompatible>0)
      next.push("Select a documented compatible interface and re-evaluate; an improvised adapter is not a qualification.");
    if(aboveBudget)
      next.push("Revise the parts budget or compare other sourced families; current known minimum already exceeds the limit.");
    if(openInterfaces>0)
      next.push("Measure exact-revision hub, axle, brake, drive and mount interfaces where flagged in the worklist.");
    if(sourceIssues>0)
      next.push("Refresh dated manufacturer evidence for affected component variants.");
    next.push(costInstruction);
    next.push(physicalInstruction);
    const exclusion=omitted.get(candidate.id) || null;
    return {
      candidate_id:candidate.id,
      result:blocked?"BLOCKED":issues.length?"UNRESOLVED_STUDY":"PLANNING_STUDY",
      shortlist_role:selected.has(candidate.id)?"DIVERSITY_SELECTED":"NOT_IN_SHORTLIST",
      shortlist_exclusion_reason:exclusion,
      shortlist_exclusion_explanation:exclusion?reasonLabels[exclusion] || "Not selected by the shortlist policy":null,
      mechanical:{
        explicit_blockers:blockers,
        incompatible_interfaces:incompatible,
        unresolved_interfaces:openInterfaces,
        source_followups:sourceIssues
      },
      cost:{
        stated_hard_budget_usd:hardBudget,
        known_minimum_parts_usd:knownMin,
        unpriced_component_count:unpriced,
        known_minimum_already_over_budget:aboveBudget,
        all_in_budget_status:"UNKNOWN_REQUIRES_QUOTES_AND_INTEGRATION_COST"
      },
      issues:uniqSorted(issues),
      next_steps:uniqSorted(next),
      physical_qualification_status:"NOT_QUALIFIED",
      authority:authority()
    };
  });
  return {
    schema_version:1,
    scope:"non_authoritative_board_feasibility_receipts",
    candidate_count:records.length,
    blocked_count:records.filter(row=>row.result==="BLOCKED").length,
    unresolved_study_count:records.filter(row=>row.result==="UNRESOLVED_STUDY").length,
    records,
    note:"A feasibility receipt explains planning constraints; it is not proof of structural fit, brake performance, sourcing completeness or safe operation.",
    authority:authority()
  };
}
