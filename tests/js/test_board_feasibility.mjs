import test from "node:test";
import assert from "node:assert/strict";
import {buildFeasibilityReport} from "../../builder/feasibility.mjs";
const authority=report=>assert.ok(Object.values(report.authority).every(x=>x===false));
const candidate=(id,extra={})=>({
  id,label:id,fit_score:0.8,readiness:"REFERENCE_COMPATIBLE",
  blockers:[],compatibility_findings:[],
  cost:{known_min_usd:550,unpriced_component_ids:["battery-study"]},
  evidence:{summary:{incompatible_interfaces:0,open_interfaces:2,source_refresh_or_integrity_issues:1}},
  ...extra
});
const shortlist={schema_version:1,scope:"non_authoritative_diverse_board_shortlist",
  selected_ids:["a"],excluded:[{id:"b",reason:"KNOWN_COMPONENT_COST_EXCEEDS_HARD_BUDGET"},
    {id:"c",reason:"NOT_SELECTED_OR_INSUFFICIENT_MECHANICAL_DIVERSITY"}]};
test("cost unknown even when known parts appear under budget",()=>{
  const report=buildFeasibilityReport([candidate("a")],shortlist,1500);
  assert.equal(report.candidate_count,1);
  assert.equal(report.records[0].result,"UNRESOLVED_STUDY");
  assert.equal(report.records[0].shortlist_role,"DIVERSITY_SELECTED");
  assert.equal(report.records[0].cost.all_in_budget_status,"UNKNOWN_REQUIRES_QUOTES_AND_INTEGRATION_COST");
  assert.equal(report.records[0].cost.known_minimum_already_over_budget,false);
  assert.ok(report.records[0].next_steps.some(x=>x.includes("independent exact-revision")));
  authority(report);authority(report.records[0]);
});
test("known subtotal already above maximum is a hard conflict, not an estimate of total",()=>{
  const over=candidate("b",{cost:{known_min_usd:1800,unpriced_component_ids:[]}});
  const r=buildFeasibilityReport([over],shortlist,1400).records[0];
  assert.equal(r.result,"BLOCKED");
  assert.equal(r.cost.known_minimum_already_over_budget,true);
  assert.equal(r.shortlist_exclusion_reason,"KNOWN_COMPONENT_COST_EXCEEDS_HARD_BUDGET");
  assert.ok(r.issues.includes("KNOWN_MINIMUM_PARTS_ABOVE_BUDGET"));
  authority(r);
});
test("mechanical blocker never blended with source staleness or soft ranking",()=>{
  const x=candidate("c",{
    blockers:["Independent friction brake not qualified"],
    compatibility_findings:[{state:"INCOMPATIBLE"}],
    readiness:"BLOCKED"
  });
  const r=buildFeasibilityReport([x],shortlist,1500).records[0];
  assert.equal(r.result,"BLOCKED");
  assert.equal(r.mechanical.explicit_blockers.length,1);
  assert.equal(r.mechanical.incompatible_interfaces,1);
  assert.ok(r.issues.includes("INCOMPATIBLE_COMPONENT_INTERFACES"));
  assert.ok(r.issues.includes("SOURCE_EVIDENCE_REFRESH_REQUIRED"));
  assert.equal(r.physical_qualification_status,"NOT_QUALIFIED");
});
test("no unresolved catalog findings is still a planning study and never ride-ready",()=>{
  const clean=candidate("a",{cost:{known_min_usd:500,unpriced_component_ids:[]},
    evidence:{summary:{incompatible_interfaces:0,open_interfaces:0,source_refresh_or_integrity_issues:0}}});
  const r=buildFeasibilityReport([clean],shortlist,2000).records[0];
  assert.equal(r.result,"PLANNING_STUDY");
  assert.equal(r.physical_qualification_status,"NOT_QUALIFIED");
  assert.equal(r.authority.powered_operation_authorized,false);
  assert.equal(r.cost.all_in_budget_status,"UNKNOWN_REQUIRES_QUOTES_AND_INTEGRATION_COST");
});
test("deterministic sorting, unchanged candidates, malformed shortlist fail closed",()=>{
  const inputs=[candidate("b"),candidate("a")];
  const original=JSON.stringify(inputs);
  const output=buildFeasibilityReport(inputs,shortlist);
  assert.deepEqual(output.records.map(r=>r.candidate_id),["a","b"]);
  assert.equal(JSON.stringify(inputs),original);
  assert.throws(()=>buildFeasibilityReport(inputs,{scope:"authorized_to_buy"}),/valid diverse shortlist/);
});
