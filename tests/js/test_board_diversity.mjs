import assert from "node:assert/strict";
import test from "node:test";
import {buildDiverseShortlist,mechanicalSignature} from "../../builder/diversity.mjs";

const candidate=(id,deck,truck,wheel,brake,drive,score=0.8,extra={})=>({
  id,label:id,deck_candidate_id:deck,topology_id:truck,
  fit_score:score,bom:[
    {category:"wheel",component_id:wheel},
    ...(brake?[{category:"brake",component_id:brake}]:[]),
    ...(drive?[{category:"drive",component_id:drive}]:[])
  ],
  cost:{known_min_usd:400,unpriced_component_ids:["UNKNOWN-ELECTRICAL"]},
  blockers:[],compatibility_findings:[],
  evidence:{summary:{open_interfaces:2,incompatible_interfaces:0}},
  ...extra
});
const a=candidate("a","deck-a","truck-x","wheel-8","brake-mech",null,0.95);
const b=candidate("b","deck-b","truck-y","wheel-9","brake-hydro","belt",0.80);
const c=candidate("c","deck-c","truck-z","wheel-8","brake-hydro","gear",0.70);
const duplicate=candidate("same-topology","deck-a","truck-x","wheel-8","brake-mech",null,0.92);

test("three genuinely mechanically different planning studies, not cosmetic duplicates",()=>{
  const before=JSON.stringify([a,duplicate,b,c]);
  const report=buildDiverseShortlist([a,duplicate,b,c],1800);
  assert.deepEqual(report.selected_ids,["a","b","c"]);
  assert.equal(report.studies.length,3);
  assert.ok(report.studies[1].differing_axes_from_first.includes("deck"));
  assert.ok(report.studies[1].differing_axes_from_first.includes("truck"));
  assert.equal(report.studies[0].unpriced_component_count,1);
  assert.equal(report.authority.powered_operation_authorized,false);
  assert.equal(report.authority.procurement_authorized,false);
  assert.equal(JSON.stringify([a,duplicate,b,c]),before);
});

test("blocked, incompatible and above known-parts budget excluded, not promoted",()=>{
  const impossible=candidate("blocking","deck-q","truck-q","wheel-x","brake","drive",0.98,
    {blockers:["No independent friction brake"]});
  const bad=candidate("bad-interface","deck-u","truck-u","wheel-x","brake","drive",0.97,
    {compatibility_findings:[{state:"INCOMPATIBLE"}]});
  const over=candidate("over-budget","deck-v","truck-v","wheel-x","brake","drive",0.96,
    {cost:{known_min_usd:2200,unpriced_component_ids:[]}});
  const report=buildDiverseShortlist([impossible,bad,over,a,b,c],1200);
  assert.deepEqual(report.selected_ids,["a","b","c"]);
  assert.deepEqual(report.excluded.slice(0,3).map(x=>x.reason),[
    "HARD_MECHANICAL_OR_MISSION_BLOCKER","INCOMPATIBLE_INTERFACE",
    "KNOWN_COMPONENT_COST_EXCEEDS_HARD_BUDGET"
  ]);
  assert.match(report.interpretation,/not verified assemblies/);
});

test("fewer than three available studies reported without mechanical inventions",()=>{
  const report=buildDiverseShortlist([a,duplicate],1200);
  assert.deepEqual(report.selected_ids,["a"]);
  assert.match(report.shortage_reason,/Only 1 mechanically distinct/);
  assert.equal(report.considered_count,2);
  assert.equal(report.eligible_count,2);
  assert.equal(report.excluded[0].reason,"NOT_SELECTED_OR_INSUFFICIENT_MECHANICAL_DIVERSITY");
});

test("selected composition slot identity wins over commercial donor BOM, no hidden authority",()=>{
  const composed={...a,composition:{selection:{
    deck:"catalog-deck",truck:"catalog-truck",wheel:"catalog-wheel",brake:null,drive:"catalog-drive"
  }}};
  const signature=mechanicalSignature(composed);
  assert.equal(signature.deck,"deck-a");
  assert.equal(signature.truck,"truck-x");
  assert.equal(signature.wheel,"catalog-wheel");
  assert.equal(signature.drive,"catalog-drive");
  assert.ok(Object.values(buildDiverseShortlist([composed]).authority).every(v=>v===false));
});

test("repeated IDs and invalid shortlist sizes fail predictably",()=>{
  const report=buildDiverseShortlist([a,{...a}],null);
  assert.equal(report.eligible_count,1);
  assert.equal(report.excluded[0].reason,"DUPLICATE_ID");
  assert.throws(()=>buildDiverseShortlist([a],null,0),/Invalid shortlist size/);
});


test("malformed numeric scores never pass selection or grant authority",()=>{
  const report=buildDiverseShortlist([
    {...a,id:"bad-null",fit_score:null},
    {...a,id:"bad-nan",fit_score:Number.NaN},
    a
  ]);
  assert.deepEqual(report.selected_ids,["a"]);
  assert.equal(report.excluded.filter(e=>e.reason==="INVALID_PLANNING_CANDIDATE").length,2);
  assert.equal(report.authority.fabrication_authorized,false);
});
